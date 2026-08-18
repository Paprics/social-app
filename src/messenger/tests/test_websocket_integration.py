from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser
import pytest

import messenger.routing
from messenger.models import Dialog, Message, Participant
from messenger.services.dialog import DialogService


pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def websocket_state(django_user_model):
    sender = django_user_model.objects.create_user(
        username="ws_sender",
        password="test-password",
    )
    reader = django_user_model.objects.create_user(
        username="ws_reader",
        password="test-password",
    )
    outsider = django_user_model.objects.create_user(
        username="ws_outsider",
        password="test-password",
    )

    dialog = DialogService.create_dialog(
        [
            sender,
            reader,
        ]
    )

    reader_participant = Participant.objects.get(
        dialog=dialog,
        user=reader,
    )

    message = Message.objects.create(
        dialog=dialog,
        sender=sender,
        text="websocket message",
    )

    return {
        "sender": sender,
        "reader": reader,
        "outsider": outsider,
        "dialog": dialog,
        "reader_participant": reader_participant,
        "message": message,
    }


def websocket_application(user):
    router = URLRouter(
        messenger.routing.websocket_urlpatterns,
    )

    async def application(scope, receive, send):
        scope = dict(scope)
        scope["user"] = user

        await router(
            scope,
            receive,
            send,
        )

    return application


def test_anonymous_user_cannot_connect_to_dialog(websocket_state):
    dialog = websocket_state["dialog"]

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(AnonymousUser()),
            f"/ws/messenger/{dialog.public_id}/",
        )

        connected, _ = await communicator.connect()

        assert connected is False

    async_to_sync(scenario)()


def test_outsider_cannot_connect_to_dialog(websocket_state):
    outsider = websocket_state["outsider"]
    dialog = websocket_state["dialog"]

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(outsider),
            f"/ws/messenger/{dialog.public_id}/",
        )

        connected, _ = await communicator.connect()

        assert connected is False

    async_to_sync(scenario)()


def test_participant_can_connect_to_dialog(websocket_state):
    reader = websocket_state["reader"]
    dialog = websocket_state["dialog"]

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(reader),
            f"/ws/messenger/{dialog.public_id}/",
        )

        connected, _ = await communicator.connect()

        assert connected is True

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_message_created_reaches_both_participants_without_implicit_read(
    websocket_state,
):
    sender = websocket_state["sender"]
    reader = websocket_state["reader"]
    dialog = websocket_state["dialog"]
    message = websocket_state["message"]
    reader_participant = websocket_state["reader_participant"]

    async def scenario():
        sender_socket = WebsocketCommunicator(
            websocket_application(sender),
            f"/ws/messenger/{dialog.public_id}/",
        )
        reader_socket = WebsocketCommunicator(
            websocket_application(reader),
            f"/ws/messenger/{dialog.public_id}/",
        )

        assert (await sender_socket.connect())[0] is True
        assert (await reader_socket.connect())[0] is True

        channel_layer = get_channel_layer()

        await channel_layer.group_send(
            f"dialog_{dialog.id}",
            {
                "type": "chat_message",
                "message_id": message.id,
                "sender_id": sender.id,
            },
        )

        sender_event = await sender_socket.receive_json_from(timeout=1)
        reader_event = await reader_socket.receive_json_from(timeout=1)

        assert sender_event == {
            "type": "message.created",
            "message_id": message.id,
            "sender_id": sender.id,
            "is_own": True,
        }
        assert reader_event == {
            "type": "message.created",
            "message_id": message.id,
            "sender_id": sender.id,
            "is_own": False,
        }

        await sender_socket.disconnect()
        await reader_socket.disconnect()

    async_to_sync(scenario)()

    reader_participant.refresh_from_db()

    assert reader_participant.last_read_message_id is None


def test_explicit_message_read_updates_cursor_and_notifies_other_side(
    websocket_state,
):
    sender = websocket_state["sender"]
    reader = websocket_state["reader"]
    dialog = websocket_state["dialog"]
    message = websocket_state["message"]
    reader_participant = websocket_state["reader_participant"]

    async def scenario():
        sender_socket = WebsocketCommunicator(
            websocket_application(sender),
            f"/ws/messenger/{dialog.public_id}/",
        )
        reader_socket = WebsocketCommunicator(
            websocket_application(reader),
            f"/ws/messenger/{dialog.public_id}/",
        )

        assert (await sender_socket.connect())[0] is True
        assert (await reader_socket.connect())[0] is True

        await reader_socket.send_json_to(
            {
                "type": "message.read",
                "message_id": message.id,
            }
        )

        sender_event = await sender_socket.receive_json_from(timeout=2)

        assert sender_event == {
            "type": "messages.read",
            "reader_id": reader.id,
            "last_read_message_id": message.id,
        }

        assert await reader_socket.receive_nothing(timeout=0.2) is True

        await sender_socket.disconnect()
        await reader_socket.disconnect()

    async_to_sync(scenario)()

    reader_participant.refresh_from_db()

    assert reader_participant.last_read_message_id == message.id


def test_message_deleted_event_reaches_open_dialog(websocket_state):
    reader = websocket_state["reader"]
    dialog = websocket_state["dialog"]
    message = websocket_state["message"]

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(reader),
            f"/ws/messenger/{dialog.public_id}/",
        )

        assert (await communicator.connect())[0] is True

        await get_channel_layer().group_send(
            f"dialog_{dialog.id}",
            {
                "type": "message_deleted",
                "message_id": message.id,
            },
        )

        event = await communicator.receive_json_from(timeout=1)

        assert event == {
            "type": "message.deleted",
            "message_id": message.id,
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_dialog_deleted_event_reaches_open_dialog(websocket_state):
    reader = websocket_state["reader"]
    dialog = websocket_state["dialog"]

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(reader),
            f"/ws/messenger/{dialog.public_id}/",
        )

        assert (await communicator.connect())[0] is True

        await get_channel_layer().group_send(
            f"dialog_{dialog.id}",
            {
                "type": "dialog_deleted",
            },
        )

        event = await communicator.receive_json_from(timeout=1)

        assert event == {
            "type": "dialog.deleted",
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_inbox_consumer_forwards_invalidation(websocket_state):
    reader = websocket_state["reader"]

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(reader),
            "/ws/messenger/inbox/",
        )

        assert (await communicator.connect())[0] is True

        await get_channel_layer().group_send(
            f"messenger_user_{reader.id}",
            {
                "type": "inbox_changed",
                "reason": "message.created",
            },
        )

        event = await communicator.receive_json_from(timeout=1)

        assert event == {
            "type": "inbox.changed",
            "reason": "message.created",
        }

        await communicator.disconnect()

    async_to_sync(scenario)()
