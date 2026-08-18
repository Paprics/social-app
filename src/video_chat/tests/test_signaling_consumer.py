# src/video_chat/tests/test_signaling_consumer.py

import pytest
from asgiref.sync import async_to_sync
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator

import video_chat.routing
from video_chat.services.matchmaking import MatchmakingService
from video_chat.services.room_storage import RoomStorage

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def signaling_backend(monkeypatch):
    queue = []
    rooms = {}
    deleted_rooms = []

    def leave_queue(self, channel_name):
        queue[:] = [channel for channel in queue if channel != channel_name]

    def join_queue(self, channel_name):
        leave_queue(self, channel_name)

        if queue:
            partner = queue.pop(0)

            if partner == channel_name:
                queue.append(channel_name)
                return None

            return partner

        queue.append(channel_name)
        return None

    def create_room(
        self,
        room_id,
        caller_channel,
        callee_channel,
    ):
        rooms[room_id] = {
            "caller": caller_channel,
            "callee": callee_channel,
        }

    def delete_room(self, room_id):
        deleted_rooms.append(room_id)
        rooms.pop(room_id, None)

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
    }


def websocket_application():
    return URLRouter(
        video_chat.routing.websocket_urlpatterns,
    )


def test_first_user_connects_and_waits_for_partner(
    signaling_backend,
):
    async def scenario():
        communicator = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        connected, _ = await communicator.connect()

        assert connected is True

        assert await communicator.receive_json_from(timeout=1) == {
            "type": "status",
            "message": "waiting",
        }

        await communicator.disconnect()

    async_to_sync(scenario)()

    assert signaling_backend["queue"] == []


def test_two_users_are_matched_as_caller_and_callee(
    signaling_backend,
):
    async def scenario():
        callee = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )
        caller = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (await callee.connect())[0] is True

        assert await callee.receive_json_from(timeout=1) == {
            "type": "status",
            "message": "waiting",
        }

        assert (await caller.connect())[0] is True

        assert await caller.receive_json_from(timeout=1) == {
            "type": "status",
            "message": "waiting",
        }

        caller_match = await caller.receive_json_from(timeout=1)
        callee_match = await callee.receive_json_from(timeout=1)

        assert caller_match["type"] == "matched"
        assert caller_match["role"] == "caller"

        assert callee_match["type"] == "matched"
        assert callee_match["role"] == "callee"

        assert caller_match["room_id"] == callee_match["room_id"]

        room_id = caller_match["room_id"]

        assert room_id in signaling_backend["rooms"]
        assert signaling_backend["queue"] == []

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()


def test_ready_and_webrtc_signaling_are_forwarded_to_partner(
    signaling_backend,
):
    async def scenario():
        callee = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )
        caller = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (await callee.connect())[0] is True
        await callee.receive_json_from(timeout=1)

        assert (await caller.connect())[0] is True
        await caller.receive_json_from(timeout=1)

        caller_match = await caller.receive_json_from(timeout=1)
        callee_match = await callee.receive_json_from(timeout=1)

        assert caller_match["room_id"] == callee_match["room_id"]

        await callee.send_json_to({"type": "ready"})

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

        ice_candidate = {
            "type": "ice_candidate",
            "candidate": {
                "candidate": ("candidate:1 1 UDP 1 " "127.0.0.1 9999 typ host"),
            },
        }

        await caller.send_json_to(ice_candidate)

        assert await callee.receive_json_from(timeout=1) == {
            "payload": ice_candidate,
        }

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()


def test_chat_message_is_forwarded_to_partner(
    signaling_backend,
):
    async def scenario():
        callee = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )
        caller = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (await callee.connect())[0] is True
        await callee.receive_json_from(timeout=1)

        assert (await caller.connect())[0] is True
        await caller.receive_json_from(timeout=1)

        await caller.receive_json_from(timeout=1)
        await callee.receive_json_from(timeout=1)

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


def test_next_disconnects_old_partner_and_keeps_socket_open(
    signaling_backend,
):
    async def scenario():
        callee = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )
        caller = WebsocketCommunicator(
            websocket_application(),
            "/ws/chat/",
        )

        assert (await callee.connect())[0] is True
        await callee.receive_json_from(timeout=1)

        assert (await caller.connect())[0] is True
        await caller.receive_json_from(timeout=1)

        caller_match = await caller.receive_json_from(timeout=1)
        callee_match = await callee.receive_json_from(timeout=1)

        room_id = caller_match["room_id"]

        assert room_id == callee_match["room_id"]

        await caller.send_json_to({"type": "next"})

        assert await callee.receive_json_from(timeout=1) == {
            "type": "partner_disconnected",
        }

        assert await caller.receive_json_from(timeout=1) == {
            "type": "status",
            "message": "waiting",
        }

        assert room_id not in signaling_backend["rooms"]

        assert room_id in signaling_backend["deleted_rooms"]

        # После "next" текущий WebSocket должен остаться открыт.
        assert await caller.receive_nothing(timeout=0.1) is True

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()
