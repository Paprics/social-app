"""
WebSocket consumer for messenger dialogs.
"""

import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import get_object_or_404

from messenger.models import Dialog
from messenger.services.dialog import DialogService

logger = logging.getLogger(__name__)


class DialogConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer диалога.

    Отвечает только за:
    - подключение пользователя;
    - проверку доступа;
    - подписку на группу диалога;
    - передачу событий клиенту.

    Бизнес-логика находится в services.
    """

    async def connect(self):

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

        if hasattr(self, "group_name"):

            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name,
            )

            logger.info(
                "Dialog websocket disconnected: %s (%s)",
                self.group_name,
                close_code,
            )

    async def chat_message(
        self,
        event,
    ):
        """
        Новое сообщение.
        """

        await self.send_json(
            {
                "type": "message.created",
                "message_id": event["message_id"],
            }
        )

    async def message_deleted(
        self,
        event,
    ):
        """
        Удаление сообщения.
        """

        await self.send_json(
            {
                "type": "message.deleted",
                "message_id": event["message_id"],
            }
        )

    @database_sync_to_async
    def check_access(
        self,
        dialog_id: int,
        user_id: int,
    ) -> bool:
        """
        Проверяет доступ пользователя к диалогу.
        """

        return DialogService.user_has_access(
            dialog_id=dialog_id,
            user_id=user_id,
        )

    @database_sync_to_async
    def get_dialog_id(
        self,
        public_id: str,
    ) -> int:
        """
        Получает ID диалога по public_id.
        """

        return (
            Dialog.objects.only(
                "id",
            )
            .get(
                public_id=public_id,
            )
            .id
        )

    async def messages_read(
        self,
        event,
    ):
        """
        Сообщения прочитаны собеседником.
        """

        await self.send_json(
            {
                "type": "messages.read",
                "reader_id": event["reader_id"],
                "last_read_message_id": event["last_read_message_id"],
            },
        )
