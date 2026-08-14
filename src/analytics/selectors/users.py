# src/analytics/selectors/users.py
"""Aggregation queries for user counts, growth and activity."""

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.db.models.functions import (
    TruncDay, TruncHour, TruncMonth, TruncWeek,
)
from django.utils import timezone

from analytics.dto.dashboard import ChartPoint, Period, StatCard
from users.models.profile import Profile

User = get_user_model()

_TRUNC = {
    "hour": TruncHour,
    "day": TruncDay,
    "week": TruncWeek,
    "month": TruncMonth,
}


def get_overview_stats(period: Period) -> list[StatCard]:
    """Основные пользовательские метрики за период и предыдущий."""
    total = User.objects.filter(is_active=True).count()
    prev_total = (
        User.objects.filter(is_active=True, date_joined__lt=period.start).count()
    )

    new = User.objects.filter(date_joined__range=(period.start, period.end)).count()
    prev_new = User.objects.filter(
        date_joined__range=(period.prev_start, period.prev_end)
    ).count()

    active = Profile.objects.filter(
        last_seen__gte=period.start
    ).count()
    prev_active = Profile.objects.filter(
        last_seen__range=(period.prev_start, period.prev_end)
    ).count()

    online_now = Profile.objects.filter(
        last_seen__gte=timezone.now() - timezone.timedelta(minutes=5)
    ).count()

    return [
        StatCard("Online now", online_now, 0, fmt="int"),
        StatCard("Total users", total, prev_total, fmt="int"),
        StatCard("New registrations", new, prev_new, fmt="int"),
        StatCard("Active users", active, prev_active, fmt="int"),
    ]


def get_registrations_chart(period: Period) -> list[ChartPoint]:
    """Регистрации по временным меткам для line chart."""
    trunc_fn = _TRUNC.get(period.granularity, TruncDay)
    qs = (
        User.objects.filter(date_joined__range=(period.start, period.end))
        .annotate(bucket=trunc_fn("date_joined"))
        .values("bucket")
        .annotate(count=Count("id"))
        .order_by("bucket")
    )
    return [
        ChartPoint(label=str(row["bucket"].date() if hasattr(row["bucket"], "date") else row["bucket"]),
                   value=row["count"])
        for row in qs
    ]


def get_active_users_chart(period: Period) -> list[ChartPoint]:
    """Активные пользователи (по last_seen) по временным меткам."""
    trunc_fn = _TRUNC.get(period.granularity, TruncDay)
    qs = (
        Profile.objects.filter(last_seen__range=(period.start, period.end))
        .annotate(bucket=trunc_fn("last_seen"))
        .values("bucket")
        .annotate(count=Count("id"))
        .order_by("bucket")
    )
    return [
        ChartPoint(label=str(row["bucket"].date() if hasattr(row["bucket"], "date") else row["bucket"]),
                   value=row["count"])
        for row in qs
    ]
