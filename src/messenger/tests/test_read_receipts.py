# src/messenger/tests/test_read_receipts.py

"""
Регрессионные тесты статуса прочтения сообщений.

Проверяют:
- сохранение last_read_message;
- запрет движения read cursor назад;
- отправку события о прочтении;
- преобразование consumer event в клиентское messages.read;
- правильный серверный рендер ✓ / ✓✓;
- HTTP endpoint для отметки нового сообщения прочитанным
  в уже открытом диалоге.
"""

from unittest.mock import AsyncMock, call, patch

import pytest
from asgiref.sync import async_to_sync
from django.template.loader import render_to_string
from django.urls import reverse

from messenger.consumers.dialog_consumer import DialogConsumer
from messenger.models import Dialog, Message, Participant
from messenger.services.read import ReadService
from messenger.views.dialog import DialogDetailView
from types import SimpleNamespace


@pytest.fixture
def read_receipt_state(django_user_model):
    """Создаёт приватный диалог и данные для тестов read receipt."""

    sender = django_user_model.objects.create_user(
        username="read_sender",
        password="test-password",
    )

    reader = django_user_model.objects.create_user(
        username="read_reader",
        password="test-password",
    )

    outsider = django_user_model.objects.create_user(
        username="read_outsider",
        password="test-password",
    )

    dialog = Dialog.objects.create()

    sender_participant = Participant.objects.create(
        dialog=dialog,
        user=sender,
    )

    reader_participant = Participant.objects.create(
        dialog=dialog,
        user=reader,
    )

    first_message = Message.objects.create(
        dialog=dialog,
        sender=sender,
        text="First message",
    )

    second_message = Message.objects.create(
        dialog=dialog,
        sender=sender,
        text="Second message",
    )

    return {
        "sender": sender,
        "reader": reader,
        "outsider": outsider,
        "dialog": dialog,
        "sender_participant": sender_participant,
        "reader_participant": reader_participant,
        "first_message": first_message,
        "second_message": second_message,
    }


@pytest.mark.django_db
def test_mark_read_up_to_moves_cursor_forward(
    read_receipt_state,
):
    """Прочтение нового сообщения двигает cursor вперёд."""

    participant = read_receipt_state["reader_participant"]

    message = read_receipt_state["second_message"]

    with patch.object(
        ReadService,
        "notify_messages_read",
    ):
        ReadService.mark_read_up_to(
            dialog_id=participant.dialog_id,
            user_id=participant.user_id,
            message_id=message.id,
        )

    participant.refresh_from_db()

    assert participant.last_read_message_id == message.id


@pytest.mark.django_db
def test_mark_read_up_to_never_moves_cursor_backward(
    read_receipt_state,
):
    """Старое сообщение не должно уменьшать last_read_message."""

    participant = read_receipt_state["reader_participant"]

    first_message = read_receipt_state["first_message"]

    second_message = read_receipt_state["second_message"]

    participant.last_read_message = second_message

    participant.save(
        update_fields=[
            "last_read_message",
        ],
    )

    with patch.object(
        ReadService,
        "notify_messages_read",
    ) as notify:

        ReadService.mark_read_up_to(
            dialog_id=participant.dialog_id,
            user_id=participant.user_id,
            message_id=first_message.id,
        )

    participant.refresh_from_db()

    assert participant.last_read_message_id == second_message.id

    notify.assert_not_called()


@pytest.mark.django_db
def test_notify_messages_read_sends_expected_group_event(
    read_receipt_state,
):
    """ReadService формирует корректное событие прочтения."""

    dialog = read_receipt_state["dialog"]

    reader = read_receipt_state["reader"]

    message = read_receipt_state["second_message"]

    channel_layer = AsyncMock()

    with patch(
        "messenger.services.read.get_channel_layer",
        return_value=channel_layer,
    ):
        ReadService.notify_messages_read(
            dialog_id=dialog.id,
            reader_id=reader.id,
            last_read_message_id=message.id,
        )

    channel_layer.group_send.assert_has_awaits(
        [
            call(
                f"dialog_{dialog.id}",
                {
                    "type": "messages_read",
                    "reader_id": reader.id,
                    "last_read_message_id": message.id,
                },
            ),
            call(
                f"messenger_user_{reader.id}",
                {
                    "type": "inbox_changed",
                    "reason": "messages.read",
                },
            ),
        ]
    )

    assert channel_layer.group_send.await_count == 2


def test_dialog_consumer_converts_read_event_to_client_payload():
    """
    Consumer передает отправителю событие messages.read.
    """

    consumer = DialogConsumer()

    consumer.scope = {
        "user": SimpleNamespace(
            id=100,
        ),
    }

    consumer.send_json = AsyncMock()

    event = {
        "type": "messages_read",
        "reader_id": 200,
        "last_read_message_id": 500,
    }

    async_to_sync(
        consumer.messages_read,
    )(
        event,
    )

    consumer.send_json.assert_awaited_once_with(
        {
            "type": "messages.read",
            "reader_id": 200,
            "last_read_message_id": 500,
        },
    )


def test_dialog_consumer_does_not_send_read_event_back_to_reader():
    """
    Consumer не отправляет пользователю
    его собственное событие прочтения.
    """

    consumer = DialogConsumer()

    consumer.scope = {
        "user": SimpleNamespace(
            id=200,
        ),
    }

    consumer.send_json = AsyncMock()

    event = {
        "type": "messages_read",
        "reader_id": 200,
        "last_read_message_id": 500,
    }

    async_to_sync(
        consumer.messages_read,
    )(
        event,
    )

    consumer.send_json.assert_not_awaited()


@pytest.mark.django_db
def test_opening_dialog_marks_latest_message_as_read(
    read_receipt_state,
    rf,
):
    """Открытие диалога отмечает последнее сообщение прочитанным."""

    reader = read_receipt_state["reader"]

    dialog = read_receipt_state["dialog"]

    participant = read_receipt_state["reader_participant"]

    latest_message = read_receipt_state["second_message"]

    request = rf.get(
        reverse(
            "messenger:dialog_detail",
            kwargs={
                "public_id": dialog.public_id,
            },
        )
    )

    request.user = reader

    view = DialogDetailView()

    view.request = request

    view.kwargs = {
        "public_id": dialog.public_id,
    }

    with patch.object(
        ReadService,
        "notify_messages_read",
    ):
        loaded_dialog = view.get_object()

    participant.refresh_from_db()

    assert loaded_dialog.pk == dialog.pk

    assert participant.last_read_message_id == latest_message.id


@pytest.mark.django_db
def test_outgoing_message_is_double_checked_when_recipient_read_it(
    read_receipt_state,
):
    """✓✓ определяется read cursor получателя, а не отправителя."""

    sender = read_receipt_state["sender"]

    dialog = read_receipt_state["dialog"]

    message = read_receipt_state["second_message"]

    reader_participant = read_receipt_state["reader_participant"]

    reader_participant.last_read_message = message

    reader_participant.save(
        update_fields=[
            "last_read_message",
        ],
    )

    dialog._current_user = sender

    html = render_to_string(
        "messenger/outgoing.html",
        {
            "dialog": dialog,
            "message": message,
        },
    )

    assert "✓✓" in html


@pytest.mark.django_db
def test_outgoing_message_stays_single_checked_when_only_sender_read_it(
    read_receipt_state,
):
    """
    Read cursor отправителя не должен превращать
    его собственное сообщение в ✓✓.
    """

    sender = read_receipt_state["sender"]

    dialog = read_receipt_state["dialog"]

    message = read_receipt_state["second_message"]

    sender_participant = read_receipt_state["sender_participant"]

    reader_participant = read_receipt_state["reader_participant"]

    sender_participant.last_read_message = message

    sender_participant.save(
        update_fields=[
            "last_read_message",
        ],
    )

    reader_participant.last_read_message = None

    reader_participant.save(
        update_fields=[
            "last_read_message",
        ],
    )

    dialog._current_user = sender

    html = render_to_string(
        "messenger/outgoing.html",
        {
            "dialog": dialog,
            "message": message,
        },
    )

    assert "✓✓" not in html
    assert "✓" in html


@pytest.mark.django_db
def test_lazy_loaded_messages_render_recipient_read_status(
    read_receipt_state,
    client,
):
    """
    Lazy loading старых сообщений сохраняет
    правильный статус ✓✓.
    """

    sender = read_receipt_state["sender"]

    dialog = read_receipt_state["dialog"]

    reader_participant = read_receipt_state["reader_participant"]

    second_message = read_receipt_state["second_message"]

    reader_participant.last_read_message = second_message

    reader_participant.save(
        update_fields=[
            "last_read_message",
        ],
    )

    cursor_message = Message.objects.create(
        dialog=dialog,
        sender=sender,
        text="Cursor message",
    )

    client.force_login(
        sender,
    )

    response = client.get(
        reverse(
            "messenger:dialog_messages_older",
            kwargs={
                "public_id": dialog.public_id,
            },
        ),
        {
            "before": cursor_message.id,
        },
    )

    html = response.content.decode()

    assert response.status_code == 200
    assert "✓✓" in html
