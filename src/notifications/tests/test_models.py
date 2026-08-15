# src/notifications/tests/test_models.py

"""Tests for Notification model."""

import pytest
from django.db import IntegrityError, transaction

from notifications.models import Notification


@pytest.mark.django_db
class TestNotificationModel:
    def test_photo_like_notification_is_unread_by_default(
        self,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = Notification.objects.create(
            recipient=notification_owner,
            actor=notification_actor,
            kind=Notification.Kind.PHOTO_LIKE,
            photo=notification_photo,
        )

        assert notification.is_read is False
        assert notification.recipient == notification_owner
        assert notification.actor == notification_actor
        assert notification.photo == notification_photo

    def test_duplicate_photo_like_notification_is_rejected(
        self,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        Notification.objects.create(
            recipient=notification_owner,
            actor=notification_actor,
            kind=Notification.Kind.PHOTO_LIKE,
            photo=notification_photo,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Notification.objects.create(
                    recipient=notification_owner,
                    actor=notification_actor,
                    kind=Notification.Kind.PHOTO_LIKE,
                    photo=notification_photo,
                )

    def test_deleting_photo_deletes_notification(
        self,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = Notification.objects.create(
            recipient=notification_owner,
            actor=notification_actor,
            kind=Notification.Kind.PHOTO_LIKE,
            photo=notification_photo,
        )

        notification_id = notification.pk

        notification_photo.delete()

        assert not Notification.objects.filter(
            pk=notification_id,
        ).exists()

    def test_deleting_actor_preserves_notification(
        self,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = Notification.objects.create(
            recipient=notification_owner,
            actor=notification_actor,
            kind=Notification.Kind.PHOTO_LIKE,
            photo=notification_photo,
        )

        notification_actor.delete()

        notification.refresh_from_db()

        assert notification.actor is None
