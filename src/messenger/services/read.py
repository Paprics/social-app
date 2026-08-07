# src/messenger/services/read.py

"""
Business logic for message read status.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from messenger.models import Message, Participant


class ReadService:
    """
    Сервис отметки сообщений как прочитанных.
    """

    @staticmethod
    @transaction.atomic
    def mark_as_read(
        participant: Participant,
        message: Message,
    ) -> Participant:
        """
        Обновляет последнее прочитанное сообщение участника.

        Значение обновляется только вперёд. После успешной
        транзакции отправляется WebSocket-событие в группу диалога.
        """

        if participant.dialog_id != message.dialog_id:
            raise ValueError(
                "Message does not belong to participant dialog.",
            )

        current_message_id = participant.last_read_message_id

        if (
            current_message_id is not None
            and current_message_id >= message.id
        ):
            return participant

        participant.last_read_message = message
        participant.save(
            update_fields=[
                "last_read_message",
            ],
        )

        transaction.on_commit(
            lambda: ReadService.notify_messages_read(
                dialog_id=participant.dialog_id,
                reader_id=participant.user_id,
                last_read_message_id=message.id,
            ),
        )

        return participant

    @staticmethod
    def notify_messages_read(
        *,
        dialog_id: int,
        reader_id: int,
        last_read_message_id: int,
    ) -> None:
        """
        Уведомляет участников диалога об изменении статуса прочтения.
        """

        channel_layer = get_channel_layer()

        async_to_sync(
            channel_layer.group_send,
        )(
            f"dialog_{dialog_id}",
            {
                "type": "messages_read",
                "reader_id": reader_id,
                "last_read_message_id": last_read_message_id,
            },
        )

    @staticmethod
    @transaction.atomic
    def reset_read_state(
        participant: Participant,
    ) -> Participant:
        """
        Сбрасывает статус прочтения участника.
        """

        if participant.last_read_message_id is None:
            return participant

        participant.last_read_message = None
        participant.save(
            update_fields=[
                "last_read_message",
            ],
        )

        return participant