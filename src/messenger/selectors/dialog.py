# src/messenger/selectors/dialog.py

"""
Selectors для работы с диалогами.

Модуль отвечает только за получение диалогов из базы данных.
Изменение данных выполняется через services.
"""

from django.db.models import OuterRef, Subquery, Count, IntegerField
from django.contrib.auth import get_user_model
from django.db.models import (
    Prefetch,
    QuerySet,
    Count,
    Q,
)
from messenger.models import Dialog, Participant, Message

User = get_user_model()


def get_user_dialogs(user: User) -> QuerySet[Dialog]:

    return (
        Dialog.objects.filter(
            participants__user=user,
            participants__is_active=True,
            participants__is_archived=False,
        )
        .annotate(unread_count=Count("messages", filter=Q(messages__id__gt=0) & ~Q(messages__sender=user)))
        .select_related(
            "last_message",
            "last_message__sender",
        )
        .prefetch_related(
            Prefetch(
                "participants",
                queryset=Participant.objects.select_related(
                    "user",
                    "user__profile",
                    "last_read_message",
                ),
            ),
        )
        .distinct()
    )


def get_dialog(dialog_id: int) -> Dialog:
    """
    Получение диалога по внутреннему ID.

    Используется для:
    - создания сообщений;
    - проверки доступа;
    - WebSocket.
    """

    return (
        Dialog.objects.prefetch_related(
            "participants__user__profile",
        )
        .select_related(
            "last_message",
        )
        .get(
            pk=dialog_id,
        )
    )


def get_dialog_by_public_id(public_id: str) -> Dialog:
    """
    Получение диалога по публичному ID из URL.
    """

    return (
        Dialog.objects.prefetch_related(
            "participants__user__profile",
        )
        .select_related(
            "last_message",
        )
        .get(
            public_id=public_id,
        )
    )


def get_dialog_with_messages(public_id: str) -> Dialog:
    """
    Возвращает диалог вместе с сообщениями.

    Используется при открытии страницы чата.

    URL работает через public_id.
    Внутренний id не используется.
    """

    return Dialog.objects.prefetch_related(
        "participants__user",
        "messages__sender",
        "messages__attachments",
    ).get(
        public_id=public_id,
    )


def get_private_dialog(user1, user2):
    """
    Возвращает существующий приватный диалог
    между двумя пользователями.

    Если диалог отсутствует —
    возвращает None.
    """

    return (
        Dialog.objects.filter(
            participants__user=user1,
        )
        .filter(
            participants__user=user2,
        )
        .distinct()
        .first()
    )
