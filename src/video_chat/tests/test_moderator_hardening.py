# src/video_chat/tests/test_moderator_hardening.py

"""Регрессии stale-room безопасности moderator WebSocket."""

import asyncio
from types import SimpleNamespace

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

import video_chat.routing

pytestmark = pytest.mark.django_db(transaction=True)


def websocket_application():
    """Создать ASGI router со staff-пользователем."""

    router = URLRouter(video_chat.routing.websocket_urlpatterns)
    user = SimpleNamespace(
        is_authenticated=True,
        is_staff=True,
    )

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


def test_moderator_revalidates_room_before_kick(
    monkeypatch,
):
    """Stale moderator не может кикнуть channel после удаления room."""

    async def scenario():
        layer = get_channel_layer()
        caller = await layer.new_channel("stale-kick-caller.")
        callee = await layer.new_channel("stale-kick-callee.")
        calls = 0

        def get_room(self, room_id):
            nonlocal calls
            calls += 1

            if calls == 1:
                return {
                    "caller": caller,
                    "callee": callee,
                    "created_at": 1000.0,
                }

            return None

        monkeypatch.setattr(
            "video_chat.consumers.moderator.RoomStorage.get_room",
            get_room,
        )

        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True
        await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "type": "kick",
                "target": caller,
            }
        )

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "room_closed",
        }

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                layer.receive(caller),
                timeout=0.1,
            )

        assert await communicator.wait(timeout=1) is None

    async_to_sync(scenario)()


def test_moderator_revalidates_room_before_signaling(
    monkeypatch,
):
    """Stale moderator не может signaling в завершённую room."""

    async def scenario():
        layer = get_channel_layer()
        caller = await layer.new_channel("stale-signal-caller.")
        callee = await layer.new_channel("stale-signal-callee.")
        calls = 0

        def get_room(self, room_id):
            nonlocal calls
            calls += 1

            if calls == 1:
                return {
                    "caller": caller,
                    "callee": callee,
                    "created_at": 1000.0,
                }

            return None

        monkeypatch.setattr(
            "video_chat.consumers.moderator.RoomStorage.get_room",
            get_room,
        )

        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True
        await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "type": "offer",
                "target": caller,
                "sdp": {
                    "type": "offer",
                    "sdp": "stale-offer",
                },
            }
        )

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "room_closed",
        }

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                layer.receive(caller),
                timeout=0.1,
            )

        assert await communicator.wait(timeout=1) is None

    async_to_sync(scenario)()


def test_moderator_socket_closes_on_room_closed_event(
    monkeypatch,
):
    """room.closed group event закрывает moderator WebSocket."""

    monkeypatch.setattr(
        "video_chat.consumers.moderator.RoomStorage.get_room",
        lambda self, room_id: {
            "caller": "caller-channel",
            "callee": "callee-channel",
            "created_at": 1000.0,
        },
    )

    async def scenario():
        layer = get_channel_layer()

        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True
        await communicator.receive_json_from(timeout=1)

        await layer.group_send(
            "moderate_room-1",
            {
                "type": "room.closed",
            },
        )

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "room_closed",
        }

        assert await communicator.wait(timeout=1) is None

    async_to_sync(scenario)()
