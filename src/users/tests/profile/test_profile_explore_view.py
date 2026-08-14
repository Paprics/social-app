# src/users/tests/profile/test_profile_explore_view.py

"""Tests for the Profile Explore shell view."""

from unittest.mock import Mock

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from users.views.profile_explore import ProfileExploreView


@pytest.fixture
def request_factory():
    """Return a request factory for Explore view tests."""

    return RequestFactory()


@pytest.mark.django_db
class TestProfileExploreView:
    def test_view_uses_profile_context_builder(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Explore view should delegate context building to ProfileContextBuilder."""

        request = request_factory.get("/")
        request.user = stranger

        expected_context = {
            "target_user": owner,
            "is_owner": False,
            "access": {},
            "friendship": None,
            "favorite_url": "/favorite/",
            "is_favorite": False,
            "is_blocked": False,
        }

        build_explore_mock = Mock(
            return_value=expected_context,
        )

        monkeypatch.setattr(
            "users.views.profile_explore.ProfileContextBuilder.build_explore",
            build_explore_mock,
        )

        view = ProfileExploreView()
        view.request = request
        view.kwargs = {
            "pk": owner.pk,
        }

        context = view.get_context_data()

        build_explore_mock.assert_called_once_with(
            request,
            owner.pk,
        )

        assert context["target_user"] == owner
