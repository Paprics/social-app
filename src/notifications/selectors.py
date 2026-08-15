# src/notifications/selectors.py

"""Read queries for notifications."""

from notifications.models import Notification


def get_user_notifications(*, user, kind=None):
    """Return notifications addressed to the user."""

    queryset = (
        Notification.objects.filter(
            recipient=user,
        )
        .select_related(
            "actor",
            "actor__profile",
            "photo",
            "photo__album",
            "photo__album__user",
            "comment",
            "comment__parent",
            "comment__parent__author",
        )
        .order_by(
            "-last_triggered_at",
            "-pk",
        )
    )

    if kind is not None:
        queryset = queryset.filter(
            kind=kind,
        )

    return queryset


def get_unread_notifications_count(*, user, kind=None) -> int:
    """Return unread notification count for the user."""

    queryset = Notification.objects.filter(
        recipient=user,
        is_read=False,
    )

    if kind is not None:
        queryset = queryset.filter(
            kind=kind,
        )

    return queryset.count()
