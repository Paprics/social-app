# src/gallery/tests/likes/test_notifications.py

"""Tests for notifications produced by gallery likes."""

import pytest

from gallery.services.likes import LikeService
from notifications.models import Notification


@pytest.mark.django_db
class TestLikeNotifications:
    def test_liking_photo_creates_owner_notification(
        self,
        gallery_owner,
        gallery_other,
        gallery_photo,
    ):
        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        notification = Notification.objects.get(
            recipient=gallery_owner,
            actor=gallery_other,
            photo=gallery_photo,
            kind=Notification.Kind.PHOTO_LIKE,
        )

        assert notification.is_read is False

    def test_relike_creates_new_notification(
        self,
        gallery_owner,
        gallery_other,
        gallery_photo,
    ):
        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        first_notification = Notification.objects.get(
            recipient=gallery_owner,
            actor=gallery_other,
            photo=gallery_photo,
            kind=Notification.Kind.PHOTO_LIKE,
        )

        first_notification_id = first_notification.pk

        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        assert not Notification.objects.filter(
            pk=first_notification_id,
        ).exists()

        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        second_notification = Notification.objects.get(
            recipient=gallery_owner,
            actor=gallery_other,
            photo=gallery_photo,
            kind=Notification.Kind.PHOTO_LIKE,
        )

        assert second_notification.pk != first_notification_id
        assert second_notification.is_read is False

    def test_liking_own_photo_does_not_create_notification(
        self,
        gallery_owner,
        gallery_photo,
    ):
        LikeService.toggle(
            user=gallery_owner,
            photo=gallery_photo,
        )

        assert not Notification.objects.exists()

    def test_unlike_removes_photo_like_notification(
        self,
        gallery_owner,
        gallery_other,
        gallery_photo,
    ):
        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        assert Notification.objects.filter(
            recipient=gallery_owner,
            actor=gallery_other,
            kind=Notification.Kind.PHOTO_LIKE,
            photo=gallery_photo,
        ).exists()

        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        assert not Notification.objects.filter(
            recipient=gallery_owner,
            actor=gallery_other,
            kind=Notification.Kind.PHOTO_LIKE,
            photo=gallery_photo,
        ).exists()
