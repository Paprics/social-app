# src/video_chat/services/redis_client.py

"""Общий Redis client для сервисов видеочата."""

import os
from functools import lru_cache

import redis as redis_lib


@lru_cache(maxsize=1)
def get_redis_client():
    """Вернуть общий Redis client с connection pool."""

    return redis_lib.from_url(
        os.environ.get(
            "REDIS_URL",
            "redis://localhost:6379/0",
        )
    )
