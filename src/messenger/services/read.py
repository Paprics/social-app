# src/messenger/services/read.py

"""
Business logic for message read status.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

from messenger.models import Message, Participant


class ReadService:
    """Сервис управления read cursor участника диалога."""

    @staticmethod
    @transaction.atomic
    def mark_read_up_to(
        *,
        dialog_id: int,
        user_id: int,
        message_id: int,
    ) -> bool:
        """
        Атомарно продвигает read cursor только вперёд.

        Participant перечитывается под SELECT ... FOR UPDATE, поэтому
        решение принимается по актуальному состоянию БД, а не по
        потенциально устаревшему объекту из caller'а.

        Возвращает True только если cursor действительно изменился.
        """

        message = (
            Message.objects
            .only(
                "id",
                "dialog_id",
            )
            .filter(
                pk=message_id,
                dialog_id=dialog_id,
            )
            .first()
        )

        if message is None:
            return False

        participant = (
            Participant.objects
            .select_for_update()
            .only(
                "id",
                "dialog_id",
                "user_id",
                "last_read_message_id",
            )
            .filter(
                dialog_id=dialog_id,
                user_id=user_id,
                is_active=True,
            )
            .first()
        )

        if participant is None:
            return False

        current_message_id = participant.last_read_message_id

        if (
            current_message_id is not None
            and current_message_id >= message.id
        ):
            return False

        participant.last_read_message_id = message.id
        participant.save(
            update_fields=[
                "last_read_message",
            ],
        )

        transaction.on_commit(
            lambda: ReadService.notify_messages_read(
                dialog_id=dialog_id,
                reader_id=user_id,
                last_read_message_id=message.id,
            ),
        )

        return True

    @staticmethod
    def mark_as_read(
        participant: Participant,
        message: Message,
    ) -> Participant:
        """
        Совместимый adapter старого API.

        Business rule находится только в mark_read_up_to().
        После миграции всех callers этот метод можно удалить.
        """

        if participant.dialog_id != message.dialog_id:
            raise ValueError(
                "Message does not belong to participant dialog.",
            )

        ReadService.mark_read_up_to(
            dialog_id=participant.dialog_id,
            user_id=participant.user_id,
            message_id=message.id,
        )

        participant.refresh_from_db(
            fields=[
                "last_read_message",
            ],
        )

        return participant

    @staticmethod
    def notify_messages_read(
        *,
        dialog_id: int,
        reader_id: int,
        last_read_message_id: int,
    ) -> None:
        """Уведомляет участников диалога об изменении read cursor."""

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


        async_to_sync(
            channel_layer.group_send,
        )(
            f"messenger_user_{reader_id}",
            {
                "type": "inbox_changed",
                "reason": "messages.read",
            },
        )

    @staticmethod
    @transaction.atomic
    def reset_read_state(
        participant: Participant,
    ) -> Participant:
        """Сбрасывает статус прочтения участника."""

        participant = (
            Participant.objects
            .select_for_update()
            .get(
                pk=participant.pk,
            )
        )

        if participant.last_read_message_id is None:
            return participant

        participant.last_read_message = None
        participant.save(
            update_fields=[
                "last_read_message",
            ],
        )

        return participant