# src/messenger/tests/test_read_consistency.py

from unittest.mock import AsyncMock

import pytest
from asgiref.sync import async_to_sync
from django.urls import reverse

from messenger.consumers.dialog_consumer import DialogConsumer
from messenger.consumers.inbox_consumer import InboxConsumer
from messenger.models import Dialog, Message, Participant
from messenger.selectors.dialog import get_user_dialogs
from messenger.services.read import ReadService


@pytest.fixture
def read_state(django_user_model):
    sender = django_user_model.objects.create_user(
        username="consistency_sender",
        password="test-password",
    )
    reader = django_user_model.objects.create_user(
        username="consistency_reader",
        password="test-password",
    )

    dialog = Dialog.objects.create()
    Participant.objects.create(
        dialog=dialog,
        user=sender,
    )
    reader_participant = Participant.objects.create(
        dialog=dialog,
        user=reader,
    )

    first = Message.objects.create(
        dialog=dialog,
        sender=sender,
        text="first",
    )
    second = Message.objects.create(
        dialog=dialog,
        sender=sender,
        text="second",
    )

    return {
        "sender": sender,
        "reader": reader,
        "dialog": dialog,
        "participant": reader_participant,
        "first": first,
        "second": second,
    }


@pytest.mark.django_db
def test_mark_as_read_does_not_trust_stale_participant_instance(
    read_state,
):
    participant = read_state["participant"]
    first = read_state["first"]
    second = read_state["second"]

    stale_participant = Participant.objects.get(
        pk=participant.pk,
    )

    Participant.objects.filter(
        pk=participant.pk,
    ).update(
        last_read_message=second,
    )

    ReadService.mark_as_read(
        stale_participant,
        first,
    )

    participant.refresh_from_db()

    assert participant.last_read_message_id == second.id


@pytest.mark.django_db
def test_message_item_get_does_not_change_read_cursor(
    read_state,
    client,
):
    reader = read_state["reader"]
    participant = read_state["participant"]
    message = read_state["second"]

    client.force_login(reader)

    response = client.get(
        reverse(
            "messenger:message_item",
            kwargs={
                "message_id": message.id,
            },
        )
    )

    participant.refresh_from_db()

    assert response.status_code == 200
    assert participant.last_read_message_id is None


@pytest.mark.django_db
def test_message_item_renders_recipient_read_state_for_sender(
    read_state,
    client,
):
    sender = read_state["sender"]
    participant = read_state["participant"]
    message = read_state["second"]

    Participant.objects.filter(
        pk=participant.pk,
    ).update(
        last_read_message=message,
    )

    client.force_login(sender)

    response = client.get(
        reverse(
            "messenger:message_item",
            kwargs={
                "message_id": message.id,
            },
        )
    )

    assert response.status_code == 200
    assert "✓✓" in response.content.decode()


@pytest.mark.django_db
def test_mark_read_up_to_rejects_message_from_another_dialog(
    read_state,
):
    sender = read_state["sender"]
    reader = read_state["reader"]
    dialog = read_state["dialog"]
    participant = read_state["participant"]

    foreign_dialog = Dialog.objects.create()
    Participant.objects.create(
        dialog=foreign_dialog,
        user=sender,
    )
    Participant.objects.create(
        dialog=foreign_dialog,
        user=reader,
    )
    foreign_message = Message.objects.create(
        dialog=foreign_dialog,
        sender=sender,
        text="foreign",
    )

    changed = ReadService.mark_read_up_to(
        dialog_id=dialog.id,
        user_id=reader.id,
        message_id=foreign_message.id,
    )

    participant.refresh_from_db()

    assert changed is False
    assert participant.last_read_message_id is None


@pytest.mark.django_db
def test_consumer_delegates_read_change_to_read_service(
    read_state,
    monkeypatch,
):
    dialog = read_state["dialog"]
    reader = read_state["reader"]
    message = read_state["second"]

    calls = []

    def fake_mark_read_up_to(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(
        ReadService,
        "mark_read_up_to",
        fake_mark_read_up_to,
    )

    consumer = DialogConsumer()
    consumer.dialog_id = dialog.id

    async_to_sync(
        consumer.mark_message_as_read,
    )(
        message_id=message.id,
        user_id=reader.id,
    )

    assert calls == [
        {
            "dialog_id": dialog.id,
            "user_id": reader.id,
            "message_id": message.id,
        }
    ]


def test_consumer_still_suppresses_read_echo():
    consumer = DialogConsumer()
    consumer.scope = {
        "user": type(
            "User",
            (),
            {
                "id": 42,
            },
        )(),
    }
    consumer.send_json = AsyncMock()

    async_to_sync(
        consumer.messages_read,
    )(
        {
            "reader_id": 42,
            "last_read_message_id": 100,
        }
    )

    consumer.send_json.assert_not_awaited()

def test_message_created_does_not_mark_read_implicitly():
    consumer = DialogConsumer()
    consumer.scope = {
        "user": type(
            "User",
            (),
            {
                "id": 2,
            },
        )(),
    }
    consumer.mark_message_as_read = AsyncMock()
    consumer.send_json = AsyncMock()

    async_to_sync(
        consumer.chat_message,
    )(
        {
            "message_id": 100,
            "sender_id": 1,
        }
    )

    consumer.mark_message_as_read.assert_not_awaited()
    consumer.send_json.assert_awaited_once()


def test_explicit_message_read_event_marks_message():
    consumer = DialogConsumer()
    consumer.scope = {
        "user": type(
            "User",
            (),
            {
                "id": 42,
            },
        )(),
    }
    consumer.mark_message_as_read = AsyncMock(
        return_value=True,
    )

    async_to_sync(
        consumer.receive_json,
    )(
        {
            "type": "message.read",
            "message_id": 123,
        }
    )

    consumer.mark_message_as_read.assert_awaited_once_with(
        message_id=123,
        user_id=42,
    )


def test_inbox_consumer_forwards_invalidation_event():
    consumer = InboxConsumer()
    consumer.send_json = AsyncMock()

    async_to_sync(
        consumer.inbox_changed,
    )(
        {
            "type": "inbox_changed",
            "reason": "message.created",
        }
    )

    consumer.send_json.assert_awaited_once_with(
        {
            "type": "inbox.changed",
            "reason": "message.created",
        }
    )


@pytest.mark.django_db
def test_unread_count_follows_read_cursor(
    read_state,
):
    reader = read_state["reader"]
    dialog = read_state["dialog"]
    first = read_state["first"]
    second = read_state["second"]

    loaded_dialog = get_user_dialogs(
        reader,
    ).get(
        pk=dialog.pk,
    )

    assert loaded_dialog.unread_count == 2

    ReadService.mark_read_up_to(
        dialog_id=dialog.id,
        user_id=reader.id,
        message_id=first.id,
    )

    loaded_dialog = get_user_dialogs(
        reader,
    ).get(
        pk=dialog.pk,
    )

    assert loaded_dialog.unread_count == 1

    ReadService.mark_read_up_to(
        dialog_id=dialog.id,
        user_id=reader.id,
        message_id=second.id,
    )

    loaded_dialog = get_user_dialogs(
        reader,
    ).get(
        pk=dialog.pk,
    )

    assert loaded_dialog.unread_count == 0

