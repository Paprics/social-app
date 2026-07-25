import os

import redis as redis_lib

QUEUE_KEY = "chat:queue"


class MatchmakingService:
    def __init__(self):
        self.redis = redis_lib.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        )

    def join_queue(self, channel_name: str) -> str | None:
        """Добавить в очередь или забрать партнёра.

        Алгоритм:
        1. lrem — убираем дубли себя (на случай переподключения)
        2. lpop — берём первого ждущего
        3. Если взяли сами себя — кладём обратно и возвращаем None
        4. Если очередь пуста — кладём себя и возвращаем None
        """
        # Шаг 1: убрать возможные дубли текущего канала
        self.redis.lrem(QUEUE_KEY, 0, channel_name)

        # Шаг 2: попробовать взять партнёра
        partner = self.redis.lpop(QUEUE_KEY)
        if partner:
            partner = partner.decode()
            if partner == channel_name:
                # Вытащили сами себя (не должно случаться после lrem выше, но на всякий случай)
                self.redis.rpush(QUEUE_KEY, channel_name)
                return None
            return partner

        # Шаг 3: партнёра нет — встаём в очередь
        self.redis.rpush(QUEUE_KEY, channel_name)
        return None

    def leave_queue(self, channel_name: str):
        """Убрать канал из очереди (при дисконнекте или перед повторным join)."""
        self.redis.lrem(QUEUE_KEY, 0, channel_name)
