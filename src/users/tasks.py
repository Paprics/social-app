# src/users/tasks.py

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from users.models import ProfileVisit

logger = logging.getLogger(__name__)


@shared_task
def flush_profile_visits_task() -> int:
    """
    Synchronize profile visits from Redis to PostgreSQL.

    Visits are accumulated in Redis and periodically written
    to the database in batches.
    """
    try:
        from django.core.cache import cache

        redis = cache.client.get_client(write=True)

        visits = redis.spop(
            "profile_visits_pending",
            settings.PROFILE_VISITS_BATCH_SIZE,
        )

        if not visits:
            return 0

        now = timezone.now()

        objects = []

        for item in visits:
            visitor_id, profile_id = map(
                int,
                item.decode().split(":"),
            )

            objects.append(
                ProfileVisit(
                    visitor_id=visitor_id,
                    profile_id=profile_id,
                    visited_at=now,
                )
            )

        ProfileVisit.objects.bulk_create(
            objects,
            update_conflicts=True,
            update_fields=[
                "visited_at",
            ],
            unique_fields=[
                "visitor",
                "profile",
            ],
        )

        processed = len(objects)

        logger.info(
            "Flushed %d profile visits from Redis to PostgreSQL.",
            processed,
        )

        return processed

    except Exception:
        logger.exception("Failed to flush profile visits.")
        raise


@shared_task
def cleanup_profile_visits_task() -> int:
    """
    Delete expired profile visit history.
    """
    try:
        threshold = timezone.now() - timedelta(
            days=settings.PROFILE_VISITS_RETENTION_DAYS,
        )

        deleted, _ = ProfileVisit.objects.filter(
            visited_at__lt=threshold,
        ).delete()

        logger.info(
            "Deleted %d expired profile visits.",
            deleted,
        )

        return deleted

    except Exception:
        logger.exception("Failed to cleanup profile visits.")
        raise
