# src/video_chat/tests/test_moderator_consumer.py

"""Регрессионные тесты WebSocket consumer модератора видеочата."""

import asyncio
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
    """Создать ASGI-приложение с заданным пользователем в scope."""

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
    """Вернуть неавторизованного пользователя."""

    return SimpleNamespace(
        is_authenticated=False,
        is_staff=False,
    )


def regular_user():
    """Вернуть обычного авторизованного пользователя."""

    return SimpleNamespace(
        is_authenticated=True,
        is_staff=False,
    )


def staff_user():
    """Вернуть staff-пользователя."""

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
    """Модераторский WebSocket недоступен пользователям без staff-прав."""

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
    """Staff-пользователь не может подключиться к отсутствующей комнате."""

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
    """Staff-модератор получает метаданные существующей комнаты."""

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


def test_moderator_signaling_is_sent_to_room_participant(
    monkeypatch,
):
    """WebRTC signaling модератора передаётся участнику текущей комнаты."""

    async def scenario():
        layer = get_channel_layer()

        caller_channel = await layer.new_channel("moderator-caller.")
        callee_channel = await layer.new_channel("moderator-callee.")

        room_meta = {
            "caller": caller_channel,
            "callee": callee_channel,
            "created_at": 1000.0,
        }

        monkeypatch.setattr(
            "video_chat.consumers.moderator.RoomStorage.get_room",
            lambda self, room_id: room_meta,
        )

        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True

        await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "type": "offer",
                "target": caller_channel,
                "sdp": {
                    "type": "offer",
                    "sdp": "test-offer",
                },
            }
        )

        event = await asyncio.wait_for(
            layer.receive(caller_channel),
            timeout=1,
        )

        assert event == {
            "type": "signaling.message",
            "payload": {
                "type": "offer",
                "target": caller_channel,
                "sdp": {
                    "type": "offer",
                    "sdp": "test-offer",
                },
                "from_moderator": True,
            },
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_moderator_cannot_signal_foreign_channel(
    monkeypatch,
):
    """Модератор не может отправить signaling пользователю другой комнаты."""

    async def scenario():
        layer = get_channel_layer()

        caller_channel = await layer.new_channel("moderator-caller.")
        callee_channel = await layer.new_channel("moderator-callee.")
        foreign_channel = await layer.new_channel("moderator-foreign.")

        room_meta = {
            "caller": caller_channel,
            "callee": callee_channel,
            "created_at": 1000.0,
        }

        monkeypatch.setattr(
            "video_chat.consumers.moderator.RoomStorage.get_room",
            lambda self, room_id: room_meta,
        )

        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True

        await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "type": "offer",
                "target": foreign_channel,
                "sdp": {
                    "type": "offer",
                    "sdp": "foreign-offer",
                },
            }
        )

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                layer.receive(foreign_channel),
                timeout=0.1,
            )

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_moderator_receives_participant_signaling(
    monkeypatch,
):
    """Модератор получает signaling участника через группу комнаты."""

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


def test_moderator_kick_is_sent_to_room_participant(
    monkeypatch,
):
    """Команда kick передаётся участнику текущей комнаты."""

    async def scenario():
        layer = get_channel_layer()

        caller_channel = await layer.new_channel("moderator-kick-caller.")
        callee_channel = await layer.new_channel("moderator-kick-callee.")

        room_meta = {
            "caller": caller_channel,
            "callee": callee_channel,
            "created_at": 1000.0,
        }

        monkeypatch.setattr(
            "video_chat.consumers.moderator.RoomStorage.get_room",
            lambda self, room_id: room_meta,
        )

        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True

        await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "type": "kick",
                "target": callee_channel,
            }
        )

        event = await asyncio.wait_for(
            layer.receive(callee_channel),
            timeout=1,
        )

        assert event == {
            "type": "moderator.kick",
        }

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "kick_sent",
            "target": callee_channel,
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_moderator_cannot_kick_foreign_channel(
    monkeypatch,
):
    """Модератор не может кикнуть пользователя другой комнаты."""

    async def scenario():
        layer = get_channel_layer()

        caller_channel = await layer.new_channel("moderator-kick-caller.")
        callee_channel = await layer.new_channel("moderator-kick-callee.")
        foreign_channel = await layer.new_channel("moderator-kick-foreign.")

        room_meta = {
            "caller": caller_channel,
            "callee": callee_channel,
            "created_at": 1000.0,
        }

        monkeypatch.setattr(
            "video_chat.consumers.moderator.RoomStorage.get_room",
            lambda self, room_id: room_meta,
        )

        communicator = WebsocketCommunicator(
            websocket_application(staff_user()),
            "/ws/chat/moderate/room-1/",
        )

        assert (await communicator.connect())[0] is True

        await communicator.receive_json_from(timeout=1)

        await communicator.send_json_to(
            {
                "type": "kick",
                "target": foreign_channel,
            }
        )

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                layer.receive(foreign_channel),
                timeout=0.1,
            )

        # Для отклонённого target модератор не должен получить kick_sent.
        assert await communicator.receive_nothing(timeout=0.1)

        await communicator.disconnect()

    async_to_sync(scenario)()
