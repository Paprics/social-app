# src/messenger/selectors/participant.py

"""
Selectors для работы с участниками диалогов.

Модуль отвечает только за получение данных из базы.
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, F, Q, QuerySet

from messenger.models import Participant

User = get_user_model()


def get_dialog_participants(
    dialog_id: int,
) -> QuerySet[Participant]:
    """
    Возвращает список участников диалога.
    """

    return Participant.objects.filter(
        dialog_id=dialog_id,
        is_active=True,
    ).select_related(
        "user",
        "user__profile",
    )


def get_user_participation(
    dialog_id: int,
    user: User,
) -> Participant:
    """
    Возвращает запись участника диалога.

    Используется для:
    - проверки доступа;
    - получения настроек диалога;
    - работы с last_read_message.
    """

    return Participant.objects.select_related(
        "dialog",
        "user",
        "last_read_message",
    ).get(
        dialog_id=dialog_id,
        user=user,
        is_active=True,
    )


def get_unread_messages_count(user: User) -> int:
    """Возвращает общее количество непрочитанных входящих сообщений."""

    result = (
        Participant.objects.filter(
            user=user,
            is_active=True,
            is_archived=False,
        )
        .aggregate(
            unread_count=Count(
                "dialog__messages",
                filter=(
                    ~Q(dialog__messages__sender=user)
                    & (
                        Q(last_read_message_id__isnull=True)
                        | Q(
                            dialog__messages__id__gt=F(
                                "last_read_message_id",
                            )
                        )
                    )
                ),
            )
        )
    )

    return result["unread_count"] or 0


def is_user_participant(
    dialog_id: int,
    user_id: int,
) -> bool:
    """
    Проверяет, является ли пользователь
    активным участником диалога.
    """

    return Participant.objects.filter(
        dialog_id=dialog_id,
        user_id=user_id,
        is_active=True,
    ).exists()
