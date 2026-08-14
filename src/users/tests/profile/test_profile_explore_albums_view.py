# src/users/tests/profile/test_profile_explore_albums_view.py

"""Tests for the lazy-loaded Albums section of Profile Explore."""

from django.conf import settings
from unittest.mock import Mock

import pytest
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from users.views.profile_explore import ProfileExploreAlbumsView


@pytest.fixture
def request_factory():
    """Return a request factory for Explore Albums tests."""

    return RequestFactory()


@pytest.mark.django_db
class TestProfileExploreAlbumsView:
    def test_view_uses_gallery_domain_selectors(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Albums endpoint should delegate gallery rules to the gallery domain."""

        request = request_factory.get("/")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": True,
            "can_view_gallery": True,
            "gallery_access": Mock(),
        }

        albums = list(range(10))

        target_mock = Mock(return_value=owner)
        access_mock = Mock(return_value=access)
        albums_mock = Mock(return_value=albums)
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
            "users.views.profile_explore.get_gallery_albums",
            albums_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExploreAlbumsView.as_view()(
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
        albums_mock.assert_called_once_with(
            target=owner,
            access=access,
        )

    def test_missing_target_returns_404(
        self,
        request_factory,
        stranger,
        monkeypatch,
    ):
        """Albums endpoint should return 404 for an unknown profile."""

        request = request_factory.get("/")
        request.user = stranger

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_target_user",
            Mock(return_value=None),
        )

        with pytest.raises(Http404):
            ProfileExploreAlbumsView.as_view()(
                request,
                pk=999999999,
            )

    def test_denied_gallery_does_not_leak_albums(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Denied gallery access should render without exposing album data."""

        request = request_factory.get("/")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": True,
            "can_view_gallery": False,
            "gallery_access": Mock(),
        }

        albums_mock = Mock(return_value=[])
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
            "users.views.profile_explore.get_gallery_albums",
            albums_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExploreAlbumsView.as_view()(
            request,
            pk=owner.pk,
        )

        assert response.status_code == 200

        render_context = render_mock.call_args.args[2]

        assert render_context["can_view_gallery"] is False
        assert list(render_context["albums"]) == []

    def test_first_page_contains_only_24_albums(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Explore should never render the entire albums collection at once."""

        request = request_factory.get("/?page=1")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": True,
            "can_view_gallery": True,
            "gallery_access": Mock(),
        }

        albums = list(range(500))
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
            "users.views.profile_explore.get_gallery_albums",
            Mock(return_value=albums),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExploreAlbumsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]

        page_size = settings.GALLERY_ALBUMS_PER_PAGE

        assert len(context["albums"]) == page_size
        assert context["page_obj"].number == 1
        assert context["page_obj"].has_next() is True
        assert context["paginator"].count == 500

    def test_second_page_contains_next_24_albums(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Second request should return the next albums page."""

        request = request_factory.get("/?page=2")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": True,
            "can_view_gallery": True,
            "gallery_access": Mock(),
        }

        albums = list(range(500))
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
            "users.views.profile_explore.get_gallery_albums",
            Mock(return_value=albums),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExploreAlbumsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]

        page_size = settings.GALLERY_ALBUMS_PER_PAGE

        assert list(context["albums"]) == list(
            range(
                page_size,
                page_size * 2,
            )
        )
        assert context["page_obj"].number == 2

    def test_closed_profile_stops_before_loading_albums(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Closed profile should stop the Albums endpoint before album loading."""

        request = request_factory.get("/")
        request.user = stranger

        access = {
            "is_owner": False,
            "can_view_profile": False,
            "can_view_gallery": False,
            "gallery_access": Mock(),
        }

        albums_mock = Mock(side_effect=AssertionError("Albums must not be loaded when profile access is denied."))

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_target_user",
            Mock(return_value=owner),
        )

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_access_context",
            Mock(return_value=access),
        )

        monkeypatch.setattr(
            "users.views.profile_explore.get_gallery_albums",
            albums_mock,
        )

        with pytest.raises(Http404):
            ProfileExploreAlbumsView.as_view()(
                request,
                pk=owner.pk,
            )

        albums_mock.assert_not_called()
