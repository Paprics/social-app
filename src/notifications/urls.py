# src/notifications/urls.py

from django.urls import path

from notifications.views import (
    NotificationListView,
    NotificationMarkAllReadView,
    NotificationMarkReadView,
)

app_name = "notifications"

urlpatterns = [
    path(
        "list/",
        NotificationListView.as_view(),
        name="list",
    ),
    path(
        "mark-all-read/",
        NotificationMarkAllReadView.as_view(),
        name="mark_all_read",
    ),
    path(
        "<int:notification_id>/read/",
        NotificationMarkReadView.as_view(),
        name="mark_read",
    ),
]
