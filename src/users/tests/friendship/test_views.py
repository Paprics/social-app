# src/users/tests/friendship/test_views.py
"""Integration tests for friendship HTTP action endpoints."""

import pytest
from django.urls import reverse

from users.models.friendship import Friendship


@pytest.mark.django_db
class TestFriendshipAuthentication:
    @pytest.mark.parametrize(
        "url_name",
        [
            "users:friend_request_send",
            "users:friend_request_cancel",
            "users:friend_request_accept",
            "users:friend_request_decline",
            "users:friend_remove",
        ],
    )
    def test_actions_require_authentication(
        self,
        client,
        user_b,
        url_name,
    ):
        response = client.post(
            reverse(
                url_name,
                kwargs={"pk": user_b.pk},
            )
        )

        assert response.status_code == 302


@pytest.mark.django_db
class TestFriendRequestSendView:
    def test_send_creates_request(self, client, user_a, user_b):
        client.force_login(user_a)

        response = client.post(
            reverse(
                "users:friend_request_send",
                kwargs={"pk": user_b.pk},
            )
        )

        assert response.status_code == 200

        assert Friendship.objects.filter(
            from_user=user_a,
            to_user=user_b,
            status=Friendship.Status.PENDING,
        ).exists()

    def test_duplicate_send_does_not_return_500(
        self,
        client,
        user_a,
        user_b,
    ):
        client.force_login(user_a)

        url = reverse(
            "users:friend_request_send",
            kwargs={"pk": user_b.pk},
        )

        client.post(url)
        response = client.post(url)

        assert response.status_code == 200
        assert Friendship.objects.count() == 1

    def test_get_is_not_allowed(self, client, user_a, user_b):
        client.force_login(user_a)

        response = client.get(
            reverse(
                "users:friend_request_send",
                kwargs={"pk": user_b.pk},
            )
        )

        assert response.status_code == 405


@pytest.mark.django_db
class TestFriendRequestLifecycleViews:
    def test_sender_can_cancel(
        self,
        client,
        user_a,
        user_b,
        pending_friend_request,
    ):
        client.force_login(user_a)

        response = client.post(
            reverse(
                "users:friend_request_cancel",
                kwargs={"pk": user_b.pk},
            )
        )

        assert response.status_code == 200
        assert not Friendship.objects.filter(
            pk=pending_friend_request.pk,
        ).exists()

    def test_recipient_can_accept(
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
        )

        assert response.status_code == 200

        pending_friend_request.refresh_from_db()

        assert pending_friend_request.status == Friendship.Status.ACCEPTED
        assert pending_friend_request.accepted_at is not None

    def test_recipient_can_decline(
        self,
        client,
        user_a,
        user_b,
        pending_friend_request,
    ):
        client.force_login(user_b)

        response = client.post(
            reverse(
                "users:friend_request_decline",
                kwargs={"pk": user_a.pk},
            )
        )

        assert response.status_code == 200
        assert not Friendship.objects.filter(
            pk=pending_friend_request.pk,
        ).exists()

    def test_friendship_can_be_removed(
        self,
        client,
        user_a,
        user_b,
        accepted_friendship,
    ):
        client.force_login(user_a)

        response = client.post(
            reverse(
                "users:friend_remove",
                kwargs={"pk": user_b.pk},
            )
        )

        assert response.status_code == 200
        assert not Friendship.objects.filter(
            pk=accepted_friendship.pk,
        ).exists()


@pytest.mark.django_db
class TestAccountCenterFriendshipResponses:

    def test_successful_account_center_action_triggers_refresh(
        self,
        client,
        user_a,
        user_b,
    ):
        client.force_login(user_a)

        response = client.post(
            reverse(
                "users:friend_request_send",
                kwargs={"pk": user_b.pk},
            )
            + "?context=account_center"
        )

        assert response.status_code == 200
        assert response.headers["HX-Trigger"] == "friendshipChanged"

        assert Friendship.objects.filter(
            from_user=user_a,
            to_user=user_b,
            status=Friendship.Status.PENDING,
        ).exists()

    def test_stale_account_center_action_keeps_row(
        self,
        client,
        user_a,
        user_b,
    ):
        client.force_login(user_a)

        response = client.post(
            reverse(
                "users:friend_request_cancel",
                kwargs={"pk": user_b.pk},
            )
            + "?context=account_center"
        )

        assert response.status_code == 204

    def test_missing_target_returns_404(self, client, user_a):
        client.force_login(user_a)

        response = client.post(
            reverse(
                "users:friend_request_send",
                kwargs={"pk": 999999999},
            )
        )

        assert response.status_code == 404
