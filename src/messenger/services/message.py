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

        transaction.on_commit(
            lambda: MessageService.notify_message_created(
                message=message,
            ),
        )

        return message

    @staticmethod
    @transaction.atomic
    def delete_message(
        *,
        message: Message,
    ) -> int:
        """
        Полностью удаляет сообщение и сохраняет согласованность
        dialog metadata и read cursors.

        Возвращает ID удаленного сообщения.
        """

        locked_message = (
            Message.objects
            .select_for_update()
            .get(
                pk=message.pk,
            )
        )

        dialog = (
            Dialog.objects
            .select_for_update()
            .get(
                pk=locked_message.dialog_id,
            )
        )

        previous_message = (
            Message.objects
            .filter(
                dialog_id=dialog.id,
                id__lt=locked_message.id,
            )
            .order_by("-id")
            .only(
                "id",
                "created_at",
            )
            .first()
        )

        previous_message_id = (
            previous_message.id
            if previous_message is not None
            else None
        )

        Participant.objects.filter(
            dialog_id=dialog.id,
            last_read_message_id=locked_message.id,
        ).update(
            last_read_message_id=previous_message_id,
        )

        message_id = locked_message.id
        was_last_message = dialog.last_message_id == message_id

        locked_message.delete()

        if was_last_message:
            last_activity_at = (
                previous_message.created_at
                if previous_message is not None
                else dialog.created_at
            )

            Dialog.objects.filter(
                pk=dialog.id,
            ).update(
                last_message_id=previous_message_id,
                last_activity_at=last_activity_at,
            )

        transaction.on_commit(
            lambda: MessageService.notify_message_deleted(
                dialog_id=dialog.id,
                message_id=message_id,
            ),
        )

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
