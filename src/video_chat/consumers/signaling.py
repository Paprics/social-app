# src/video_chat/consumers/signaling.py

"""WebSocket consumer для пользователей случайного видеочата."""

import json
import math
import time
import uuid

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from video_chat.services.matchmaking import MatchmakingService
from video_chat.services.participant import (
    InvalidChatGender,
    build_participant_metadata,
)
from video_chat.services.participant_storage import ParticipantStorage
from video_chat.services.room_storage import RoomStorage

COOLDOWN_SECONDS = 3


class SignalingConsumer(AsyncWebsocketConsumer):
    """Управляет matchmaking-сессией, signaling и текстовым чатом."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.room_id = None
        self.partner_channel = None

        self.matchmaking = MatchmakingService()
        self.room_storage = RoomStorage()
        self.participant_storage = ParticipantStorage()

        self.in_room = False
        self.media_connected = False

        self.session_id = None
        self.session_active = False

        self.search_available_at = 0.0

    async def connect(self):
        """Принять WebSocket без автоматического входа в matchmaking."""

        await self.accept()

    async def disconnect(self, close_code):
        """Очистить Redis-состояние после закрытия WebSocket."""

        await self._finish_session(
            notify_partner=True,
        )

    async def receive(self, text_data):
        """Обработать команду браузера."""

        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "start":
            await self._handle_start(data)
            return

        if msg_type == "search":
            await self._handle_search()
            return

        if msg_type == "next":
            await self._handle_next()
            return

        if msg_type == "stop":
            await self._handle_stop()
            return

        if msg_type == "connected":
            await self._handle_connected()
            return

        if msg_type in (
            "offer",
            "answer",
            "ice_candidate",
        ):
            await self._handle_signaling(data)
            return

        if msg_type == "ready":
            await self._handle_ready()
            return

        if msg_type == "chat_message":
            await self._handle_chat_message(data)

    async def room_matched(self, event):
        """Принять созданную caller-ом комнату как callee."""

        if not self.session_active:
            await sync_to_async(self.room_storage.delete_room)(event["room_id"])

            await self.channel_layer.send(
                event["caller_channel"],
                {
                    "type": "partner.disconnected",
                },
            )
            return

        self.room_id = event["room_id"]
        self.partner_channel = event["caller_channel"]
        self.in_room = True
        self.media_connected = False

        await self.send_json(
            {
                "type": "matched",
                "room_id": self.room_id,
                "role": "callee",
            }
        )

    async def signaling_message(self, event):
        """Передать WebRTC payload из channel layer браузеру."""

        await self.send_json(
            {
                "payload": event["payload"],
            }
        )

    async def partner_disconnected(self, event):
        """После разрыва пары автоматически перейти в cooldown."""

        self.partner_channel = None
        self.room_id = None
        self.in_room = False
        self.media_connected = False

        if not self.session_active:
            await self.send_json(
                {
                    "type": "partner_disconnected",
                }
            )
            return

        await self._enter_cooldown(
            event_type="partner_disconnected",
        )

    async def moderator_kick(self, event):
        """Закрыть соединение пользователя по команде модератора."""

        await self.send_json(
            {
                "type": "kicked",
            }
        )
        await self.close()

    async def _handle_start(self, data):
        """Создать Redis-only сессию и запустить первый поиск."""

        if self.session_active:
            await self._send_error("already_started")
            return

        session_id = str(uuid.uuid4())
        chat_gender = data.get("gender", "")

        try:
            participant = await sync_to_async(build_participant_metadata)(
                user=self.scope.get("user"),
                chat_gender=chat_gender,
                session_id=session_id,
            )
        except InvalidChatGender:
            await self._send_error("invalid_gender")
            return

        self.session_id = session_id
        self.session_active = True
        self.search_available_at = 0.0

        await sync_to_async(self.participant_storage.save)(
            self.channel_name,
            participant,
        )

        await self.send_json(
            {
                "type": "started",
                "session_id": self.session_id,
                "chat_gender": participant["chat_gender"],
            }
        )

        await self._find_partner()

    async def _handle_search(self):
        """Продолжить поиск после cooldown."""

        if not self.session_active:
            await self._send_error("no_active_session")
            return

        if self.in_room:
            return

        remaining = self._cooldown_remaining()

        if remaining > 0:
            await self.send_json(
                {
                    "type": "cooldown",
                    "seconds": remaining,
                }
            )
            return

        await self._find_partner()

    async def _handle_next(self):
        """Разорвать пару и начать трёхсекундный cooldown."""

        if not self.session_active:
            return

        await sync_to_async(self.matchmaking.leave_queue)(self.channel_name)

        await self._end_current_room(
            notify_partner=True,
        )

        await self._enter_cooldown(
            event_type="cooldown",
        )

    async def _handle_stop(self):
        """Остановить matchmaking-сессию и очистить Redis."""

        if not self.session_active:
            await self.send_json(
                {
                    "type": "stopped",
                }
            )
            return

        await self._finish_session(
            notify_partner=True,
        )

        await self.send_json(
            {
                "type": "stopped",
            }
        )

    async def _handle_connected(self):
        """Разрешить текстовый чат для текущей пары."""

        if not self.session_active or not self.in_room or not self.room_id:
            return

        self.media_connected = True

    async def _handle_signaling(self, data):
        """Маршрутизировать WebRTC signaling партнёру или модератору."""

        if data.get("from_moderator_reply"):
            await self._send_signaling_to_moderator(data)
            return

        if not self.session_active or not self.in_room or not self.partner_channel:
            return

        await self.channel_layer.send(
            self.partner_channel,
            {
                "type": "signaling.message",
                "payload": data,
            },
        )

    async def _send_signaling_to_moderator(self, data):
        """Передать ответ отдельного moderator WebRTC-соединения."""

        if not self.room_id:
            return

        payload = {
            **data,
            # Channel identity определяет сервер, а не браузер.
            "answering_channel": self.channel_name,
        }

        await self.channel_layer.group_send(
            f"moderate_{self.room_id}",
            {
                "type": "signaling.message",
                "payload": payload,
            },
        )

    async def _handle_ready(self):
        """Сообщить caller-у, что callee готов принять WebRTC offer."""

        if not self.in_room or not self.partner_channel:
            return

        await self.channel_layer.send(
            self.partner_channel,
            {
                "type": "signaling.message",
                "payload": {
                    "type": "ready_to_connect",
                },
            },
        )

    async def _handle_chat_message(self, data):
        """Передать сообщение только после подтверждённого WebRTC connect."""

        if not self.session_active or not self.media_connected or not self.partner_channel or not self.room_id:
            return

        text = str(data.get("text", "")).strip()[:500]

        if not text:
            return

        await self.channel_layer.send(
            self.partner_channel,
            {
                "type": "signaling.message",
                "payload": {
                    "type": "chat_message",
                    "text": text,
                    "sender": "partner",
                },
            },
        )

    async def _find_partner(self):
        """Встать в очередь или создать комнату с валидным участником."""

        if not self.session_active:
            return

        self.in_room = False
        self.media_connected = False
        self.search_available_at = 0.0

        await sync_to_async(self.matchmaking.leave_queue)(self.channel_name)

        while self.session_active:
            partner = await sync_to_async(self.matchmaking.join_queue)(self.channel_name)

            # Отправляем waiting только после завершения операции с очередью.
            # Так клиент, получив status=waiting, видит уже актуальное
            # состояние matchmaking, а не промежуточное.
            await self.send_json(
                {
                    "type": "status",
                    "message": "waiting",
                }
            )

            if not partner:
                return

            partner_participant = await sync_to_async(self.participant_storage.get)(partner)

            if not partner_participant:
                continue

            await self._create_room(
                partner,
                partner_participant,
            )
            return

    async def _create_room(
        self,
        partner_channel: str,
        partner_participant: dict,
    ):
        """Создать комнату со snapshot metadata обоих участников."""

        caller_participant = await sync_to_async(self.participant_storage.get)(self.channel_name)

        if not caller_participant:
            await self._finish_session(
                notify_partner=False,
            )
            return

        self.room_id = str(uuid.uuid4())
        self.partner_channel = partner_channel
        self.in_room = True
        self.media_connected = False

        await sync_to_async(self.room_storage.create_room)(
            self.room_id,
            self.channel_name,
            partner_channel,
            caller_participant=caller_participant,
            callee_participant=partner_participant,
        )

        await self.send_json(
            {
                "type": "matched",
                "room_id": self.room_id,
                "role": "caller",
            }
        )

        await self.channel_layer.send(
            partner_channel,
            {
                "type": "room.matched",
                "room_id": self.room_id,
                "caller_channel": self.channel_name,
            },
        )

    async def _end_current_room(
        self,
        *,
        notify_partner: bool,
    ):
        """Удалить текущую комнату и сбросить локальное состояние."""

        old_partner = self.partner_channel
        old_room = self.room_id

        self.partner_channel = None
        self.room_id = None
        self.in_room = False
        self.media_connected = False

        if old_room:
            await sync_to_async(self.room_storage.delete_room)(old_room)

        if notify_partner and old_partner:
            await self.channel_layer.send(
                old_partner,
                {
                    "type": "partner.disconnected",
                },
            )

    async def _enter_cooldown(
        self,
        *,
        event_type: str,
    ):
        """Запретить повторный поиск на COOLDOWN_SECONDS."""

        self.search_available_at = time.monotonic() + COOLDOWN_SECONDS

        await self.send_json(
            {
                "type": event_type,
                "seconds": COOLDOWN_SECONDS,
            }
        )

    def _cooldown_remaining(self) -> int:
        """Вернуть оставшееся время cooldown, округлённое вверх."""

        return max(
            0,
            math.ceil(self.search_available_at - time.monotonic()),
        )

    async def _finish_session(
        self,
        *,
        notify_partner: bool,
    ):
        """Очистить очередь, room и participant metadata."""

        await sync_to_async(self.matchmaking.leave_queue)(self.channel_name)

        await self._end_current_room(
            notify_partner=notify_partner,
        )

        await sync_to_async(self.participant_storage.delete)(self.channel_name)

        self.session_id = None
        self.session_active = False
        self.search_available_at = 0.0

    async def _send_error(
        self,
        code: str,
    ):
        """Отправить клиенту машинный код ошибки."""

        await self.send_json(
            {
                "type": "error",
                "code": code,
            }
        )

    async def send_json(self, data: dict):
        """Отправить JSON-сообщение браузеру."""

        await self.send(text_data=json.dumps(data))
