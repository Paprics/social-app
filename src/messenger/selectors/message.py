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


def _message_queryset() -> QuerySet[Message]:
    """
    Базовый queryset сообщений.

    Здесь централизованы:
    - исключение удалённых сообщений;
    - оптимизация связанных объектов.
    """

    return Message.objects.select_related(
        "sender",
        "sender__profile",
    ).prefetch_related(
        "attachments",
    )


def get_dialog_messages(dialog_id: int) -> QuerySet[Message]:
    """
    Возвращает сообщения конкретного диалога.

    Используется для:
    - открытия истории сообщений;
    - первоначальной загрузки чата.
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
    limit: int = 50,
) -> QuerySet[Message]:
    """
    Возвращает сообщения старше указанного сообщения.

    Используется для cursor pagination.

    Пример:

    Загружены сообщения до ID 500.
    Пользователь листает вверх.
    Получаем:

    id < 500

    limit = 50
    """

    return (
        _message_queryset()
        .filter(
            dialog_id=dialog_id,
            id__lt=message_id,
        )
        .order_by("-id")[:limit]
    )


def get_latest_messages(
    dialog_id: int,
    limit: int = 50,
) -> QuerySet[Message]:
    """
    Возвращает последние сообщения диалога.

    Используется при первом открытии чата.
    """

    return (
        _message_queryset()
        .filter(
            dialog_id=dialog_id,
        )
        .order_by("id")[:limit]
    )


def get_unread_messages(
    dialog_id: int,
    last_read_message_id: int | None,
) -> QuerySet[Message]:
    """
    Возвращает непрочитанные сообщения.

    Логика основана на поле:
    Participant.last_read_message.

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

    Используется:
    - отображение сообщения;
    - редактирование;
    - удаление;
    - HTMX partial.
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
