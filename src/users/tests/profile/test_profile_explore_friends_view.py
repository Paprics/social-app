# src/users/tests/profile/test_profile_explore_friends_view.py

"""Tests for the Friends section of Profile Explore."""

from unittest.mock import Mock

import pytest
from django.conf import settings
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from users.views.profile_explore import ProfileExploreFriendsView


@pytest.fixture
def request_factory():
    """Return a request factory for Explore Friends tests."""

    return RequestFactory()


def make_friendships(*, target, count):
    """Build lightweight Friendship-like objects for view tests."""

    return [
        Mock(
            from_user_id=target.pk,
            from_user=target,
            to_user=index,
        )
        for index in range(count)
    ]


@pytest.mark.django_db
class TestProfileExploreFriendsView:
    def test_view_uses_profile_access_and_friendship_service(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Friends endpoint should reuse profile access and friendship domain logic."""

        request = request_factory.get("/")
        request.user = stranger

        relation = {
            "is_self": False,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": False,
            "can_send_request": True,
        }

        friendship_relations = make_friendships(
            target=owner,
            count=10,
        )

        target_mock = Mock(return_value=owner)
        relation_mock = Mock(return_value=relation)
        friends_mock = Mock(return_value=friendship_relations)

        access_service = Mock()
        access_service.can_view_profile.return_value = True
        access_service.can_view_friends.return_value = True

        access_class_mock = Mock(return_value=access_service)
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_profile_target",
            target_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.FriendshipService.get_relation",
            relation_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.ProfileAccessService",
            access_class_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_friends",
            friends_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExploreFriendsView.as_view()(
            request,
            pk=owner.pk,
        )

        assert response.status_code == 200

        target_mock.assert_called_once_with(owner.pk)

        relation_mock.assert_called_once_with(
            stranger,
            owner,
        )

        access_class_mock.assert_called_once_with(
            viewer=stranger,
            target=owner,
            is_friend=False,
        )

        friends_mock.assert_called_once_with(owner)

    def test_missing_target_returns_404(
        self,
        request_factory,
        stranger,
        monkeypatch,
    ):
        """Friends endpoint should propagate 404 for an unknown profile."""

        request = request_factory.get("/")
        request.user = stranger

        target_mock = Mock(
            side_effect=Http404,
        )

        monkeypatch.setattr(
            "users.views.profile_explore.get_profile_target",
            target_mock,
        )

        with pytest.raises(Http404):
            ProfileExploreFriendsView.as_view()(
                request,
                pk=999999999,
            )

    def test_denied_friends_access_does_not_load_friends(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Closed friends list should render without loading friend data."""

        request = request_factory.get("/")
        request.user = stranger

        relation = {
            "is_self": False,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": False,
            "can_send_request": True,
        }

        access_service = Mock()
        access_service.can_view_profile.return_value = True
        access_service.can_view_friends.return_value = False

        friends_mock = Mock(side_effect=AssertionError("Friends must not be loaded when friends access is denied."))

        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_profile_target",
            Mock(return_value=owner),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.FriendshipService.get_relation",
            Mock(return_value=relation),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.ProfileAccessService",
            Mock(return_value=access_service),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_friends",
            friends_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExploreFriendsView.as_view()(
            request,
            pk=owner.pk,
        )

        assert response.status_code == 200

        friends_mock.assert_not_called()

        context = render_mock.call_args.args[2]

        assert context["can_view_friends"] is False
        assert context["friends"] == []

    def test_first_page_contains_configured_friends_count(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Explore should paginate large friend collections."""

        request = request_factory.get("/?page=1")
        request.user = stranger

        relation = {
            "is_self": False,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": False,
            "can_send_request": True,
        }

        access_service = Mock()
        access_service.can_view_profile.return_value = True
        access_service.can_view_friends.return_value = True

        friendship_relations = make_friendships(
            target=owner,
            count=500,
        )
        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_profile_target",
            Mock(return_value=owner),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.FriendshipService.get_relation",
            Mock(return_value=relation),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.ProfileAccessService",
            Mock(return_value=access_service),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_friends",
            Mock(return_value=friendship_relations),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExploreFriendsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]
        page_size = settings.PROFILE_EXPLORE_FRIENDS_PER_PAGE

        assert len(context["friendships"]) == page_size
        assert context["page_obj"].number == 1
        assert context["page_obj"].has_next() is True
        assert context["paginator"].count == 500

    def test_second_page_contains_next_friendships(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Second request should return the next friendship page."""

        request = request_factory.get("/?page=2")
        request.user = stranger

        relation = {
            "is_self": False,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": False,
            "can_send_request": True,
        }

        access_service = Mock()
        access_service.can_view_profile.return_value = True
        access_service.can_view_friends.return_value = True

        friendship_relations = make_friendships(
            target=owner,
            count=500,
        )

        render_mock = Mock(return_value=HttpResponse(status=200))

        monkeypatch.setattr(
            "users.views.profile_explore.get_profile_target",
            Mock(return_value=owner),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.FriendshipService.get_relation",
            Mock(return_value=relation),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.ProfileAccessService",
            Mock(return_value=access_service),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_friends",
            Mock(return_value=friendship_relations),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExploreFriendsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]
        page_size = settings.PROFILE_EXPLORE_FRIENDS_PER_PAGE

        assert list(context["friendships"]) == friendship_relations[page_size : page_size * 2]
        assert context["page_obj"].number == 2

    def test_closed_profile_stops_before_loading_friends(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Closed profile should stop before friendship data is loaded."""

        request = request_factory.get("/")
        request.user = stranger

        relation = {
            "is_self": False,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": False,
            "can_send_request": True,
        }

        access_service = Mock()
        access_service.can_view_profile.return_value = False
        access_service.can_view_friends.return_value = False

        friends_mock = Mock(side_effect=AssertionError("Friends must not be loaded when profile access is denied."))

        monkeypatch.setattr(
            "users.views.profile_explore.get_profile_target",
            Mock(return_value=owner),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.FriendshipService.get_relation",
            Mock(return_value=relation),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.ProfileAccessService",
            Mock(return_value=access_service),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.get_friends",
            friends_mock,
        )

        with pytest.raises(Http404):
            ProfileExploreFriendsView.as_view()(
                request,
                pk=owner.pk,
            )

        friends_mock.assert_not_called()
