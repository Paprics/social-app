# src/video_chat/tests/test_matchmaking.py

from video_chat.services.matchmaking import (
    QUEUE_KEY,
    MatchmakingService,
)


def test_first_user_is_added_to_queue(fake_redis):
    service = MatchmakingService()

    partner = service.join_queue("channel-a")

    assert partner is None
    assert fake_redis.lists[QUEUE_KEY] == [b"channel-a"]


def test_second_user_gets_first_user_as_partner(
    fake_redis,
):
    service = MatchmakingService()

    assert service.join_queue("channel-a") is None

    partner = service.join_queue("channel-b")

    assert partner == "channel-a"
    assert fake_redis.lists[QUEUE_KEY] == []


def test_join_queue_removes_duplicate_channel_entries(
    fake_redis,
):
    service = MatchmakingService()

    fake_redis.rpush(QUEUE_KEY, "channel-a")
    fake_redis.rpush(QUEUE_KEY, "channel-a")
    fake_redis.rpush(QUEUE_KEY, "channel-b")

    partner = service.join_queue("channel-a")

    assert partner == "channel-b"
    assert fake_redis.lists[QUEUE_KEY] == []


def test_leave_queue_removes_all_channel_entries(
    fake_redis,
):
    service = MatchmakingService()

    fake_redis.rpush(QUEUE_KEY, "channel-a")
    fake_redis.rpush(QUEUE_KEY, "channel-b")
    fake_redis.rpush(QUEUE_KEY, "channel-a")

    service.leave_queue("channel-a")

    assert fake_redis.lists[QUEUE_KEY] == [b"channel-b"]
