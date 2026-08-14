# src/users/tests/profile/test_profile_explore_mutual_friends_context.py

"""Tests for Mutual Friends data in the Profile Explore shell."""

from unittest.mock import Mock

import pytest
from django.test import RequestFactory

from users.services.friendship_service import FriendshipService
from users.services.profile_context import ProfileContextBuilder


@pytest.fixture
def request_factory():
    """Return a request factory."""

    return RequestFactory()


@pytest.mark.django_db
class TestProfileExploreMutualFriendsContext:
    """Test Mutual Friends metadata loaded by the Explore shell."""

    def test_explore_contains_mutual_friends_count(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Explore should expose mutual friends count for an eligible viewer."""

        request = request_factory.get("/")
        request.user = stranger

        base_context = {
            "target_user": owner,
            "is_owner": False,
            "access": {
                "can_view_profile": True,
                "can_view_friends": True,
            },
            "friendship": None,
            "favorite_url": "",
            "is_favorite": False,
            "is_blocked": False,
        }

        monkeypatch.setattr(
            ProfileContextBuilder,
            "_build_base_context",
            Mock(return_value=(base_context, False)),
        )

        monkeypatch.setattr(
            ProfileContextBuilder,
            "_record_visit",
            Mock(),
        )

        count_mock = Mock(return_value=3)

        monkeypatch.setattr(
            "users.services.profile_context.builder.get_mutual_friends_count",
            count_mock,
        )

        context = ProfileContextBuilder.build_explore(
            request,
            owner.pk,
        )

        assert context["mutual_friends_count"] == 3

        count_mock.assert_called_once_with(
            stranger,
            owner,
        )

    def test_anonymous_viewer_has_zero_mutual_friends_count(
        self,
        request_factory,
        owner,
        monkeypatch,
    ):
        """Anonymous viewers should not calculate mutual friends."""

        request = request_factory.get("/")
        request.user = Mock(
            is_authenticated=False,
        )

        base_context = {
            "target_user": owner,
            "is_owner": False,
            "access": {
                "can_view_profile": True,
                "can_view_friends": True,
            },
            "friendship": None,
            "favorite_url": "",
            "is_favorite": False,
            "is_blocked": False,
        }

        monkeypatch.setattr(
            ProfileContextBuilder,
            "_build_base_context",
            Mock(return_value=(base_context, False)),
        )

        monkeypatch.setattr(
            ProfileContextBuilder,
            "_record_visit",
            Mock(),
        )

        count_mock = Mock()

        monkeypatch.setattr(
            "users.services.profile_context.builder.get_mutual_friends_count",
            count_mock,
        )

        context = ProfileContextBuilder.build_explore(
            request,
            owner.pk,
        )

        assert context["mutual_friends_count"] == 0
        count_mock.assert_not_called()

    def test_owner_has_zero_mutual_friends_count(
        self,
        request_factory,
        owner,
        monkeypatch,
    ):
        """Profile owner should not calculate mutual friends with themselves."""

        request = request_factory.get("/")
        request.user = owner

        base_context = {
            "target_user": owner,
            "is_owner": True,
            "access": {
                "can_view_profile": True,
                "can_view_friends": True,
            },
            "friendship": None,
            "favorite_url": "",
            "is_favorite": False,
            "is_blocked": False,
        }

        monkeypatch.setattr(
            ProfileContextBuilder,
            "_build_base_context",
            Mock(return_value=(base_context, False)),
        )

        monkeypatch.setattr(
            ProfileContextBuilder,
            "_record_visit",
            Mock(),
        )

        count_mock = Mock()

        monkeypatch.setattr(
            "users.services.profile_context.builder.get_mutual_friends_count",
            count_mock,
        )

        context = ProfileContextBuilder.build_explore(
            request,
            owner.pk,
        )

        assert context["mutual_friends_count"] == 0
        count_mock.assert_not_called()

    def test_closed_friends_access_has_zero_mutual_friends_count(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Mutual friends should not be calculated when friends are hidden."""

        request = request_factory.get("/")
        request.user = stranger

        base_context = {
            "target_user": owner,
            "is_owner": False,
            "access": {
                "can_view_profile": True,
                "can_view_friends": False,
            },
            "friendship": None,
            "favorite_url": "",
            "is_favorite": False,
            "is_blocked": False,
        }

        monkeypatch.setattr(
            ProfileContextBuilder,
            "_build_base_context",
            Mock(return_value=(base_context, False)),
        )

        monkeypatch.setattr(
            ProfileContextBuilder,
            "_record_visit",
            Mock(),
        )

        count_mock = Mock()

        monkeypatch.setattr(
            "users.services.profile_context.builder.get_mutual_friends_count",
            count_mock,
        )

        context = ProfileContextBuilder.build_explore(
            request,
            owner.pk,
        )

        assert context["mutual_friends_count"] == 0
        count_mock.assert_not_called()
