# src/users/tests/friendship/test_account_center.py
"""Integration tests for friendship lists and actions in Account Center."""

import pytest
from django.urls import reverse

from users.models.friendship import Friendship
from users.services.friendship_service import FriendshipService


@pytest.mark.django_db
class TestAccountCenterFriendLists:
    def test_friends_page_contains_accepted_friendship(
        self,
        client,
        user_a,
        user_b,
        accepted_friendship,
    ):
        client.force_login(user_a)

        response = client.get(reverse("users:account_center_friends_list"))

        assert response.status_code == 200
        assert accepted_friendship in response.context["friendships"]

    def test_pending_request_is_not_in_friends(
        self,
        client,
        user_a,
        pending_friend_request,
    ):
        client.force_login(user_a)

        response = client.get(reverse("users:account_center_friends_list"))

        assert pending_friend_request not in response.context["friendships"]

    def test_incoming_page_contains_received_request(
        self,
        client,
        user_a,
        user_b,
    ):
        request = Friendship.objects.create(
            from_user=user_b,
            to_user=user_a,
        )

        client.force_login(user_a)

        response = client.get(reverse("users:account_center_friends_incoming"))

        assert request in response.context["friend_requests"]

    def test_outgoing_page_contains_sent_request(
        self,
        client,
        user_a,
        user_b,
    ):
        request = Friendship.objects.create(
            from_user=user_a,
            to_user=user_b,
        )

        client.force_login(user_a)

        response = client.get(reverse("users:account_center_friends_outgoing"))

        assert request in response.context["friend_requests"]


@pytest.mark.django_db
class TestAccountCenterFriendshipLifecycle:
    def test_accept_moves_request_from_incoming_to_friends(
        self,
        client,
        user_a,
        user_b,
        pending_friend_request,
    ):
        client.force_login(user_b)

        response = client.post(
            reverse(
                "users:friend_request_accept",
                kwargs={"pk": user_a.pk},
            )
            + "?context=account_center"
        )

        assert response.status_code == 200

        assert not FriendshipService.has_pending_request(
            user_a,
            user_b,
        )

        assert FriendshipService.are_friends(
            user_a,
            user_b,
        )

        incoming = client.get(reverse("users:account_center_friends_incoming"))

        assert pending_friend_request not in incoming.context["friend_requests"]

        friends = client.get(reverse("users:account_center_friends_list"))

        pending_friend_request.refresh_from_db()

        assert pending_friend_request in friends.context["friendships"]

    def test_decline_removes_incoming_request(
        self,
        client,
        user_a,
        user_b,
        pending_friend_request,
    ):
        client.force_login(user_b)

        client.post(
            reverse(
                "users:friend_request_decline",
                kwargs={"pk": user_a.pk},
            )
            + "?context=account_center"
        )

        assert not Friendship.objects.filter(
            pk=pending_friend_request.pk,
        ).exists()

    def test_cancel_removes_outgoing_request(
        self,
        client,
        user_a,
        user_b,
        pending_friend_request,
    ):
        client.force_login(user_a)

        client.post(
            reverse(
                "users:friend_request_cancel",
                kwargs={"pk": user_b.pk},
            )
            + "?context=account_center"
        )

        assert not Friendship.objects.filter(
            pk=pending_friend_request.pk,
        ).exists()

    def test_remove_removes_friend_from_account_center(
        self,
        client,
        user_a,
        user_b,
        accepted_friendship,
    ):
        client.force_login(user_a)

        client.post(
            reverse(
                "users:friend_remove",
                kwargs={"pk": user_b.pk},
            )
            + "?context=account_center"
        )

        assert not Friendship.objects.filter(
            pk=accepted_friendship.pk,
        ).exists()
