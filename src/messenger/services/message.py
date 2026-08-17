# src/messenger/services/message.py

"""
Сервис работы с сообщениями.

Отвечает за:
- создание сообщений;
- удаление сообщений;
- отправку WebSocket событий.

Вся бизнес-логика сообщений находится здесь.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from messenger.models import Dialog, Message, Participant


class MessageService:
    """Бизнес-логика сообщений."""

    @staticmethod
    @transaction.atomic
    def create_message(
        *,
        dialog: Dialog,
        sender,
        text: str,
    ) -> Message:
        """Создает новое сообщение."""

        message = Message.objects.create(
            dialog=dialog,
            sender=sender,
            text=text,
        )

        dialog.last_message = message
        dialog.last_activity_at = message.created_at

        dialog.save(
            update_fields=[
                "last_message",
                "last_activity_at",
                "updated_at",
            ],
        )

        return message

    @staticmethod
    @transaction.atomic
    def delete_message(
        *,
        message: Message,
    ) -> int:
        """
        Полностью удаляет сообщение из базы.

        Возвращает ID удаленного сообщения.
        """

        message_id = message.id

        message.delete()

        return message_id

    @staticmethod
    def notify_message_created(
        *,
        message: Message,
    ) -> None:
        """Отправляет событие создания сообщения."""

        channel_layer = get_channel_layer()

        async_to_sync(
            channel_layer.group_send,
        )(
            f"dialog_{message.dialog_id}",
            {
                "type": "chat_message",
                "message_id": message.id,
                "sender_id": message.sender_id,
            },
        )

        MessageService.notify_inbox_changed(
            dialog_id=message.dialog_id,
            reason="message.created",
        )


    @staticmethod
    def notify_message_deleted(
        *,
        dialog_id: int,
        message_id: int,
    ) -> None:
        """Отправляет событие удаления сообщения."""

        channel_layer = get_channel_layer()

        async_to_sync(
            channel_layer.group_send,
        )(
            f"dialog_{dialog_id}",
            {
                "type": "message_deleted",
                "message_id": message_id,
            },
        )

        MessageService.notify_inbox_changed(
            dialog_id=dialog_id,
            reason="message.deleted",
        )

    @staticmethod
    def notify_inbox_changed(
        *,
        dialog_id: int,
        reason: str,
    ) -> None:
        channel_layer = get_channel_layer()

        user_ids = (
            Participant.objects
            .filter(
                dialog_id=dialog_id,
                is_active=True,
            )
            .values_list(
                "user_id",
                flat=True,
            )
        )

        for user_id in user_ids:
            async_to_sync(
                channel_layer.group_send,
            )(
                f"messenger_user_{user_id}",
                {
                    "type": "inbox_changed",
                    "reason": reason,
                },
            )
