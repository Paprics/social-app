# src/analytics/selectors/geography.py
"""Geographic distribution of users."""

from django.db.models import Count

from analytics.dto.dashboard import GeoRow
from users.models.profile import Profile


def get_top_countries(limit: int = 10) -> list[GeoRow]:
    qs = (
        Profile.objects.filter(user__is_active=True, country__isnull=False)
        .values("country__name_en")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    total = Profile.objects.filter(user__is_active=True).count() or 1
    return [
        GeoRow(name=r["country__name_en"], count=r["count"],
               pct=round(r["count"] / total * 100, 1))
        for r in qs
    ]


def get_top_regions(limit: int = 10) -> list[GeoRow]:
    qs = (
        Profile.objects.filter(user__is_active=True, region__isnull=False)
        .values("region__name_en")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    total = Profile.objects.filter(user__is_active=True).count() or 1
    return [
        GeoRow(name=r["region__name_en"], count=r["count"],
               pct=round(r["count"] / total * 100, 1))
        for r in qs
    ]


def get_top_cities(limit: int = 10) -> list[GeoRow]:
    qs = (
        Profile.objects.filter(user__is_active=True, city__isnull=False)
        .values("city__name_en")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    total = Profile.objects.filter(user__is_active=True).count() or 1
    return [
        GeoRow(name=r["city__name_en"], count=r["count"],
               pct=round(r["count"] / total * 100, 1))
        for r in qs
    ]
