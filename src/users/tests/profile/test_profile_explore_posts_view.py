# src/users/tests/profile/test_profile_explore_posts_view.py

"""Tests for the Posts section of Profile Explore."""

from unittest.mock import Mock, call

import pytest
from django.conf import settings
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from users.views.profile_explore import ProfileExplorePostsView


@pytest.fixture
def request_factory():
    """Return a request factory."""

    return RequestFactory()


@pytest.mark.django_db
class TestProfileExplorePostsView:
    """Test the Posts Explore endpoint."""

    def test_view_uses_post_domain_helpers(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Endpoint should reuse existing post selectors and access helpers."""

        request = request_factory.get("/")
        request.user = stranger

        posts = list(range(3))

        target_mock = Mock(return_value=owner)

        access = Mock()
        access.can_view_profile = True
        access.can_view_wall.return_value = True

        access_mock = Mock(return_value=access)
        posts_mock = Mock(return_value=posts)
        permissions_mock = Mock(
            return_value={
                "can_edit": False,
                "can_delete": False,
            }
        )
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_owner",
            target_mock,
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.build_post_access",
            access_mock,
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_posts",
            posts_mock,
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_post_permissions",
            permissions_mock,
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExplorePostsView.as_view()(
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
        posts_mock.assert_called_once_with(
            owner=owner,
        )

        assert permissions_mock.call_count == len(posts)

    def test_missing_target_returns_404(
        self,
        request_factory,
        stranger,
        monkeypatch,
    ):
        """Unknown profile should return 404."""

        request = request_factory.get("/")
        request.user = stranger

        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_owner",
            Mock(side_effect=Http404),
            raising=False,
        )

        with pytest.raises(Http404):
            ProfileExplorePostsView.as_view()(
                request,
                pk=999999,
            )

    def test_closed_profile_stops_before_loading_posts(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Closed profile should return 404 before loading wall posts."""

        request = request_factory.get("/")
        request.user = stranger

        access = Mock()
        access.can_view_profile = False

        posts_mock = Mock()
        permissions_mock = Mock()

        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_owner",
            Mock(return_value=owner),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.build_post_access",
            Mock(return_value=access),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_posts",
            posts_mock,
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_post_permissions",
            permissions_mock,
            raising=False,
        )

        with pytest.raises(Http404):
            ProfileExplorePostsView.as_view()(
                request,
                pk=owner.pk,
            )

        access.can_view_wall.assert_not_called()
        posts_mock.assert_not_called()
        permissions_mock.assert_not_called()

    def test_disabled_wall_does_not_leak_posts(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Disabled wall should render unavailable state without loading posts."""

        request = request_factory.get("/")
        request.user = stranger

        access = Mock()
        access.can_view_profile = True
        access.can_view_wall.return_value = False

        posts_mock = Mock()
        permissions_mock = Mock()
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_owner",
            Mock(return_value=owner),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.build_post_access",
            Mock(return_value=access),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_posts",
            posts_mock,
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_post_permissions",
            permissions_mock,
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExplorePostsView.as_view()(
            request,
            pk=owner.pk,
        )

        assert response.status_code == 200

        posts_mock.assert_not_called()
        permissions_mock.assert_not_called()

        context = render_mock.call_args.args[2]

        assert context["can_view_wall"] is False
        assert context["posts"] == []
        assert context["post_items"] == []
        assert context["page_obj"] is None
        assert context["paginator"] is None

    def test_first_page_contains_configured_count(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Explore should paginate wall posts using configured page size."""

        request = request_factory.get("/?page=1")
        request.user = stranger

        access = Mock()
        access.can_view_profile = True
        access.can_view_wall.return_value = True

        posts = list(range(500))
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_owner",
            Mock(return_value=owner),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.build_post_access",
            Mock(return_value=access),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_posts",
            Mock(return_value=posts),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_post_permissions",
            Mock(return_value={}),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExplorePostsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]
        page_size = settings.PROFILE_EXPLORE_POSTS_PER_PAGE

        assert len(context["posts"]) == page_size
        assert len(context["post_items"]) == page_size
        assert context["page_obj"].number == 1

    def test_second_page_contains_next_posts(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Second request should return the next wall posts page."""

        request = request_factory.get("/?page=2")
        request.user = stranger

        access = Mock()
        access.can_view_profile = True
        access.can_view_wall.return_value = True

        posts = list(range(500))
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_owner",
            Mock(return_value=owner),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.build_post_access",
            Mock(return_value=access),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_posts",
            Mock(return_value=posts),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_post_permissions",
            Mock(return_value={}),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExplorePostsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]
        page_size = settings.PROFILE_EXPLORE_POSTS_PER_PAGE

        assert list(context["posts"]) == posts[page_size : page_size * 2]
        assert context["page_obj"].number == 2

    def test_builds_permissions_for_each_visible_post(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Each rendered post should receive its own UI permissions."""

        request = request_factory.get("/")
        request.user = stranger

        access = Mock()
        access.can_view_profile = True
        access.can_view_wall.return_value = True

        posts = [101, 102, 103]

        permissions_mock = Mock(
            side_effect=lambda *, access, post: {
                "post_id": post,
            }
        )
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_owner",
            Mock(return_value=owner),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.build_post_access",
            Mock(return_value=access),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_wall_posts",
            Mock(return_value=posts),
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_post_permissions",
            permissions_mock,
            raising=False,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExplorePostsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]

        assert context["post_items"] == [
            {
                "post": 101,
                "permissions": {
                    "post_id": 101,
                },
            },
            {
                "post": 102,
                "permissions": {
                    "post_id": 102,
                },
            },
            {
                "post": 103,
                "permissions": {
                    "post_id": 103,
                },
            },
        ]

        assert permissions_mock.call_args_list == [
            call(
                access=access,
                post=101,
            ),
            call(
                access=access,
                post=102,
            ),
            call(
                access=access,
                post=103,
            ),
        ]
