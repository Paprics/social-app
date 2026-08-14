# src/analytics/selectors/activity.py
"""Online buckets and hourly activity heatmap."""

from django.db.models import Count
from django.db.models.functions import ExtractHour
from django.utils import timezone

from analytics.dto.dashboard import ChartPoint, Period, StatCard
from users.models.profile import Profile


def get_online_buckets() -> list[StatCard]:
    """Сегменты онлайн-активности по last_seen."""
    now = timezone.now()
    base = Profile.objects.filter(user__is_active=True)

    def _count(minutes=None, days=None):
        if minutes:
            return base.filter(last_seen__gte=now - timezone.timedelta(minutes=minutes)).count()
        return base.filter(last_seen__gte=now - timezone.timedelta(days=days)).count()

    total = base.count() or 1
    buckets = [
        ("Online < 5 min",  _count(minutes=5)),
        ("Active < 1 hour", _count(minutes=60)),
        ("Active < 24h",    _count(days=1)),
        ("Active < 7d",     _count(days=7)),
        ("Active < 30d",    _count(days=30)),
        ("Dormant > 30d",   base.filter(last_seen__lt=now - timezone.timedelta(days=30)).count()),
    ]
    return [
        StatCard(label, count, 0, unit=f"{round(count/total*100,1)}%")
        for label, count in buckets
    ]


def get_activity_by_hour(period: Period) -> list[ChartPoint]:
    """Кол-во уникальных активных пользователей по часу суток."""
    qs = (
        Profile.objects.filter(last_seen__range=(period.start, period.end))
        .annotate(hour=ExtractHour("last_seen"))
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )
    hour_map = {r["hour"]: r["count"] for r in qs}
    return [
        ChartPoint(label=f"{h:02d}:00", value=hour_map.get(h, 0))
        for h in range(24)
    ]
