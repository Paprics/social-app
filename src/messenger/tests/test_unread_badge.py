import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from messenger.context_processors import messenger_context
from messenger.models import Message, Participant
from messenger.selectors.participant import get_unread_messages_count
from messenger.services.dialog import DialogService
from notifications.context_processor import notifications_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def unread_state(django_user_model):
    user = django_user_model.objects.create_user(
        username="badge_user",
        password="test-password",
    )
    first_sender = django_user_model.objects.create_user(
        username="badge_sender_1",
        password="test-password",
    )
    second_sender = django_user_model.objects.create_user(
        username="badge_sender_2",
        password="test-password",
    )

    first_dialog = DialogService.create_dialog([user, first_sender])
    second_dialog = DialogService.create_dialog([user, second_sender])

    first_participant = Participant.objects.get(
        dialog=first_dialog,
        user=user,
    )

    return {
        "user": user,
        "first_sender": first_sender,
        "second_sender": second_sender,
        "first_dialog": first_dialog,
        "second_dialog": second_dialog,
        "first_participant": first_participant,
    }


def test_unread_count_sums_dialogs_and_ignores_own_messages(unread_state):
    user = unread_state["user"]

    Message.objects.create(
        dialog=unread_state["first_dialog"],
        sender=unread_state["first_sender"],
        text="first incoming",
    )
    Message.objects.create(
        dialog=unread_state["first_dialog"],
        sender=user,
        text="own message",
    )
    Message.objects.create(
        dialog=unread_state["second_dialog"],
        sender=unread_state["second_sender"],
        text="second incoming",
    )

    assert get_unread_messages_count(user) == 2


def test_unread_count_follows_last_read_cursor(unread_state):
    user = unread_state["user"]
    participant = unread_state["first_participant"]

    first = Message.objects.create(
        dialog=unread_state["first_dialog"],
        sender=unread_state["first_sender"],
        text="first",
    )
    second = Message.objects.create(
        dialog=unread_state["first_dialog"],
        sender=unread_state["first_sender"],
        text="second",
    )

    participant.last_read_message = first
    participant.save(update_fields=["last_read_message"])
    assert get_unread_messages_count(user) == 1

    participant.last_read_message = second
    participant.save(update_fields=["last_read_message"])
    assert get_unread_messages_count(user) == 0


def test_archived_dialog_is_not_in_global_unread_count(unread_state):
    user = unread_state["user"]
    participant = unread_state["first_participant"]

    Message.objects.create(
        dialog=unread_state["first_dialog"],
        sender=unread_state["first_sender"],
        text="archived incoming",
    )

    participant.is_archived = True
    participant.save(update_fields=["is_archived"])

    assert get_unread_messages_count(user) == 0


def test_messenger_context_exposes_unread_count(unread_state):
    user = unread_state["user"]

    Message.objects.create(
        dialog=unread_state["first_dialog"],
        sender=unread_state["first_sender"],
        text="context incoming",
    )

    request = RequestFactory().get("/")
    request.user = user

    assert messenger_context(request)["messenger_unread_count"] == 1


def test_messenger_context_returns_zero_for_anonymous_user():
    request = RequestFactory().get("/")
    request.user = AnonymousUser()

    assert messenger_context(request) == {
        "messenger_unread_count": 0,
    }


def test_unread_messages_do_not_activate_notification_bell(unread_state):
    user = unread_state["user"]

    Message.objects.create(
        dialog=unread_state["first_dialog"],
        sender=unread_state["first_sender"],
        text="not a bell notification",
    )

    request = RequestFactory().get("/")
    request.user = user

    notifications = notifications_context(request)["notifications"]

    assert "messages" not in notifications
    assert notifications["count"] == 0
    assert notifications["has_notifications"] is False
