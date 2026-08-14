# src/analytics/urls.py
"""URL configuration for analytics app."""

from django.urls import path

from analytics.views.dashboard import AnalyticsDashboardView

app_name = "analytics"

urlpatterns = [
    path("", AnalyticsDashboardView.as_view(), name="dashboard"),
]
