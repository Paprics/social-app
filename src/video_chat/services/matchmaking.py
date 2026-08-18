# src/video_chat/services/matchmaking.py

"""Управление очередью пользователей для случайного видеочата."""

from video_chat.services.redis_client import get_redis_client

QUEUE_KEY = "chat:queue"

MATCHMAKING_SCRIPT = """
redis.call("LREM", KEYS[1], 0, ARGV[1])

local partner = redis.call("LPOP", KEYS[1])

if partner then
    return partner
end

redis.call("RPUSH", KEYS[1], ARGV[1])
return false
"""


class MatchmakingService:
    """Управляет очередью ожидания пользователей в Redis."""

    def __init__(self):
        self.redis = get_redis_client()

    def join_queue(self, channel_name: str) -> str | None:
        """Атомарно добавить пользователя в очередь или вернуть партнёра."""

        partner = self.redis.eval(
            MATCHMAKING_SCRIPT,
            1,
            QUEUE_KEY,
            channel_name,
        )

        if partner is None:
            return None

        if isinstance(partner, bytes):
            return partner.decode()

        return str(partner)

    def leave_queue(self, channel_name: str) -> None:
        """Удалить все записи канала из очереди ожидания."""

        self.redis.lrem(
            QUEUE_KEY,
            0,
            channel_name,
        )
