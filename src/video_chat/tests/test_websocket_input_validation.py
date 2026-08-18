# src/video_chat/tests/test_websocket_input_validation.py

"""Регрессии валидации входящих WebSocket сообщений."""

from types import SimpleNamespace

import pytest
from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

import video_chat.routing
from video_chat.services.websocket_message import (
    MAX_WEBSOCKET_MESSAGE_BYTES,
    InvalidWebSocketMessage,
    decode_websocket_message,
)

pytestmark = pytest.mark.django_db(transaction=True)


def websocket_application(
    *,
    user=None,
):
    """Создать ASGI router с явным пользователем."""

    router = URLRouter(
        video_chat.routing.websocket_urlpatterns
    )

    if user is None:
        user = SimpleNamespace(
            is_authenticated=False,
            is_staff=False,
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


def test_decoder_accepts_object_and_rejects_non_object():
    """Decoder принимает только JSON-object."""

    assert decode_websocket_message(
        '{"type":"stop"}'
    ) == {
        "type": "stop",
    }

    with pytest.raises(
        InvalidWebSocketMessage
    ):
        decode_websocket_message(
            '["stop"]'
        )


def test_signaling_consumer_rejects_malformed_json():
    """Malformed JSON не завершает user consumer исключением."""

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (
            await communicator.connect()
        )[0] is True

        await communicator.send_to(
            text_data="{"
        )

        assert await communicator.receive_json_from(
            timeout=1
        ) == {
            "type": "error",
            "code": "invalid_payload",
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_signaling_consumer_rejects_unknown_type():
    """Неизвестная команда получает машинную ошибку."""

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (
            await communicator.connect()
        )[0] is True

        await communicator.send_json_to(
            {
                "type": "not-supported",
            }
        )

        assert await communicator.receive_json_from(
            timeout=1
        ) == {
            "type": "error",
            "code": "unsupported_type",
        }

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_signaling_consumer_closes_oversized_message():
    """Слишком большой frame получает ошибку и закрывает сокет."""

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (
            await communicator.connect()
        )[0] is True

        await communicator.send_to(
            text_data=(
                "x"
                * (
                    MAX_WEBSOCKET_MESSAGE_BYTES
                    + 1
                )
            )
        )

        assert await communicator.receive_json_from(
            timeout=1
        ) == {
            "type": "error",
            "code": "message_too_large",
        }

        assert await communicator.wait(
            timeout=1
        ) is None

    async_to_sync(scenario)()


def test_moderator_consumer_rejects_malformed_json(
    monkeypatch,
):
    """Malformed JSON в moderator socket не вызывает traceback."""

    monkeypatch.setattr(
        "video_chat.consumers.moderator.RoomStorage.get_room",
        lambda self, room_id: {
            "caller": "caller-channel",
            "callee": "callee-channel",
            "created_at": 1000.0,
        },
    )

    staff = SimpleNamespace(
        is_authenticated=True,
        is_staff=True,
    )

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(
                user=staff,
            ),
            "/ws/chat/moderate/room-1/",
        )

        assert (
            await communicator.connect()
        )[0] is True

        await communicator.receive_json_from(
            timeout=1
        )

        await communicator.send_to(
            text_data="{"
        )

        assert await communicator.receive_json_from(
            timeout=1
        ) == {
            "type": "error",
            "code": "invalid_payload",
        }

        await communicator.disconnect()

    async_to_sync(scenario)()
