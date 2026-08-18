# src/video_chat/tests/test_room_storage.py

"""Тесты Redis-хранилища активных комнат."""

import json

from video_chat.services.room_storage import (
    ROOM_INDEX_KEY,
    ROOM_KEY_PREFIX,
    ROOM_TTL,
    RoomStorage,
)


def test_create_room_stores_participant_metadata_and_ttl(
    fake_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.services.room_storage.time.time",
        lambda: 1234.5,
    )

    storage = RoomStorage()

    caller = {
        "user_id": 1,
        "chat_gender": "male",
    }
    callee = {
        "user_id": None,
        "chat_gender": "female",
    }

    storage.create_room(
        "room-1",
        "caller-channel",
        "callee-channel",
        caller_participant=caller,
        callee_participant=callee,
    )

    room_key = (
        f"{ROOM_KEY_PREFIX}"
        "room-1"
    )
    raw = fake_redis.get(
        room_key
    )

    assert json.loads(raw) == {
        "caller": "caller-channel",
        "callee": "callee-channel",
        "caller_participant": caller,
        "callee_participant": callee,
        "created_at": 1234.5,
    }

    assert (
        fake_redis.expirations[
            room_key
        ]
        == ROOM_TTL
    )

    assert fake_redis.zrevrange(
        ROOM_INDEX_KEY,
        0,
        -1,
    ) == [
        b"room-1",
    ]


def test_get_room_returns_metadata(
    fake_redis,
):
    storage = RoomStorage()

    fake_redis.set(
        f"{ROOM_KEY_PREFIX}room-1",
        json.dumps(
            {
                "caller": "caller-channel",
                "callee": "callee-channel",
                "caller_participant": {},
                "callee_participant": {},
                "created_at": 1000.0,
            }
        ),
        ex=ROOM_TTL,
    )

    assert storage.get_room(
        "room-1"
    ) == {
        "caller": "caller-channel",
        "callee": "callee-channel",
        "caller_participant": {},
        "callee_participant": {},
        "created_at": 1000.0,
    }


def test_get_room_returns_none_when_missing(
    fake_redis,
):
    storage = RoomStorage()

    assert storage.get_room(
        "missing"
    ) is None


def test_delete_room_removes_room_and_index_entry(
    fake_redis,
):
    storage = RoomStorage()

    storage.create_room(
        "room-1",
        "caller-channel",
        "callee-channel",
    )

    storage.delete_room(
        "room-1"
    )

    assert storage.get_room(
        "room-1"
    ) is None

    assert fake_redis.zrevrange(
        ROOM_INDEX_KEY,
        0,
        -1,
    ) == []


def test_list_rooms_returns_newest_first(
    fake_redis,
    monkeypatch,
):
    timestamps = iter(
        [
            1000.0,
            2000.0,
        ]
    )
    monkeypatch.setattr(
        "video_chat.services.room_storage.time.time",
        lambda: next(timestamps),
    )

    storage = RoomStorage()

    storage.create_room(
        "old-room",
        "caller-old",
        "callee-old",
    )
    storage.create_room(
        "new-room",
        "caller-new",
        "callee-new",
    )

    rooms = storage.list_rooms()

    assert [
        room["room_id"]
        for room in rooms
    ] == [
        "new-room",
        "old-room",
    ]


def test_list_rooms_removes_stale_index_entries(
    fake_redis,
):
    storage = RoomStorage()

    fake_redis.zadd(
        ROOM_INDEX_KEY,
        {
            "stale-room": 1000.0,
        },
    )

    assert storage.list_rooms() == []

    assert fake_redis.zrevrange(
        ROOM_INDEX_KEY,
        0,
        -1,
    ) == []
