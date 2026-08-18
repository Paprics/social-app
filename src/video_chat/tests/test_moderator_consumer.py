# src/video_chat/tests/test_moderator_consumer.py

from types import SimpleNamespace

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

import video_chat.routing

pytestmark = pytest.mark.django_db(transaction=True)


ROOM_META = {
    "caller": "caller-channel",
    "callee": "callee-channel",
    "created_at": 1000.0,
}


def websocket_application(user):
    router = URLRouter(video_chat.routing.websocket_urlpatterns)

    async def application(
        scope,
        receive,
        send,
    ):
        scope = dict(scope)
        scope["user"] = user

        await router(
            scope,
            receive,
            send,
        )

    return application


def anonymous_user():
    return SimpleNamespace(
        is_authenticated=False,
        is_staff=False,
    )


def regular_user():
    return SimpleNamespace(
        is_authenticated=True,
        is_staff=False,
    )


def staff_user():
    return SimpleNamespace(
        is_authenticated=True,
        is_staff=True,
    )


@pytest.mark.parametrize(
    "user",
    [
        anonymous_user(),
        regular_user(),
    ],
)
def test_moderator_websocket_rejects_non_staff(
    user,
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.consumers.moderator.RoomStorage.get_room",
        lambda self, room_id: ROOM_META,
    )

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(user),
            "/ws/chat/moderate/room-1/",
        )

        connected, close_code = await communicator.connect()

        if connected:
            await communicator.disconnect()

        assert connected is False
        assert close_code == 4403

    async_to_sync(scenario)()


def test_moderator_websocket_rejects_missing_room(
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.consumers.moderator.RoomStorage.get_room",
        lambda self, room_id: None,
    )

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/missing-room/",
        )

        connected, close_code = await communicator.connect()

        assert connected is False
        assert close_code == 4404

    async_to_sync(scenario)()


def test_staff_moderator_receives_room_info(
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.consumers.moderator.RoomStorage.get_room",
        lambda self, room_id: ROOM_META,
    )

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/room-1/",
        )

        connected, _ = await communicator.connect()

        assert connected is True

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "room_info",
            "room_id": "room-1",
            "caller": "caller-channel",
            "callee": "callee-channel",
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_moderator_signaling_is_sent_to_target(
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.consumers.moderator.RoomStorage.get_room",
        lambda self, room_id: ROOM_META,
    )

    async def scenario():
        layer = get_channel_layer()

        target = await layer.new_channel("moderator-test.")

        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True

        await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "type": "offer",
                "target": target,
                "sdp": {
                    "type": "offer",
                    "sdp": "test-offer",
                },
            }
        )

        event = await layer.receive(target)

        assert event == {
            "type": "signaling.message",
            "payload": {
                "type": "offer",
                "target": target,
                "sdp": {
                    "type": "offer",
                    "sdp": "test-offer",
                },
                "from_moderator": True,
            },
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_moderator_receives_participant_signaling(
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.consumers.moderator.RoomStorage.get_room",
        lambda self, room_id: ROOM_META,
    )

    async def scenario():
        layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True

        await communicator.receive_json_from(timeout=1)

        await layer.group_send(
            "moderate_room-1",
            {
                "type": "signaling.message",
                "payload": {
                    "type": "answer",
                    "sdp": "test-answer",
                },
            },
        )

        assert await communicator.receive_json_from(timeout=1) == {
            "payload": {
                "type": "answer",
                "sdp": "test-answer",
            }
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_moderator_kick_is_sent_to_target(
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.consumers.moderator.RoomStorage.get_room",
        lambda self, room_id: ROOM_META,
    )

    async def scenario():
        layer = get_channel_layer()

        target = await layer.new_channel("moderator-kick-test.")

        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True

        await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "type": "kick",
                "target": target,
            }
        )

        event = await layer.receive(target)

        assert event == {
            "type": "moderator.kick",
        }

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "kick_sent",
            "target": target,
        }

        await communicator.disconnect()

    async_to_sync(scenario)()
