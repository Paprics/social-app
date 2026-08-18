# src/video_chat/consumers/moderator.py

"""WebSocket consumer для модерации активных видеочат-комнат."""

import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from video_chat.services.room_storage import RoomStorage


class ModeratorConsumer(AsyncWebsocketConsumer):
    """Позволяет staff-модератору наблюдать и управлять комнатой."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.room_id = None
        self.room_group = None
        self.room_storage = RoomStorage()
        self.room_meta = None

    async def connect(self):
        """Подключить staff-модератора к существующей комнате."""

        user = self.scope.get("user")

        # Проверяем права до чтения комнаты, чтобы посторонний пользователь
        # не мог использовать WebSocket для проверки существования room_id.
        if user is None or not user.is_authenticated or not user.is_staff:
            await self.close(code=4403)
            return

        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group = f"moderate_{self.room_id}"

        self.room_meta = await sync_to_async(self.room_storage.get_room)(self.room_id)

        if not self.room_meta:
            await self.close(code=4404)
            return

        await self.channel_layer.group_add(
            self.room_group,
            self.channel_name,
        )

        await self.accept()

        await self.send_json(
            {
                "type": "room_info",
                "room_id": self.room_id,
                "caller": self.room_meta["caller"],
                "callee": self.room_meta["callee"],
            }
        )

    async def disconnect(self, close_code):
        """Удалить модератора из channel group комнаты."""

        if self.room_group:
            await self.channel_layer.group_discard(
                self.room_group,
                self.channel_name,
            )

    async def receive(self, text_data):
        """Обработать signaling или команду модератора."""

        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type in ("offer", "answer", "ice_candidate"):
            await self._handle_signaling(data)
            return

        if msg_type == "kick":
            await self._handle_kick(data)

    async def _handle_signaling(self, data):
        """Передать moderator WebRTC signaling участнику комнаты."""

        target = data.get("target")

        if not self._is_room_participant(target):
            return

        await self.channel_layer.send(
            target,
            {
                "type": "signaling.message",
                "payload": {
                    **data,
                    "from_moderator": True,
                },
            },
        )

    async def _handle_kick(self, data):
        """Отправить команду отключения участнику текущей комнаты."""

        target = data.get("target")

        if not self._is_room_participant(target):
            return

        await self.channel_layer.send(
            target,
            {
                "type": "moderator.kick",
            },
        )

        await self.send_json(
            {
                "type": "kick_sent",
                "target": target,
            }
        )

    def _is_room_participant(self, target: str | None) -> bool:
        """Проверить, принадлежит ли channel_name текущей комнате."""

        if not target or not self.room_meta:
            return False

        return target in {
            self.room_meta["caller"],
            self.room_meta["callee"],
        }

    async def signaling_message(self, event):
        """Передать signaling от участника браузеру модератора."""

        await self.send_json(
            {
                "payload": event["payload"],
            }
        )

    async def send_json(self, data: dict):
        """Отправить JSON-сообщение браузеру модератора."""

        await self.send(text_data=json.dumps(data))
