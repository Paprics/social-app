# src/messenger/selectors/dialog.py

"""
Selectors для работы с диалогами.

Модуль отвечает только за получение диалогов из базы данных.
Изменение данных выполняется через services.
"""

from django.contrib.auth import get_user_model
from django.db.models import (
    Count,
    F,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Subquery,
    Value,
)
from django.db.models.functions import Coalesce

from messenger.models import Dialog, Participant
from messenger.models.dialog import DialogType

User = get_user_model()


def get_user_dialogs(user: User) -> QuerySet[Dialog]:
    """
    Возвращает активные диалоги пользователя.

    Диалоги сортируются по времени последней активности:
    самый недавно активный диалог отображается первым.

    Направление последнего сообщения значения не имеет:
    входящее и исходящее сообщение одинаково обновляют
    активность соответствующего диалога.

    Для каждого диалога вычисляет количество непрочитанных
    входящих сообщений с учётом last_read_message текущего
    участника.

    Архивированные и неактивные участия исключаются.
    """

    current_participant = Participant.objects.filter(
        dialog_id=OuterRef("pk"),
        user=user,
    )

    return (
        Dialog.objects.filter(
            participants__user=user,
            participants__is_active=True,
            participants__is_archived=False,
        )
        .annotate(
            _last_read_message_id=Subquery(
                current_participant.values(
                    "last_read_message_id",
                )[:1]
            )
        )
        .annotate(
            unread_count=Count(
                "messages",
                filter=(
                    ~Q(messages__sender=user)
                    & Q(
                        messages__id__gt=Coalesce(
                            F("_last_read_message_id"),
                            Value(0),
                        )
                    )
                ),
                distinct=True,
            )
        )
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
        .order_by(
            "-last_activity_at",
            "-id",
        )
    )


def get_dialog(dialog_id: int) -> Dialog:
    """
    Возвращает диалог по внутреннему ID.

    Используется для создания сообщений,
    проверки доступа и WebSocket-операций.
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
    Возвращает диалог по публичному ID.

    Публичный идентификатор используется в URL вместо
    внутреннего первичного ключа диалога.
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

    Предзагружает участников, отправителей сообщений
    и вложения для отображения страницы чата.

    Диалог определяется по публичному ID.
    """

    return Dialog.objects.prefetch_related(
        "participants__user",
        "messages__sender",
        "messages__attachments",
    ).get(
        public_id=public_id,
    )


def get_private_dialog(
    user1: User,
    user2: User,
) -> Dialog | None:
    """
    Возвращает существующий приватный диалог
    между двумя пользователями.

    Групповые диалоги исключаются из поиска.

    Если приватный диалог отсутствует,
    возвращает None.
    """

    return (
        Dialog.objects.filter(
            dialog_type=DialogType.PRIVATE,
            participants__user=user1,
            participants__is_active=True,
        )
        .filter(
            participants__user=user2,
            participants__is_active=True,
        )
        .distinct()
        .first()
    )
