# src/users/tests/profile/test_profile_explore_mutual_friends_view.py

"""Tests for the Mutual Friends section of Profile Explore."""

from unittest.mock import Mock

import pytest
from django.conf import settings
from django.http import Http404, HttpResponse
from django.test import RequestFactory

from users.views.profile_explore import ProfileExploreMutualFriendsView


@pytest.fixture
def request_factory():
    """Return a request factory."""

    return RequestFactory()


@pytest.mark.django_db
class TestProfileExploreMutualFriendsView:
    """Test the Mutual Friends Explore endpoint."""

    def test_view_uses_profile_access_and_friendship_service(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Endpoint should reuse profile access and friendship domain logic."""

        request = request_factory.get("/")
        request.user = stranger

        relation = {
            "is_self": False,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": False,
            "can_send_request": True,
        }

        mutual_friends = list(range(10))

        target_mock = Mock(return_value=owner)
        relation_mock = Mock(return_value=relation)
        mutual_mock = Mock(return_value=mutual_friends)

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
            "users.views.profile_explore.get_mutual_friends",
            mutual_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExploreMutualFriendsView.as_view()(
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
        mutual_mock.assert_called_once_with(
            stranger,
            owner,
        )

    def test_missing_target_returns_404(
        self,
        request_factory,
        stranger,
        monkeypatch,
    ):
        """Unknown profile should return 404."""

        request = request_factory.get("/")
        request.user = stranger

        target_mock = Mock(side_effect=Http404)

        monkeypatch.setattr(
            "users.views.profile_explore.get_profile_target",
            target_mock,
        )

        with pytest.raises(Http404):
            ProfileExploreMutualFriendsView.as_view()(
                request,
                pk=999999,
            )

    def test_denied_friends_access_does_not_leak_mutual_friends(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Hidden friends should prevent mutual friend loading."""

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

        mutual_mock = Mock()
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
            "users.views.profile_explore.get_mutual_friends",
            mutual_mock,
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        response = ProfileExploreMutualFriendsView.as_view()(
            request,
            pk=owner.pk,
        )

        assert response.status_code == 200
        mutual_mock.assert_not_called()

        context = render_mock.call_args.args[2]

        assert context["can_view_mutual_friends"] is False
        assert context["mutual_friends"] == []

    def test_first_page_contains_configured_count(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Mutual friends should use configured pagination."""

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

        mutual_friends = list(range(500))
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
            "users.views.profile_explore.get_mutual_friends",
            Mock(return_value=mutual_friends),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExploreMutualFriendsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]
        page_size = settings.PROFILE_EXPLORE_FRIENDS_PER_PAGE

        assert len(context["mutual_friends"]) == page_size
        assert context["page_obj"].number == 1

    def test_second_page_contains_next_mutual_friends(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Second request should return the next mutual friends page."""

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

        mutual_friends = list(range(500))
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
            "users.views.profile_explore.get_mutual_friends",
            Mock(return_value=mutual_friends),
        )
        monkeypatch.setattr(
            "users.views.profile_explore.render",
            render_mock,
        )

        ProfileExploreMutualFriendsView.as_view()(
            request,
            pk=owner.pk,
        )

        context = render_mock.call_args.args[2]
        page_size = settings.PROFILE_EXPLORE_FRIENDS_PER_PAGE

        assert list(context["mutual_friends"]) == mutual_friends[page_size : page_size * 2]
        assert context["page_obj"].number == 2

    def test_closed_profile_stops_before_loading_mutual_friends(
        self,
        request_factory,
        owner,
        stranger,
        monkeypatch,
    ):
        """Closed profile should return 404 before loading mutual friends."""

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

        mutual_mock = Mock()

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
            "users.views.profile_explore.get_mutual_friends",
            mutual_mock,
        )

        with pytest.raises(Http404):
            ProfileExploreMutualFriendsView.as_view()(
                request,
                pk=owner.pk,
            )

        mutual_mock.assert_not_called()
