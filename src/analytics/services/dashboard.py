# src/analytics/services/dashboard.py
"""Orchestrates all selectors into a single DashboardData payload."""

from analytics.dto.dashboard import DashboardData, Period
from analytics.selectors import (
    activity,
    content,
    demographics,
    funnel,
    geography,
    health,
    media,
    messenger,
    social,
    users,
)


def build_dashboard(period: Period) -> DashboardData:
    """Собирает весь dashboard за один вызов."""
    return DashboardData(
        period=period,
        overview=users.get_overview_stats(period),
        registrations_chart=users.get_registrations_chart(period),
        active_users_chart=users.get_active_users_chart(period),
        gender_rows=demographics.get_gender_rows(),
        age_rows=demographics.get_age_rows(),
        looking_for_matrix=demographics.get_looking_for_matrix(),
        top_countries=geography.get_top_countries(),
        top_regions=geography.get_top_regions(),
        top_cities=geography.get_top_cities(),
        online_buckets=activity.get_online_buckets(),
        activity_by_hour=activity.get_activity_by_hour(period),
        media_stats=media.get_media_stats(period),
        storage=media.get_storage_stats(),
        social_stats=social.get_social_stats(period),
        messaging_stats=messenger.get_messaging_stats(period),
        content_stats=content.get_content_stats(period),
        funnel=funnel.get_funnel(),
        health_rows=health.get_health_rows(),
    )
