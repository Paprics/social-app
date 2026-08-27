from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from messenger.selectors.participant import get_unread_messages_count


class InboxConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]

        if not user.is_authenticated:
            await self.close()
            return

        self.group_name = f"messenger_user_{user.id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

    async def receive_json(self, content, **kwargs):
        if content.get("type") != "inbox.sync":
            return

        await self.send_inbox_state(
            reason="sync",
        )

    async def inbox_changed(self, event):
        await self.send_inbox_state(
            reason=event.get(
                "reason",
                "unknown",
            ),
        )

    async def send_inbox_state(
        self,
        *,
        reason: str,
    ) -> None:
        unread_count = await self._get_unread_messages_count()

        await self.send_json(
            {
                "type": "inbox.changed",
                "reason": reason,
                "unread_count": unread_count,
            }
        )

    @database_sync_to_async
    def _get_unread_messages_count(self) -> int:
        return get_unread_messages_count(
            self.scope["user"],
        )
