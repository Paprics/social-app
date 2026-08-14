# src/users/tests/profile/test_profile_explore_photos_view.py

"""Tests for the Photos section of Profile Explore."""

from unittest.mock import Mock

import pytest
from django.conf import settings
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from users.views.profile_explore import ProfileExplorePhotosView


@pytest.fixture
def request_factory():
    """Return a request factory for Explore Photos tests."""

    return RequestFactory()


@pytest.mark.django_db
class TestProfileExplorePhotosView:
    def test_view_uses_gallery_domain_selectors(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Photos endpoint should delegate gallery rules to the gallery domain."""

        request = request_factory.get("/")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": True,
            "can_view_gallery": True,
            "gallery_access": Mock(),
        }

        photos = list(range(10))

        target_mock = Mock(return_value=owner)
        access_mock = Mock(return_value=access)
        photos_mock = Mock(return_value=photos)
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_target_user",
            target_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_access_context",
            access_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_photos",
            photos_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExplorePhotosView.as_view()(
            request,
            pk=owner.pk,
        )

        assert response.status_code == 200

        target_mock.assert_called_once_with(
            user_id=owner.pk,
        )
        access_mock.assert_called_once_with(
            viewer=stranger,
            target=owner,
        )
        photos_mock.assert_called_once_with(
            target=owner,
            access=access,
        )

    def test_missing_target_returns_404(
        self,
        request_factory,
        stranger,
        monkeypatch,
    ):
        """Photos endpoint should return 404 for an unknown profile."""

        request = request_factory.get("/")
        request.user = stranger

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_target_user",
            Mock(return_value=None),
        )

        with pytest.raises(Http404):
            ProfileExplorePhotosView.as_view()(
                request,
                pk=999999999,
            )

    def test_denied_gallery_does_not_leak_photos(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Denied gallery access should render without exposing photo data."""

        request = request_factory.get("/")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": True,
            "can_view_gallery": False,
            "gallery_access": Mock(),
        }

        photos_mock = Mock(return_value=[])
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_target_user",
            Mock(return_value=owner),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_access_context",
            Mock(return_value=access),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_photos",
            photos_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExplorePhotosView.as_view()(
            request,
            pk=owner.pk,
        )

        assert response.status_code == 200

        render_context = render_mock.call_args.args[2]

        assert render_context["can_view_gallery"] is False
        assert list(render_context["photos"]) == []

    def test_first_page_contains_configured_photos_count(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Explore should never render the entire photos collection at once."""

        request = request_factory.get("/?page=1")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": True,
            "can_view_gallery": True,
            "gallery_access": Mock(),
        }

        photos = list(range(500))
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_target_user",
            Mock(return_value=owner),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_access_context",
            Mock(return_value=access),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_photos",
            Mock(return_value=photos),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExplorePhotosView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]
        page_size = settings.GALLERY_PHOTOS_PER_PAGE

        assert len(context["photos"]) == page_size
        assert context["page_obj"].number == 1
        assert context["page_obj"].has_next() is True
        assert context["paginator"].count == 500

    def test_second_page_contains_next_photos(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Second request should return the next photos page."""

        request = request_factory.get("/?page=2")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": True,
            "can_view_gallery": True,
            "gallery_access": Mock(),
        }

        photos = list(range(500))
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_target_user",
            Mock(return_value=owner),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_access_context",
            Mock(return_value=access),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_photos",
            Mock(return_value=photos),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExplorePhotosView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]
        page_size = settings.GALLERY_PHOTOS_PER_PAGE

        assert list(context["photos"]) == list(
            range(
                page_size,
                page_size * 2,
            )
        )
        assert context["page_obj"].number == 2

    def test_closed_profile_stops_before_loading_photos(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Closed profile should stop the Photos endpoint before photo loading."""

        request = request_factory.get("/")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": False,
            "can_view_gallery": False,
            "gallery_access": Mock(),
        }

        photos_mock = Mock(side_effect=AssertionError("Photos must not be loaded when profile access is denied."))

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_target_user",
            Mock(return_value=owner),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_access_context",
            Mock(return_value=access),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_photos",
            photos_mock,
        )

        with pytest.raises(Http404):
            ProfileExplorePhotosView.as_view()(
                request,
                pk=owner.pk,
            )

        photos_mock.assert_not_called()
