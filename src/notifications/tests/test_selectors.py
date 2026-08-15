# src/notifications/tests/test_selectors.py

"""Tests for notification selectors."""

import pytest

from notifications.models import Notification
from notifications.selectors import (
    get_unread_notifications_count,
    get_user_notifications,
)
from notifications.services import NotificationService


@pytest.mark.django_db
class TestNotificationSelectors:
    def test_get_user_notifications_returns_recipient_notifications(
        self,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        notifications = get_user_notifications(
            user=notification_owner,
        )

        assert notification in notifications

    def test_get_user_notifications_excludes_other_recipient(
        self,
        notification_owner,
        notification_actor,
        notification_other,
        notification_photo,
    ):
        NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        notifications = get_user_notifications(
            user=notification_other,
        )

        assert not notifications.exists()

    def test_unread_count_counts_only_unread(
        self,
        notification_owner,
        notification_actor,
        notification_other,
        notification_photo,
    ):
        first = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        NotificationService.notify_photo_like(
            actor=notification_other,
            photo=notification_photo,
        )

        NotificationService.mark_read(
            recipient=notification_owner,
            notification_id=first.pk,
        )

        assert (
            get_unread_notifications_count(
                user=notification_owner,
            )
            == 1
        )

    def test_unread_count_can_filter_by_kind(
        self,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        count = get_unread_notifications_count(
            user=notification_owner,
            kind=Notification.Kind.PHOTO_LIKE,
        )

        assert count == 1
