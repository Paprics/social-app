# src/video_chat/tests/test_room_storage.py

import json

from video_chat.services.room_storage import (
    ROOM_TTL,
    ROOMS_KEY,
    RoomStorage,
)


def test_create_room_stores_metadata_and_ttl(
    fake_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.services.room_storage.time.time",
        lambda: 1234.5,
    )

    storage = RoomStorage()

    storage.create_room(
        "room-1",
        "caller-channel",
        "callee-channel",
    )

    raw = fake_redis.hget(
        ROOMS_KEY,
        "room-1",
    )

    assert json.loads(raw) == {
        "caller": "caller-channel",
        "callee": "callee-channel",
        "created_at": 1234.5,
    }

    assert fake_redis.expirations[ROOMS_KEY] == ROOM_TTL


def test_get_room_returns_metadata(fake_redis):
    storage = RoomStorage()

    fake_redis.hset(
        ROOMS_KEY,
        "room-1",
        json.dumps(
            {
                "caller": "caller-channel",
                "callee": "callee-channel",
                "created_at": 1000.0,
            }
        ),
    )

    assert storage.get_room("room-1") == {
        "caller": "caller-channel",
        "callee": "callee-channel",
        "created_at": 1000.0,
    }


def test_get_room_returns_none_when_missing(
    fake_redis,
):
    storage = RoomStorage()

    assert storage.get_room("missing") is None


def test_delete_room_removes_room(fake_redis):
    storage = RoomStorage()

    fake_redis.hset(
        ROOMS_KEY,
        "room-1",
        "{}",
    )

    storage.delete_room("room-1")

    assert storage.get_room("room-1") is None


def test_list_rooms_returns_newest_first(
    fake_redis,
):
    storage = RoomStorage()

    fake_redis.hset(
        ROOMS_KEY,
        "old-room",
        json.dumps(
            {
                "caller": "caller-old",
                "callee": "callee-old",
                "created_at": 1000.0,
            }
        ),
    )

    fake_redis.hset(
        ROOMS_KEY,
        "new-room",
        json.dumps(
            {
                "caller": "caller-new",
                "callee": "callee-new",
                "created_at": 2000.0,
            }
        ),
    )

    rooms = storage.list_rooms()

    assert [room["room_id"] for room in rooms] == [
        "new-room",
        "old-room",
    ]
