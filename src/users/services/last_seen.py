# src/users/services/last_seen.py

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from users.models import Profile


class LastSeenService:
    """Service for updating a user's last seen timestamp."""

    UPDATE_INTERVAL = getattr(settings, "LAST_SEEN_UPDATE_INTERVAL", 300)

    @classmethod
    def get_key(cls, user_id: int) -> str:
        """Return the cache key for throttling updates."""
        return f"last-seen-update:{user_id}"

    @classmethod
    def touch(cls, user_id: int) -> None:
        """Update last_seen if the throttle interval has expired."""
        key = cls.get_key(user_id)

        if cache.get(key):
            return

        Profile.objects.filter(user_id=user_id).update(
            last_seen=timezone.now(),
        )

        cache.set(
            key,
            True,
            timeout=cls.UPDATE_INTERVAL,
        )
