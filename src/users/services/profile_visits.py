# src/users/services/profile_visits.py

import logging

from django.core.cache import cache
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class ProfileVisitService:
    """
    Buffers profile visits in Redis.

    A visit is counted at most once per hour for each
    (visitor, profile) pair.

    Pending visits are periodically synchronized to PostgreSQL
    by a scheduled Celery task.
    """

    LOCK_PREFIX = "profile_visit_lock"
    PENDING_KEY = "profile_visits_pending"
    LOCK_TIMEOUT = 60 * 60

    @classmethod
    def record(cls, visitor_id: int, target_id: int) -> None:
        """
        Record a profile visit.

        Duplicate visits within one hour are ignored.
        If Redis is unavailable, the request continues normally.
        """

        if visitor_id == target_id:
            return

        lock_key = f"{cls.LOCK_PREFIX}:{visitor_id}:{target_id}"

        try:
            # Atomically create the lock only if it does not exist.
            if not cache.add(
                lock_key,
                True,
                timeout=cls.LOCK_TIMEOUT,
            ):
                return

            redis = cache.client.get_client(write=True)

            # Queue the visit for periodic synchronization.
            redis.sadd(
                cls.PENDING_KEY,
                f"{visitor_id}:{target_id}",
            )

        except RedisError:
            logger.exception(
                "Failed to record profile visit (%s -> %s).",
                visitor_id,
                target_id,
            )
