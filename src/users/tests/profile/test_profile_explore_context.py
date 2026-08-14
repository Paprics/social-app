# src/users/tests/profile/test_profile_explore_context.py

"""Tests for lightweight profile Explore context building."""

from unittest.mock import Mock

import pytest
from django.test import RequestFactory

from users.services.profile_context import ProfileContextBuilder


@pytest.fixture
def request_factory():
    """Return a request factory for profile Explore tests."""

    return RequestFactory()


@pytest.mark.django_db
class TestProfileExploreContext:
    def test_explore_context_has_lightweight_contract(
        self,
        request_factory,
        public_owner,
        stranger,
        monkeypatch,
    ):
        """Explore should contain only shared profile state, not preview content."""

        request = request_factory.get("/")
        request.user = stranger

        monkeypatch.setattr(
            "users.services.profile_context.builder.ProfileVisitService.record",
            Mock(),
        )

        context = ProfileContextBuilder.build_explore(
            request,
            public_owner.pk,
        )

        assert set(context) == {
            "target_user",
            "is_owner",
            "access",
            "friendship",
            "favorite_url",
            "is_favorite",
            "is_blocked",
            "viewer_has_blocked",
            "target_has_blocked",
            "mutual_friends_count",
        }

        assert set(context["access"]) == {
            "can_view_profile",
            "can_view_friends",
            "can_send_message",
            "can_view_wall",
            "can_post_on_wall",
        }

        assert context["target_user"] == public_owner
        assert context["is_owner"] is False

    def test_explore_does_not_load_profile_preview_content(
        self,
        request_factory,
        public_owner,
        stranger,
        monkeypatch,
    ):
        """Explore shell must not load albums, friends or mutual-friend previews."""

        request = request_factory.get("/")
        request.user = stranger

        content_mock = Mock(side_effect=AssertionError("Profile preview content must not be loaded for Explore."))

        monkeypatch.setattr(
            "users.services.profile_context.builder.build_profile_content",
            content_mock,
        )

        monkeypatch.setattr(
            "users.services.profile_context.builder.ProfileVisitService.record",
            Mock(),
        )

        ProfileContextBuilder.build_explore(
            request,
            public_owner.pk,
        )

        content_mock.assert_not_called()
