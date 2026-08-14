# src/analytics/selectors/health.py
"""Database health — quality indicators of user accounts."""

from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from analytics.dto.dashboard import HealthRow
from users.models.profile import Profile


def get_health_rows() -> list[HealthRow]:
    """Return quality and completeness indicators for active user profiles."""

    profiles = Profile.objects.filter(
        user__is_active=True,
    )

    total = profiles.count() or 1
    inactive_threshold = timezone.now() - timedelta(days=30)

    no_avatar = profiles.filter(
        avatar_photo__isnull=True,
    ).count()

    no_bio = profiles.filter(
        bio="",
    ).count()

    no_gender = profiles.filter(
        gender="",
    ).count()

    no_city = profiles.filter(
        city__isnull=True,
    ).count()

    no_photo = (
        profiles.annotate(
            photo_count=Count(
                "user__galleries__photos",
                distinct=True,
            )
        )
        .filter(photo_count=0)
        .count()
    )

    inactive_30d = profiles.filter(
        last_seen__lt=inactive_threshold,
    ).count()

    never_posted = (
        profiles.annotate(
            post_count=Count(
                "user__authored_posts",
                distinct=True,
            )
        )
        .filter(post_count=0)
        .count()
    )

    never_messaged = (
        profiles.annotate(
            message_count=Count(
                "user__sent_messages",
                distinct=True,
            )
        )
        .filter(message_count=0)
        .count()
    )

    rows = [
        ("No avatar", no_avatar),
        ("No bio", no_bio),
        ("No gender set", no_gender),
        ("No city set", no_city),
        ("No photos", no_photo),
        ("Inactive > 30d", inactive_30d),
        ("Never posted", never_posted),
        ("Never messaged", never_messaged),
    ]

    return [
        HealthRow(
            label=label,
            count=count,
            pct=round(count / total * 100, 1),
        )
        for label, count in rows
    ]
