# src/video_chat/services/participant_storage.py

"""Временные metadata активных участников видеочата в Redis."""

import json
from video_chat.services.redis_client import get_redis_client

PARTICIPANT_KEY_PREFIX = "chat:participant:"
PARTICIPANT_TTL = 21600


class ParticipantStorage:
    """Хранит metadata каждого активного участника в отдельном Redis key."""

    def __init__(self):
        self.redis = get_redis_client()

    @staticmethod
    def _key(channel_name: str) -> str:
        """Вернуть Redis key участника."""

        return f"{PARTICIPANT_KEY_PREFIX}{channel_name}"

    def save(self, channel_name: str, metadata: dict) -> None:
        """Сохранить metadata участника с индивидуальным TTL."""

        self.redis.set(
            self._key(channel_name),
            json.dumps(metadata),
            ex=PARTICIPANT_TTL,
        )

    def get(self, channel_name: str) -> dict | None:
        """Вернуть metadata участника по channel_name."""

        raw = self.redis.get(
            self._key(channel_name)
        )

        if raw is None:
            return None

        return json.loads(raw)

    def delete(self, channel_name: str) -> None:
        """Удалить metadata участника."""

        if channel_name:
            self.redis.delete(
                self._key(channel_name)
            )
