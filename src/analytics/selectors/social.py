# src/analytics/selectors/social.py
"""Friendship, favorites and block statistics."""

from django.db.models import Count

from analytics.dto.dashboard import Period, StatCard
from users.models.favorite import Favorite
from users.models.friendship import Friendship
from users.models.user_block import UserBlock


def get_social_stats(period: Period) -> list[StatCard]:
    """Друзья, избранное и блокировки."""
    accepted = Friendship.Status.ACCEPTED
    pending = Friendship.Status.PENDING

    total_friends = Friendship.objects.filter(status=accepted).count()
    new_friends = Friendship.objects.filter(
        status=accepted, updated_at__range=(period.start, period.end)
    ).count()
    prev_friends = Friendship.objects.filter(
        status=accepted, updated_at__range=(period.prev_start, period.prev_end)
    ).count()

    sent_requests = Friendship.objects.filter(
        created_at__range=(period.start, period.end)
    ).count()
    prev_sent = Friendship.objects.filter(
        created_at__range=(period.prev_start, period.prev_end)
    ).count()

    pending_count = Friendship.objects.filter(status=pending).count()

    total_fav = Favorite.objects.count()
    new_fav = Favorite.objects.filter(created_at__range=(period.start, period.end)).count()
    prev_fav = Favorite.objects.filter(
        created_at__range=(period.prev_start, period.prev_end)
    ).count()

    total_blocks = UserBlock.objects.count()
    new_blocks = UserBlock.objects.filter(
        created_at__range=(period.start, period.end)
    ).count()

    return [
        StatCard("Total friendships", total_friends, total_friends - new_friends),
        StatCard("New friendships", new_friends, prev_friends),
        StatCard("Friend requests sent", sent_requests, prev_sent),
        StatCard("Pending requests", pending_count, 0),
        StatCard("Total favorites", total_fav, total_fav - new_fav),
        StatCard("New favorites", new_fav, prev_fav),
        StatCard("Total blocks", total_blocks, 0),
        StatCard("New blocks", new_blocks, 0),
    ]
