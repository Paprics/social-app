"""
signaling.py — Главный WebSocket consumer для видеочата.

Что делает этот файл:
    Обрабатывает все WebSocket соединения от обычных пользователей чата.
    Отвечает за три вещи:
        1. Матчмейкинг — найти собеседника через очередь в Redis
        2. Сигналинг — проксировать WebRTC сообщения (offer/answer/ICE) между партнёрами
        3. Текстовый чат — пересылать сообщения между партнёрами

Как работает WebRTC соединение (упрощённо):
    1. Оба пользователя подключаются к WebSocket
    2. Сервер находит им пару (матчмейкинг)
    3. Один получает роль "caller", другой — "callee"
    4. Callee поднимает RTCPeerConnection и сообщает "ready"
    5. Caller получает "ready_to_connect" и создаёт offer
    6. Идёт обмен offer/answer/ICE через сервер (сигналинг)
    7. После этого видео/аудио идут напрямую P2P, минуя сервер
"""

import json
import logging
import uuid

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from chat.services.matchmaking import MatchmakingService
from chat.services.room_storage import RoomStorage

logger = logging.getLogger(__name__)


class SignalingConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для обычных пользователей видеочата.

    Жизненный цикл одного соединения:
        connect() → _find_partner() → [ожидание] → _create_room() или room_matched()
        → receive() [множество раз] → disconnect()

    Атрибуты:
        room_id: UUID текущей комнаты. None если пользователь в очереди.
        partner_channel: channel_name партнёра. Используется для прямой отправки
                         сообщений через channel layer.
        matchmaking: сервис для работы с очередью в Redis.
        room_storage: сервис для хранения списка комнат (нужен модератору).
        in_room: True если пользователь находится в активной комнате.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.partner_channel = None
        self.matchmaking = MatchmakingService()
        self.room_storage = RoomStorage()
        self.in_room = False

    # ── Жизненный цикл соединения ───────────────────────────────────────────

    async def connect(self):
        """Пользователь открыл WebSocket.

        Принимаем соединение и сразу ищем партнёра.
        Если партнёра нет — пользователь встаёт в очередь и ждёт.
        """
        await self.accept()
        await self._find_partner()

    async def disconnect(self, close_code):
        """Пользователь закрыл вкладку или потерял соединение.

        Порядок важен:
            1. Убираем себя из очереди (если ещё там)
            2. Удаляем комнату из Redis (чтобы модератор не видел мёртвые комнаты)
            3. Уведомляем партнёра о разрыве
        """
        # Убираем себя из очереди матчмейкинга на случай если ещё там
        await sync_to_async(self.matchmaking.leave_queue)(self.channel_name)

        # Удаляем комнату из Redis если она была
        if self.room_id:
            await sync_to_async(self.room_storage.delete_room)(self.room_id)

        # Уведомляем партнёра — он увидит "Партнёр отключился"
        if self.partner_channel:
            await self.channel_layer.send(
                self.partner_channel,
                {"type": "partner.disconnected"},
            )
            self.partner_channel = None

    async def receive(self, text_data):
        """Получено сообщение от клиента (браузера).

        Роутим по полю type:
            offer/answer/ice_candidate → WebRTC сигналинг, проксируем партнёру
            next → пользователь нажал "Следующий", ищем нового партнёра
            ready → callee сообщает что RTCPeerConnection готов
            chat_message → текстовое сообщение, пересылаем партнёру
        """
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type in ("offer", "answer", "ice_candidate"):
            # WebRTC сигналинг — просто передаём партнёру как есть.
            # Сервер не понимает содержимое, просто проксирует.
            if self.partner_channel:
                await self.channel_layer.send(
                    self.partner_channel,
                    {
                        "type": "signaling.message",
                        "payload": data,  # Фронт читает msg.payload.type
                    },
                )

            # Также пересылаем модератору если он подключён к этой комнате.
            # Модератору нужен сигналинг чтобы установить своё P2P соединение.
            if self.room_id:
                await self.channel_layer.group_send(
                    f"moderate_{self.room_id}",  # Группа модераторов этой комнаты
                    {"type": "signaling.message", "payload": data},
                )

        elif msg_type == "next":
            # Пользователь нажал "Следующий" — разрываем текущую связь и ищем нового
            await self._handle_next()

        elif msg_type == "ready":
            # Callee поднял RTCPeerConnection и сообщает что готов принять offer.
            # Пересылаем это caller-у — он только тогда создаст и пошлёт offer.
            # Это handshake который решает гонку состояний:
            # без него caller мог отправить offer до того как callee создал pc.
            if self.partner_channel:
                await self.channel_layer.send(
                    self.partner_channel,
                    {
                        "type": "signaling.message",
                        "payload": {"type": "ready_to_connect"},
                    },
                )

        elif msg_type == "chat_message":
            # Текстовое сообщение — пересылаем партнёру.
            # Меняем sender на "partner" чтобы у партнёра отобразилось правильно.
            if self.partner_channel and self.room_id:
                payload = {
                    "type": "chat_message",
                    "text": data.get("text", ""),
                    "sender": "partner",
                }
                await self.channel_layer.send(
                    self.partner_channel,
                    {"type": "signaling.message", "payload": payload},
                )

    # ── Обработчики сообщений из channel layer ──────────────────────────────
    # Эти методы вызываются когда ДРУГОЙ consumer шлёт сообщение этому
    # через self.channel_layer.send(). Django Channels автоматически
    # маппит type "room.matched" → метод room_matched() (точка → подчёркивание).

    async def room_matched(self, event):
        """Callee получает это сообщение когда caller нашёл его в очереди.

        Вызывается через channel_layer.send() из _create_room() caller-а.

        event содержит:
            room_id: UUID новой комнаты
            caller_channel: channel_name caller-а (нужен для отправки сигналинга)
        """
        try:
            self.room_id = event["room_id"]
            self.partner_channel = event["caller_channel"]
            self.in_room = True

            # Отправляем клиенту — он узнаёт что нашёлся партнёр и его роль
            await self.send_json(
                {
                    "type": "matched",
                    "room_id": self.room_id,
                    "role": "callee",  # Этот пользователь — callee
                }
            )
        except Exception as e:
            logger.error(f"[room_matched] EXCEPTION: {e}", exc_info=True)
            raise

    async def signaling_message(self, event):
        """Получен WebRTC payload от партнёра или модератора — пересылаем клиенту.

        ВАЖНО: фронт ожидает структуру { payload: { type: "...", ... } }.
        Не менять формат без изменения room.html!

        ВАЖНО: этот метод должен быть только один в классе.
        Если объявить дважды — Python молча возьмёт последний, первый исчезнет.
        """
        await self.send_json({"payload": event["payload"]})

    async def partner_disconnected(self, event):
        """Партнёр отключился или нажал "Следующий".

        ВАЖНО: мы НЕ вызываем _find_partner() автоматически.
        Пользователь сам решает — нажать "Следующий" или подождать.
        Это предотвращает бесконечный цикл матчинга.
        """
        self.partner_channel = None
        self.room_id = None
        self.in_room = False
        # Клиент покажет "Партнёр отключился. Нажмите Следующий."
        await self.send_json({"type": "partner_disconnected"})

    async def moderator_kick(self, event):
        """Модератор кикнул этого пользователя.

        Отправляем клиенту уведомление и принудительно закрываем WebSocket.
        Клиент перенаправится или покажет сообщение о бане.
        """
        await self.send_json({"type": "kicked"})
        await self.close()

    # ── Внутренние методы ───────────────────────────────────────────────────

    async def _find_partner(self):
        """Поиск партнёра через очередь Redis.

        Алгоритм:
            1. Сбрасываем in_room
            2. Убираем себя из очереди (дубли от переподключений)
            3. Сообщаем клиенту "ожидание"
            4. Пробуем взять партнёра из очереди
            5. Если нашли — создаём комнату, если нет — ждём (стоим в очереди)
        """
        self.in_room = False
        # Убираем дубли — на случай если этот channel уже есть в очереди
        await sync_to_async(self.matchmaking.leave_queue)(self.channel_name)
        await self.send_json({"type": "status", "message": "waiting"})
        partner = await sync_to_async(self.matchmaking.join_queue)(self.channel_name)
        if partner:
            await self._create_room(partner)

    async def _create_room(self, partner_channel: str):
        """Создать комнату когда нашли партнёра.

        Этот пользователь становится caller-ом — он первым узнаёт о матче
        и будет отправлять WebRTC offer (но только после ready_to_connect от callee).

        Args:
            partner_channel: channel_name пользователя из очереди (станет callee)
        """
        self.room_id = str(uuid.uuid4())
        self.partner_channel = partner_channel
        self.in_room = True

        # Сохраняем комнату в Redis — модератор увидит её в своём списке
        await sync_to_async(self.room_storage.create_room)(
            self.room_id, self.channel_name, partner_channel
        )

        # Сообщаем этому пользователю (caller) о матче
        await self.send_json(
            {
                "type": "matched",
                "room_id": self.room_id,
                "role": "caller",
            }
        )

        # Уведомляем callee через channel layer.
        # channel_layer.send() — прямая отправка конкретному каналу (не broadcast).
        # Тип "room.matched" → вызовет метод room_matched() у callee.
        await self.channel_layer.send(
            partner_channel,
            {
                "type": "room.matched",
                "room_id": self.room_id,
                "caller_channel": self.channel_name,  # Callee запомнит кто его caller
            },
        )

    async def _handle_next(self):
        """Пользователь нажал кнопку "Следующий".

        Порядок операций критически важен:
            1. Сначала сохраняем ссылки на старого партнёра и комнату
            2. Сбрасываем своё состояние (partner_channel = None и т.д.)
            3. Удаляем комнату из Redis
            4. Уведомляем старого партнёра о разрыве
            5. Ищем нового партнёра

        ВАЖНО: шаг 2 до шага 4 — если сначала уведомить партнёра,
        а потом сбрасывать состояние, можно получить гонку состояний.
        """
        old_partner = self.partner_channel
        old_room = self.room_id

        # Сбрасываем состояние ДО уведомления партнёра
        self.partner_channel = None
        self.room_id = None
        self.in_room = False

        # Удаляем комнату из Redis
        if old_room:
            await sync_to_async(self.room_storage.delete_room)(old_room)

        # Партнёр получит partner_disconnected и будет ждать нажатия кнопки
        if old_partner:
            await self.channel_layer.send(
                old_partner,
                {"type": "partner.disconnected"},
            )

        # Идём искать нового партнёра
        await self._find_partner()

    async def send_json(self, data: dict):
        """Отправить JSON клиенту через WebSocket."""
        await self.send(text_data=json.dumps(data))
