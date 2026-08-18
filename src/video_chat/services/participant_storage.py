# src/video_chat/services/participant_storage.py

"""Временные metadata активных участников видеочата в Redis."""

import json
import os

import redis as redis_lib

PARTICIPANTS_KEY = "chat:participants"
PARTICIPANT_TTL = 21600


class ParticipantStorage:
    """Связывает channel_name с текущей VideoChatSession и identity metadata."""

    def __init__(self):
        self.redis = redis_lib.from_url(
            os.environ.get(
                "REDIS_URL",
                "redis://localhost:6379/0",
            )
        )

    def save(self, channel_name: str, metadata: dict) -> None:
        """Сохранить metadata активного участника."""

        self.redis.hset(
            PARTICIPANTS_KEY,
            channel_name,
            json.dumps(metadata),
        )
        self.redis.expire(
            PARTICIPANTS_KEY,
            PARTICIPANT_TTL,
        )

    def get(self, channel_name: str) -> dict | None:
        """Вернуть metadata участника по channel_name."""

        raw = self.redis.hget(
            PARTICIPANTS_KEY,
            channel_name,
        )

        if raw is None:
            return None

        return json.loads(raw)

    def delete(self, channel_name: str) -> None:
        """Удалить metadata участника."""

        if channel_name:
            self.redis.hdel(
                PARTICIPANTS_KEY,
                channel_name,
            )
