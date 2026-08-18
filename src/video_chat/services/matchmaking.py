# src/video_chat/services/matchmaking.py

"""Управление очередью пользователей для случайного видеочата."""

import os

import redis as redis_lib

QUEUE_KEY = "chat:queue"


class MatchmakingService:
    """Управляет очередью ожидания пользователей в Redis."""

    def __init__(self):
        self.redis = redis_lib.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))

    def join_queue(self, channel_name: str) -> str | None:
        """Добавить пользователя в очередь или вернуть ожидающего партнёра."""

        # Удаляем старые записи этого канала после возможного переподключения.
        self.redis.lrem(QUEUE_KEY, 0, channel_name)

        partner = self.redis.lpop(QUEUE_KEY)

        if partner:
            partner = partner.decode()

            # Защита от неконсистентного состояния очереди.
            if partner == channel_name:
                self.redis.rpush(QUEUE_KEY, channel_name)
                return None

            return partner

        self.redis.rpush(QUEUE_KEY, channel_name)
        return None

    def leave_queue(self, channel_name: str) -> None:
        """Удалить все записи канала из очереди ожидания."""

        self.redis.lrem(QUEUE_KEY, 0, channel_name)
