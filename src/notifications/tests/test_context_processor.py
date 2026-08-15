# src/notifications/tests/test_context_processor.py

"""Tests for notification context processor."""

import pytest
from django.test import RequestFactory

from notifications.context_processor import notifications_context
from notifications.services import NotificationService


@pytest.mark.django_db
def test_photo_like_is_in_global_notification_count(
    notification_owner,
    notification_actor,
    notification_photo,
):
    NotificationService.notify_photo_like(
        actor=notification_actor,
        photo=notification_photo,
    )

    request = RequestFactory().get("/")
    request.user = notification_owner

    context = notifications_context(
        request,
    )

    assert context["notifications"]["likes"] == 1
    assert context["notifications"]["count"] == 1
    assert context["notifications"]["has_notifications"] is True
