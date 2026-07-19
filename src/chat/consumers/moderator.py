"""
moderator.py — WebSocket consumer для модератора.

Что делает этот файл:
    Позволяет модератору (is_staff пользователю) подключиться к существующей
    комнате и наблюдать за видео обоих участников через WebRTC.

Как работает WebRTC mesh на троих:
    Обычно два пользователя соединены напрямую P2P:
        Пользователь 1 ←──P2P──→ Пользователь 2

    Когда подключается модератор, схема становится:
        Пользователь 1 ←──P2P──→ Пользователь 2  (существующее соединение, не трогаем)
        Пользователь 1 ←──P2P──→ Модератор        (новое соединение)
        Пользователь 2 ←──P2P──→ Модератор        (новое соединение)

    Модератор устанавливает ДВА отдельных RTCPeerConnection.
    Его микрофон и камера отключены (recvonly) — он только смотрит.

Как работает kick:
    Модератор нажимает Kick → фронт отправляет {type: "kick", target: channel_name}
    → ModeratorConsumer пересылает channel_layer.send() нужному SignalingConsumer
    → SignalingConsumer.moderator_kick() закрывает WebSocket пользователя
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from chat.services.room_storage import RoomStorage

logger = logging.getLogger(__name__)


class ModeratorConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer для модератора видеочата.

    Подключается к существующей комнате по room_id из URL.
    Получает WebRTC сигналинг от обоих участников через channel group.
    Может отправить kick любому участнику.

    URL: ws://host/ws/chat/moderate/{room_id}/
    Доступ: только пользователи с is_staff=True (проверка временно отключена для диагностики)

    Атрибуты:
        room_id: UUID комнаты к которой подключён модератор
        room_group: название channel group ("moderate_{room_id}")
        room_storage: сервис для чтения метаданных комнаты из Redis
        room_meta: dict с caller и callee channel_name
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.room_id = None
        self.room_group = None
        self.room_storage = RoomStorage()
        self.room_meta = None

    # ── Жизненный цикл соединения ───────────────────────────────────────────

    async def connect(self):
        """Модератор подключается к комнате.

        Проверяет что комната существует в Redis.
        Вступает в channel group чтобы получать сигналинг от участников.
        Отправляет модератору данные комнаты (caller и callee channel_name).
        """
        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group = f"moderate_{self.room_id}"

        # Проверяем что комната ещё активна
        self.room_meta = await sync_to_async(self.room_storage.get_room)(self.room_id)
        logger.error(f"[MOD] room_meta: {self.room_meta}")

        if not self.room_meta:
            logger.error(f"[MOD] комната не найдена: {self.room_id}")
            await self.close(code=4404)
            return

        # Вступаем в group — будем получать сигналинг от участников
        await self.channel_layer.group_add(self.room_group, self.channel_name)
        await self.accept()

        # Отправляем модератору данные комнаты
        await self.send_json(
            {
                "type": "room_info",
                "room_id": self.room_id,
                "caller": self.room_meta["caller"],
                "callee": self.room_meta["callee"],
            }
        )
        logger.error(f"[MOD] room_info отправлен")

    async def disconnect(self, close_code):
        """Модератор закрыл вкладку.

        Покидаем channel group. Участники не уведомляются —
        их соединение между собой продолжает работать.
        """
        if self.room_group:
            await self.channel_layer.group_discard(self.room_group, self.channel_name)

    async def receive(self, text_data):
        """Получено сообщение от модератора.

        Типы сообщений:
            offer/answer/ice_candidate:
                WebRTC сигналинг от модератора к конкретному участнику.
                Поле "target" содержит channel_name участника.
                Пересылаем напрямую нужному SignalingConsumer.

            kick:
                Кик участника. Поле "target" содержит channel_name участника.
                SignalingConsumer.moderator_kick() закроет его WebSocket.
        """
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type in ("offer", "answer", "ice_candidate"):
            # Пересылаем WebRTC сигналинг конкретному участнику по target.
            # from_moderator=True — участник будет знать что это от модератора,
            # а не от своего партнёра, и ответит с from_moderator_reply=True.
            target = data.get("target")
            if target and self.room_meta:
                await self.channel_layer.send(
                    target,
                    {
                        "type": "signaling.message",
                        "payload": {**data, "from_moderator": True},
                    },
                )

        elif msg_type == "kick":
            # Кик пользователя.
            # moderator.kick → SignalingConsumer.moderator_kick() → ws.close()
            target = data.get("target")
            if target:
                await self.channel_layer.send(
                    target,
                    {"type": "moderator.kick"},
                )
                await self.send_json(
                    {
                        "type": "kick_sent",
                        "target": target,
                    }
                )

    # ── Обработчики channel layer ────────────────────────────────────────────

    async def signaling_message(self, event):
        """Получен сигналинг от участника комнаты — пересылаем модератору.

        Вызывается когда SignalingConsumer делает group_send() в "moderate_{room_id}".
        Модератор получает answer и ice_candidate от участников
        чтобы завершить установку P2P соединения.
        """
        await self.send_json({"payload": event["payload"]})

    # ── Утилиты ─────────────────────────────────────────────────────────────

    async def send_json(self, data: dict):
        """Отправить JSON модератору через WebSocket."""
        await self.send(text_data=json.dumps(data))
