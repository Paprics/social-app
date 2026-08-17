# src/messenger/consumers/dialog_consumer.py

"""
WebSocket consumer для диалогов messenger.

Отвечает за:
- подключение пользователя;
- проверку доступа;
- подписку на группу диалога;
- доставку realtime-событий;
- отметку входящего сообщения прочитанным,
  если соответствующий диалог открыт.
"""

import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

from messenger.models import Dialog
from messenger.services.dialog import DialogService
from messenger.services.read import ReadService

logger = logging.getLogger(__name__)


class DialogConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer открытого диалога."""

    async def connect(self):
        """Подключает пользователя к realtime-группе диалога."""

        user = self.scope["user"]

        if isinstance(user, AnonymousUser):
            await self.close()
            return

        self.public_id = self.scope["url_route"]["kwargs"]["public_id"]

        try:
            self.dialog_id = await self.get_dialog_id(
                self.public_id,
            )
        except Dialog.DoesNotExist:
            logger.warning(
                "Dialog not found: %s",
                self.public_id,
            )

            await self.close()
            return

        has_access = await self.check_access(
            self.dialog_id,
            user.id,
        )

        if not has_access:
            logger.warning(
                "User %s has no access to dialog %s",
                user.id,
                self.dialog_id,
            )

            await self.close()
            return

        self.group_name = f"dialog_{self.dialog_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        logger.info(
            "Dialog websocket connected: %s",
            self.group_name,
        )

    async def disconnect(
        self,
        close_code,
    ):
        """Отключает пользователя от группы диалога."""

        if hasattr(
            self,
            "group_name",
        ):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

            logger.info(
                "Dialog websocket disconnected: %s (%s)",
                self.group_name,
                close_code,
            )

    async def receive_json(
        self,
        content,
        **kwargs,
    ):
        if content.get("type") != "message.read":
            return

        message_id = content.get("message_id")

        if (
            isinstance(message_id, bool)
            or not isinstance(message_id, int)
            or message_id <= 0
        ):
            return

        await self.mark_message_as_read(
            message_id=message_id,
            user_id=self.scope["user"].id,
        )

    async def chat_message(
        self,
        event,
    ):
        """Обрабатывает событие создания сообщения."""

        message_id = event["message_id"]
        sender_id = event["sender_id"]
        current_user_id = self.scope["user"].id
        is_own = sender_id == current_user_id


        await self.send_json(
            {
                "type": "message.created",
                "message_id": message_id,
                "sender_id": sender_id,
                "is_own": is_own,
            },
        )

    async def message_deleted(
        self,
        event,
    ):
        """Передает клиенту событие удаления сообщения."""

        await self.send_json(
            {
                "type": "message.deleted",
                "message_id": event["message_id"],
            },
        )

    async def dialog_deleted(
        self,
        event,
    ):
        """Tell the open client that this dialog no longer exists."""

        await self.send_json(
            {
                "type": "dialog.deleted",
            },
        )

    async def messages_read(
        self,
        event,
    ):
        """Передает read receipt только противоположной стороне."""

        current_user_id = self.scope["user"].id
        reader_id = event["reader_id"]

        if reader_id == current_user_id:
            return

        await self.send_json(
            {
                "type": "messages.read",
                "reader_id": reader_id,
                "last_read_message_id": event["last_read_message_id"],
            },
        )

    @database_sync_to_async
    def mark_message_as_read(
        self,
        *,
        message_id: int,
        user_id: int,
    ) -> None:
        """Делегирует изменение read-state application service."""

        return ReadService.mark_read_up_to(
            dialog_id=self.dialog_id,
            user_id=user_id,
            message_id=message_id,
        )

    @database_sync_to_async
    def check_access(
        self,
        dialog_id: int,
        user_id: int,
    ) -> bool:
        """Проверяет доступ пользователя к диалогу."""

        return DialogService.user_has_access(
            dialog_id=dialog_id,
            user_id=user_id,
        )

    @database_sync_to_async
    def get_dialog_id(
        self,
        public_id: str,
    ) -> int:
        """Получает внутренний ID диалога по public_id."""

        return (
            Dialog.objects.only(
                "id",
            )
            .get(
                public_id=public_id,
            )
            .id
        )
