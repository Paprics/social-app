# src/messenger/selectors/message.py

"""
Selectors for messenger messages.

Этот модуль отвечает только за получение сообщений из базы данных.

Здесь НЕ должно быть:
- создания сообщений;
- изменения сообщений;
- проверки прав;
- отправки WebSocket событий.

Вся бизнес-логика находится в services.
"""

from django.db.models import QuerySet

from messenger.models import Message

MESSAGE_BATCH_SIZE = 30


def _message_queryset() -> QuerySet[Message]:
    """
    Возвращает базовый queryset сообщений.

    Здесь централизованы оптимизации связанных объектов.
    """

    return Message.objects.select_related(
        "sender",
        "sender__profile",
    ).prefetch_related(
        "attachments",
    )


def get_dialog_messages(dialog_id: int) -> QuerySet[Message]:
    """
    Возвращает все сообщения конкретного диалога.

    Не используется для первоначальной загрузки страницы чата.
    Предназначен для внутренних сценариев, где действительно
    требуется полная история.
    """

    return (
        _message_queryset()
        .filter(
            dialog_id=dialog_id,
        )
        .order_by("-id")
    )


def get_messages_before(
    dialog_id: int,
    message_id: int,
    limit: int = MESSAGE_BATCH_SIZE,
) -> list[Message]:
    """
    Возвращает порцию сообщений старше указанного сообщения.

    Сообщения выбираются от новых к старым для эффективного
    cursor pagination, после чего разворачиваются в естественный
    порядок отображения: от старого к новому.
    """

    messages = list(
        _message_queryset()
        .filter(
            dialog_id=dialog_id,
            id__lt=message_id,
        )
        .order_by("-id")[:limit]
    )

    messages.reverse()

    return messages


def get_latest_messages(
    dialog_id: int,
    limit: int = MESSAGE_BATCH_SIZE,
) -> list[Message]:
    """
    Возвращает последние сообщения диалога.

    В браузер передается только последняя порция сообщений,
    отсортированная от старого к новому.
    """

    messages = list(
        _message_queryset()
        .filter(
            dialog_id=dialog_id,
        )
        .order_by("-id")[:limit]
    )

    messages.reverse()

    return messages


def has_messages_before(
    dialog_id: int,
    message_id: int,
) -> bool:
    """
    Проверяет наличие сообщений старше указанного сообщения.
    """

    return Message.objects.filter(
        dialog_id=dialog_id,
        id__lt=message_id,
    ).exists()


def get_unread_messages(
    dialog_id: int,
    last_read_message_id: int | None,
) -> QuerySet[Message]:
    """
    Возвращает непрочитанные сообщения.

    Логика основана на поле Participant.last_read_message.

    Если пользователь ещё ничего не прочитал,
    возвращаются все сообщения диалога.
    """

    queryset = _message_queryset().filter(
        dialog_id=dialog_id,
    )

    if last_read_message_id:
        queryset = queryset.filter(
            id__gt=last_read_message_id,
        )

    return queryset.order_by("id")


def get_message(message_id: int) -> Message:
    """
    Возвращает одно сообщение.

    Используется для отображения, редактирования,
    удаления и HTMX partial.
    """

    return (
        Message.objects.select_related(
            "dialog",
            "sender",
        )
        .prefetch_related(
            "attachments",
        )
        .get(
            pk=message_id,
        )
    )
