# src/messenger/selectors/participant.py

"""
Selectors для работы с участниками диалогов.

Модуль отвечает только за получение данных из базы.
"""

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

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
