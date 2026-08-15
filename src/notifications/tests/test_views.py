# src/notifications/tests/test_views.py

"""Tests for notification views."""

import pytest
from django.urls import reverse

from notifications.models import Notification
from notifications.services import NotificationService


@pytest.mark.django_db
class TestNotificationListView:
    def test_anonymous_user_is_redirected(
        self,
        client,
    ):
        response = client.get(
            reverse("notifications:list"),
        )

        assert response.status_code == 302

    def test_user_can_view_own_notifications(
        self,
        client,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        client.force_login(
            notification_owner,
        )

        response = client.get(
            reverse("notifications:list"),
        )

        assert response.status_code == 200
        assert notification in response.context["notification_items"]

    def test_user_does_not_see_other_users_notifications(
        self,
        client,
        notification_owner,
        notification_actor,
        notification_other,
        notification_photo,
    ):
        NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        client.force_login(
            notification_other,
        )

        response = client.get(
            reverse("notifications:list"),
        )

        assert response.status_code == 200
        assert list(response.context["notification_items"]) == []

    def test_kind_filter_returns_photo_likes(
        self,
        client,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        client.force_login(
            notification_owner,
        )

        response = client.get(
            reverse("notifications:list"),
            {
                "kind": Notification.Kind.PHOTO_LIKE,
            },
        )

        assert response.status_code == 200
        assert notification in response.context["notification_items"]
        assert response.context["current_kind"] == Notification.Kind.PHOTO_LIKE

    def test_invalid_kind_falls_back_to_all(
        self,
        client,
        notification_owner,
    ):
        client.force_login(
            notification_owner,
        )

        response = client.get(
            reverse("notifications:list"),
            {
                "kind": "something-invalid",
            },
        )

        assert response.status_code == 200
        assert response.context["current_kind"] is None

    def test_user_can_mark_own_notification_read(
        self,
        client,
        notification_owner,
        notification_actor,
        notification_photo,
    ):
        notification = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        client.force_login(notification_owner)

        response = client.post(
            reverse(
                "notifications:mark_read",
                kwargs={
                    "notification_id": notification.pk,
                },
            ),
        )

        notification.refresh_from_db()

        assert response.status_code == 200
        assert notification.is_read is True
        assert response.headers["HX-Refresh"] == "true"

    def test_user_cannot_mark_other_users_notification_read(
        self,
        client,
        notification_actor,
        notification_other,
        notification_photo,
    ):
        notification = NotificationService.notify_photo_like(
            actor=notification_actor,
            photo=notification_photo,
        )

        client.force_login(notification_other)

        client.post(
            reverse(
                "notifications:mark_read",
                kwargs={
                    "notification_id": notification.pk,
                },
            ),
        )

        notification.refresh_from_db()

        assert notification.is_read is False

    def test_mark_all_read_marks_current_users_notifications(
        self,
        client,
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

        client.force_login(notification_owner)

        response = client.post(
            reverse("notifications:mark_all_read"),
        )

        first.refresh_from_db()
        second.refresh_from_db()

        assert response.status_code == 200
        assert first.is_read is True
        assert second.is_read is True
        assert response.headers["HX-Refresh"] == "true"
