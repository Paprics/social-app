# src/notifications/tests/test_services.py

"""Tests for NotificationService."""

import pytest

from notifications.models import Notification
from notifications.services import NotificationService


@pytest.mark.django_db
class TestNotificationService:
    def test_notify_photo_like_creates_notification(
        self,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        assert notification is not None
        assert notification.recipient == notification_owner
        assert notification.actor == notification_actor
        assert notification.photo == notification_photo
        assert notification.kind == Notification.Kind.PHOTO_LIKE
        assert notification.is_read is False

    def test_own_photo_like_does_not_create_notification(
        self,
        notification_owner,
        notification_photo,
    ):
        result = NotificationService.notify_photo_like(
            actor=notification_owner,
            photo=notification_photo,
        )

        assert result is None
        assert Notification.objects.count() == 0

    def test_repeated_photo_like_reuses_notification(
        self,
        notification_actor,
        notification_photo,
    ):
        first = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        first.is_read = True
        first.save(
            update_fields=[
                "is_read",
            ]
        )

        first_triggered_at = first.last_triggered_at

        second = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        assert second.pk == first.pk
        assert Notification.objects.count() == 1
        assert second.is_read is False
        assert second.last_triggered_at >= first_triggered_at

    def test_mark_read_marks_recipient_notification(
        self,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        result = NotificationService.mark_read(
            recipient=notification_owner,
            notification_id=notification.pk,
        )

        notification.refresh_from_db()

        assert result is True
        assert notification.is_read is True

    def test_user_cannot_mark_another_users_notification_read(
        self,
        notification_other,
        notification_actor,
        notification_photo,
    ):
        notification = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        result = NotificationService.mark_read(
            recipient=notification_other,
            notification_id=notification.pk,
        )

        notification.refresh_from_db()

        assert result is False
        assert notification.is_read is False

    def test_mark_all_read_marks_all_recipient_notifications(
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

        second = NotificationService.notify_photo_like(
            actor=notification_other,
            photo=notification_photo,
        )

        updated = NotificationService.mark_all_read(
            recipient=notification_owner,
        )

        first.refresh_from_db()
        second.refresh_from_db()

        assert updated == 2
        assert first.is_read is True
        assert second.is_read is True
