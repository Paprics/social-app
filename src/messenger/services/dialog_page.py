# src/messenger/services/dialog_page.py

"""
Сервис подготовки контекста страницы диалога.
"""

from django.contrib.auth import get_user_model

from messenger.models import Dialog
from messenger.selectors.message import (
    MESSAGE_BATCH_SIZE,
    get_latest_messages,
    has_messages_before,
)

User = get_user_model()


class DialogPageService:
    """
    Формирует данные для страницы диалога.
    """

    @staticmethod
    def build(
        dialog: Dialog,
        request,
    ) -> dict:
        """
        Собирает контекст страницы диалога.

        Первоначально загружает только последнюю
        порцию сообщений.
        """

        request_user: User = request.user

        other_user = None

        if dialog.is_private:
            for participant in dialog.participants.all():
                if participant.user_id != request_user.id:
                    other_user = participant.user
                    break

        show_online_status = False
        is_online = False
        last_seen = None

        if other_user:
            show_online_status = (
                other_user.settings.show_online_status
            )

            if show_online_status:
                is_online = other_user.profile.is_online
                last_seen = other_user.profile.last_seen

        messages = get_latest_messages(
            dialog.id,
            limit=MESSAGE_BATCH_SIZE,
        )

        oldest_message_id = (
            messages[0].id
            if messages
            else None
        )

        has_older_messages = (
            has_messages_before(
                dialog.id,
                oldest_message_id,
            )
            if oldest_message_id
            else False
        )

        return {
            "other_user": other_user,
            "messages": messages,
            "oldest_message_id": oldest_message_id,
            "has_older_messages": has_older_messages,
            "show_online_status": show_online_status,
            "is_online": is_online,
            "last_seen": last_seen,
        }