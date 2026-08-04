# users/services/online.py
from django.core.cache import cache
from django.conf import settings


class OnlineService:
    """Service for tracking user online status."""

    ONLINE_TIMEOUT = getattr(settings, "ONLINE_TIMEOUT", 120)

    @classmethod
    def get_key(cls, user_id: int) -> str:
        """Return the cache key for a user's online status."""
        return f"online:user:{user_id}"

    @classmethod
    def touch(cls, user_id: int) -> None:
        """Mark the user as online and refresh the TTL."""
        cache.set(
            cls.get_key(user_id),
            True,
            timeout=cls.ONLINE_TIMEOUT,
        )

    @classmethod
    def is_online(cls, user_id: int) -> bool:
        """Return whether the user is currently online."""
        return cache.get(cls.get_key(user_id)) is not None

    @classmethod
    def mark_offline(cls, user_id: int) -> None:
        """Immediately mark the user as offline."""
        cache.delete(cls.get_key(user_id))
