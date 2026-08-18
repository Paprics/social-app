# src/video_chat/tests/test_chat_storage.py

from video_chat.services.chat_storage import (
    CHAT_KEY_PREFIX,
    CHAT_TTL,
    ChatStorage,
)


def test_save_and_get_messages(
    fake_redis,
    monkeypatch,
):
    monkeypatch.setattr(
        "video_chat.services.chat_storage.time.time",
        lambda: 1234.5,
    )

    storage = ChatStorage()

    message = storage.save_message(
        "room-1",
        "caller",
        "hello",
    )

    assert message == {
        "sender": "caller",
        "text": "hello",
        "timestamp": 1234.5,
    }

    assert storage.get_messages("room-1") == [
        {
            "sender": "caller",
            "text": "hello",
            "timestamp": 1234.5,
        }
    ]

    key = f"{CHAT_KEY_PREFIX}room-1"

    assert fake_redis.expirations[key] == CHAT_TTL


def test_delete_chat_removes_messages(
    fake_redis,
):
    storage = ChatStorage()

    storage.save_message(
        "room-1",
        "caller",
        "hello",
    )

    storage.delete_chat("room-1")

    assert storage.get_messages("room-1") == []
