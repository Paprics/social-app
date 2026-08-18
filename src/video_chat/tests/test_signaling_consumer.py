# src/video_chat/tests/test_signaling_consumer.py

"""Регрессионные тесты lifecycle случайного видеочата."""

import asyncio

import pytest
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import AnonymousUser

import video_chat.routing
from users.models.profile import Profile
from video_chat.consumers.signaling import SignalingConsumer
from video_chat.services.matchmaking import MatchmakingService
from video_chat.services.participant_storage import ParticipantStorage
from video_chat.services.room_storage import RoomStorage

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def signaling_backend(monkeypatch):
    """Подменить Redis-сервисы in-memory состоянием."""

    queue = []
    rooms = {}
    deleted_rooms = []
    participants = {}

    def leave_queue(self, channel_name):
        queue[:] = [channel for channel in queue if channel != channel_name]

    def join_queue(self, channel_name):
        leave_queue(
            self,
            channel_name,
        )

        if queue:
            partner = queue.pop(0)

            if partner == channel_name:
                queue.append(channel_name)
                return None

            return partner

        queue.append(channel_name)
        return None

    def save_participant(
        self,
        channel_name,
        metadata,
    ):
        participants[channel_name] = dict(metadata)

    def get_participant(
        self,
        channel_name,
    ):
        metadata = participants.get(channel_name)

        return dict(metadata) if metadata else None

    def delete_participant(
        self,
        channel_name,
    ):
        participants.pop(
            channel_name,
            None,
        )

    def create_room(
        self,
        room_id,
        caller_channel,
        callee_channel,
        *,
        caller_participant=None,
        callee_participant=None,
    ):
        rooms[room_id] = {
            "caller": caller_channel,
            "callee": callee_channel,
            "caller_participant": (caller_participant or {}),
            "callee_participant": (callee_participant or {}),
        }

    def delete_room(
        self,
        room_id,
    ):
        deleted_rooms.append(room_id)
        rooms.pop(
            room_id,
            None,
        )

    monkeypatch.setattr(
        MatchmakingService,
        "leave_queue",
        leave_queue,
    )
    monkeypatch.setattr(
        MatchmakingService,
        "join_queue",
        join_queue,
    )
    monkeypatch.setattr(
        ParticipantStorage,
        "save",
        save_participant,
    )
    monkeypatch.setattr(
        ParticipantStorage,
        "get",
        get_participant,
    )
    monkeypatch.setattr(
        ParticipantStorage,
        "delete",
        delete_participant,
    )
    monkeypatch.setattr(
        RoomStorage,
        "create_room",
        create_room,
    )
    monkeypatch.setattr(
        RoomStorage,
        "delete_room",
        delete_room,
    )

    return {
        "queue": queue,
        "rooms": rooms,
        "deleted_rooms": deleted_rooms,
        "participants": participants,
    }


def websocket_application(
    user=None,
):
    """Вернуть ASGI router с явным пользователем в scope."""

    router = URLRouter(video_chat.routing.websocket_urlpatterns)

    if user is None:
        user = AnonymousUser()

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


async def start_session(
    communicator,
    gender="male",
):
    await communicator.send_json_to(
        {
            "type": "start",
            "gender": gender,
        }
    )

    started = await communicator.receive_json_from(timeout=1)
    waiting = await communicator.receive_json_from(timeout=1)

    assert started["type"] == "started"
    assert started["chat_gender"] == gender
    assert waiting == {
        "type": "status",
        "message": "waiting",
    }

    return started


async def connect_pair():
    callee = WebsocketCommunicator(
        websocket_application(),
        "/ws/chat/",
    )
    caller = WebsocketCommunicator(
        websocket_application(),
        "/ws/chat/",
    )

    assert (await callee.connect())[0] is True
    assert await callee.receive_nothing(timeout=0.05)

    await start_session(
        callee,
        "female",
    )

    assert (await caller.connect())[0] is True
    assert await caller.receive_nothing(timeout=0.05)

    await start_session(
        caller,
        "male",
    )

    caller_match = await caller.receive_json_from(timeout=1)
    callee_match = await callee.receive_json_from(timeout=1)

    assert caller_match["type"] == "matched"
    assert caller_match["role"] == "caller"
    assert callee_match["type"] == "matched"
    assert callee_match["role"] == "callee"
    assert caller_match["room_id"] == callee_match["room_id"]

    return (
        caller,
        callee,
        caller_match,
        callee_match,
    )


def test_websocket_connect_does_not_start_matchmaking(
    signaling_backend,
):
    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        connected, _ = await communicator.connect()

        assert connected is True
        assert await communicator.receive_nothing(timeout=0.1)
        assert signaling_backend["queue"] == []

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_start_creates_anonymous_redis_metadata_and_enters_queue(
    signaling_backend,
):
    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (await communicator.connect())[0] is True

        started = await start_session(
            communicator,
            "female",
        )

        assert started["session_id"]
        assert len(signaling_backend["queue"]) == 1

        metadata = next(iter(signaling_backend["participants"].values()))

        assert metadata["user_id"] is None
        assert metadata["is_authenticated"] is False
        assert metadata["chat_gender"] == "female"

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_authenticated_metadata_keeps_profile_and_chat_gender_separate(
    signaling_backend,
    django_user_model,
):
    user = django_user_model.objects.create_user(
        username="video_member",
        password="test-password",
    )

    Profile.objects.update_or_create(
        user=user,
        defaults={
            "gender": Profile.Gender.MALE,
        },
    )

    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(user),
            "/ws/chat/",
        )

        assert (await communicator.connect())[0] is True

        await start_session(
            communicator,
            "couple",
        )

        metadata = next(iter(signaling_backend["participants"].values()))

        assert metadata["user_id"] == user.pk
        assert metadata["username"] == "video_member"
        assert metadata["profile_gender"] == "male"
        assert metadata["chat_gender"] == "couple"

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_invalid_gender_does_not_create_metadata(
    signaling_backend,
):
    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (await communicator.connect())[0] is True

        await communicator.send_json_to(
            {
                "type": "start",
                "gender": "not-a-gender",
            }
        )

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "error",
            "code": "invalid_gender",
        }

        assert signaling_backend["queue"] == []

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_two_started_users_are_matched_with_participant_metadata(
    signaling_backend,
):
    async def scenario():
        (
            caller,
            callee,
            caller_match,
            _,
        ) = await connect_pair()

        room = signaling_backend["rooms"][caller_match["room_id"]]

        assert room["caller_participant"]["chat_gender"] == "male"
        assert room["callee_participant"]["chat_gender"] == "female"

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()


def test_ready_and_webrtc_signaling_are_forwarded_to_partner(
    signaling_backend,
):
    async def scenario():
        (
            caller,
            callee,
            _,
            _,
        ) = await connect_pair()

        await callee.send_json_to(
            {
                "type": "ready",
            }
        )

        assert await caller.receive_json_from(timeout=1) == {
            "payload": {
                "type": "ready_to_connect",
            }
        }

        offer = {
            "type": "offer",
            "sdp": {
                "type": "offer",
                "sdp": "v=0 offer",
            },
        }

        await caller.send_json_to(offer)

        assert await callee.receive_json_from(timeout=1) == {
            "payload": offer,
        }

        answer = {
            "type": "answer",
            "sdp": {
                "type": "answer",
                "sdp": "v=0 answer",
            },
        }

        await callee.send_json_to(answer)

        assert await caller.receive_json_from(timeout=1) == {
            "payload": answer,
        }

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()


def test_chat_is_blocked_until_connected(
    signaling_backend,
):
    async def scenario():
        (
            caller,
            callee,
            _,
            _,
        ) = await connect_pair()

        await caller.send_json_to(
            {
                "type": "chat_message",
                "text": "too early",
            }
        )

        assert await callee.receive_nothing(timeout=0.1)

        await caller.send_json_to(
            {
                "type": "connected",
            }
        )

        await caller.send_json_to(
            {
                "type": "chat_message",
                "text": "hello",
            }
        )

        assert await callee.receive_json_from(timeout=1) == {
            "payload": {
                "type": "chat_message",
                "text": "hello",
                "sender": "partner",
            }
        }

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()


def test_next_enters_cooldown_and_search_is_server_enforced(
    signaling_backend,
    monkeypatch,
):
    async def scenario():
        (
            caller,
            callee,
            caller_match,
            _,
        ) = await connect_pair()

        room_id = caller_match["room_id"]

        await caller.send_json_to(
            {
                "type": "next",
            }
        )

        assert await caller.receive_json_from(timeout=1) == {
            "type": "cooldown",
            "seconds": 3,
        }

        assert await callee.receive_json_from(timeout=1) == {
            "type": "partner_disconnected",
            "seconds": 3,
        }

        assert signaling_backend["queue"] == []
        assert room_id not in signaling_backend["rooms"]

        await caller.send_json_to(
            {
                "type": "search",
            }
        )

        assert await caller.receive_json_from(timeout=1) == {
            "type": "cooldown",
            "seconds": 3,
        }

        # Не подменяем time.monotonic(): его использует asyncio для timeout.
        # Подменяем только расчёт cooldown у consumer.
        monkeypatch.setattr(
            SignalingConsumer,
            "_cooldown_remaining",
            lambda self: 0,
        )

        await caller.send_json_to(
            {
                "type": "search",
            }
        )

        assert await caller.receive_json_from(timeout=1) == {
            "type": "status",
            "message": "waiting",
        }

        assert len(signaling_backend["queue"]) == 1

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()


def test_stop_removes_waiting_user_and_redis_metadata(
    signaling_backend,
):
    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (await communicator.connect())[0] is True

        await start_session(
            communicator,
            "non_binary",
        )

        assert len(signaling_backend["queue"]) == 1

        await communicator.send_json_to(
            {
                "type": "stop",
            }
        )

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "stopped",
        }

        assert signaling_backend["queue"] == []
        assert signaling_backend["participants"] == {}

        await communicator.disconnect()

    async_to_sync(scenario)()


def test_moderator_reply_is_not_forwarded_to_partner(
    signaling_backend,
):
    async def scenario():
        layer = get_channel_layer()

        (
            caller,
            callee,
            caller_match,
            _,
        ) = await connect_pair()

        room_id = caller_match["room_id"]

        moderator_channel = await layer.new_channel("moderator-reply-test.")

        await layer.group_add(
            f"moderate_{room_id}",
            moderator_channel,
        )

        await caller.send_json_to(
            {
                "type": "answer",
                "sdp": {
                    "type": "answer",
                    "sdp": "moderator-answer",
                },
                "from_moderator_reply": True,
                "answering_channel": "spoofed-channel",
            }
        )

        moderator_event = await asyncio.wait_for(
            layer.receive(moderator_channel),
            timeout=1,
        )

        caller_channel = signaling_backend["rooms"][room_id]["caller"]

        assert moderator_event == {
            "type": "signaling.message",
            "payload": {
                "type": "answer",
                "sdp": {
                    "type": "answer",
                    "sdp": "moderator-answer",
                },
                "from_moderator_reply": True,
                "answering_channel": caller_channel,
            },
        }

        assert await callee.receive_nothing(timeout=0.1)

        await layer.group_discard(
            f"moderate_{room_id}",
            moderator_channel,
        )

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()
