# src/video_chat/consumers/moderator.py

"""WebSocket consumer для модерации активных видеочат-комнат."""

import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from video_chat.services.room_storage import RoomStorage
from video_chat.services.websocket_message import (
    InvalidWebSocketMessage,
    WebSocketMessageTooLarge,
    decode_websocket_message,
)


class ModeratorConsumer(AsyncWebsocketConsumer):
    """Позволяет staff-модератору наблюдать и управлять комнатой."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.room_id = None
        self.room_group = None
        self.room_storage = RoomStorage()

    async def connect(self):
        """Подключить staff-модератора к существующей комнате."""

        user = self.scope.get("user")

        if user is None or not user.is_authenticated or not user.is_staff:
            await self.close(code=4403)
            return

        self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
        self.room_group = f"moderate_{self.room_id}"

        room_meta = await self._get_room()

        if not room_meta:
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
                "caller": room_meta["caller"],
                "callee": room_meta["callee"],
            }
        )

    async def disconnect(self, close_code):
        """Удалить модератора из channel group комнаты."""

        if self.room_group:
            await self.channel_layer.group_discard(
                self.room_group,
                self.channel_name,
            )

    async def receive(
        self,
        text_data=None,
        bytes_data=None,
    ):
        """Проверить и обработать команду модератора."""

        try:
            data = decode_websocket_message(
                text_data
            )
        except WebSocketMessageTooLarge:
            await self._send_error(
                "message_too_large"
            )
            await self.close(
                code=4409
            )
            return
        except InvalidWebSocketMessage:
            await self._send_error(
                "invalid_payload"
            )
            return

        msg_type = data.get(
            "type"
        )

        if msg_type in (
            "offer",
            "answer",
            "ice_candidate",
        ):
            await self._handle_signaling(data)
            return

        if msg_type == "kick":
            await self._handle_kick(data)
            return

        await self._send_error(
            "unsupported_type"
        )

    async def _handle_signaling(self, data):
        """Передать moderator WebRTC signaling участнику активной комнаты."""

        target = data.get("target")
        room_meta = await self._get_room()

        if not room_meta:
            await self._close_stale_room()
            return

        if not self._is_room_participant(
            target,
            room_meta,
        ):
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
        """Отправить команду отключения участнику активной комнаты."""

        target = data.get("target")
        room_meta = await self._get_room()

        if not room_meta:
            await self._close_stale_room()
            return

        if not self._is_room_participant(
            target,
            room_meta,
        ):
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

    async def _get_room(self) -> dict | None:
        """Перечитать актуальную комнату из Redis."""

        if not self.room_id:
            return None

        return await sync_to_async(
            self.room_storage.get_room
        )(
            self.room_id
        )

    @staticmethod
    def _is_room_participant(
        target: str | None,
        room_meta: dict,
    ) -> bool:
        """Проверить принадлежность channel_name актуальной комнате."""

        if not target:
            return False

        return target in {
            room_meta["caller"],
            room_meta["callee"],
        }

    async def _close_stale_room(self):
        """Закрыть moderator WebSocket завершённой комнаты."""

        await self.send_json(
            {
                "type": "room_closed",
            }
        )
        await self.close()

    async def signaling_message(self, event):
        """Передать signaling от участника браузеру модератора."""

        await self.send_json(
            {
                "payload": event["payload"],
            }
        )

    async def room_closed(self, event):
        """Закрыть moderator WebSocket после завершения комнаты."""

        await self._close_stale_room()

    async def _send_error(
        self,
        code: str,
    ):
        """Отправить модератору машинный код ошибки."""

        await self.send_json(
            {
                "type": "error",
                "code": code,
            }
        )

    async def send_json(self, data: dict):
        """Отправить JSON-сообщение браузеру модератора."""

        await self.send(text_data=json.dumps(data))
