# src/analytics/services/periods.py
"""Build AnalyticsPeriod from a string label or custom date range."""

from datetime import timedelta

from django.utils import timezone

from analytics.dto.dashboard import Period

_LABELS = {
    "24h": (1, "hour"),
    "7d": (7, "day"),
    "30d": (30, "day"),
    "90d": (90, "week"),
    "year": (365, "month"),
    "all": (None, "month"),
}


def build_period(label: str, date_from=None, date_to=None) -> Period:
    """Вернуть Period по label или кастомному диапазону дат."""
    now = timezone.now()

    if label == "custom" and date_from and date_to:
        start = timezone.make_aware(date_from) if timezone.is_naive(date_from) else date_from
        end = timezone.make_aware(date_to) if timezone.is_naive(date_to) else date_to
        delta = end - start
        prev_start = start - delta
        prev_end = start
        days = delta.days
        granularity = _granularity(days)
        return Period(label="custom", start=start, end=end,
                      prev_start=prev_start, prev_end=prev_end,
                      granularity=granularity)

    if label not in _LABELS:
        label = "30d"

    days, granularity = _LABELS[label]

    if days is None:
        # "all" — от первой записи, но в контексте periods просто берём 3 года
        start = now - timedelta(days=365 * 3)
        granularity = "month"
    elif label == "24h":
        start = now - timedelta(hours=24)
    else:
        start = now - timedelta(days=days)

    end = now
    delta = end - start
    prev_start = start - delta
    prev_end = start

    return Period(label=label, start=start, end=end,
                  prev_start=prev_start, prev_end=prev_end,
                  granularity=granularity)


def _granularity(days: int) -> str:
    if days <= 1:
        return "hour"
    if days <= 90:
        return "day"
    if days <= 365:
        return "week"
    return "month"
