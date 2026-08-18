# src/video_chat/tests/test_participant_storage.py

"""Тесты Redis metadata активных участников видеочата."""

from video_chat.services.participant_storage import (
    PARTICIPANTS_KEY,
    PARTICIPANT_TTL,
    ParticipantStorage,
)


def test_participant_storage_round_trip(
    fake_redis,
):
    storage = ParticipantStorage()

    metadata = {
        "session_pk": 10,
        "session_id": "session-1",
        "user_id": 42,
        "username": "alice",
        "is_authenticated": True,
        "profile_gender": "female",
        "chat_gender": "couple",
    }

    storage.save(
        "channel-1",
        metadata,
    )

    assert storage.get(
        "channel-1"
    ) == metadata

    assert (
        fake_redis.expirations[
            PARTICIPANTS_KEY
        ]
        == PARTICIPANT_TTL
    )

    storage.delete(
        "channel-1"
    )

    assert storage.get(
        "channel-1"
    ) is None
