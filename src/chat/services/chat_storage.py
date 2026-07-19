import json
import os
import time
import redis as redis_lib

CHAT_TTL = 3600  # 1 час
CHAT_KEY_PREFIX = "chat:messages:"


class ChatStorage:
    """Хранение сообщений текстового чата в Redis с TTL.

    Сообщения не попадают в PostgreSQL — только in-memory Redis.
    При разрыве сессии чат удаляется явно или истекает по TTL.
    """

    def __init__(self):
        self.redis = redis_lib.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        )

    def _key(self, room_id: str) -> str:
        return f"{CHAT_KEY_PREFIX}{room_id}"

    def save_message(self, room_id: str, sender: str, text: str) -> dict:
        """Сохранить сообщение и обновить TTL ключа."""
        message = {
            "sender": sender,
            "text": text,
            "timestamp": time.time(),
        }
        key = self._key(room_id)
        self.redis.rpush(key, json.dumps(message))
        self.redis.expire(key, CHAT_TTL)
        return message

    def get_messages(self, room_id: str) -> list[dict]:
        """Получить всю историю чата комнаты."""
        key = self._key(room_id)
        raw = self.redis.lrange(key, 0, -1)
        return [json.loads(m) for m in raw]

    def delete_chat(self, room_id: str):
        """Явно удалить чат при завершении сессии."""
        self.redis.delete(self._key(room_id))
