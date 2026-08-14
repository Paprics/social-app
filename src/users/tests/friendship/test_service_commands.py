# src/users/tests/friendship/test_service_commands.py
"""Tests for friendship state-changing service operations."""

import pytest
from django.contrib.auth.models import AnonymousUser

from users.models.friendship import Friendship
from users.models.user_block import UserBlock
from users.services.friendship_errors import (
    AlreadyFriendsError,
    FriendRequestAlreadyExistsError,
    FriendRequestNotFoundError,
    FriendshipAuthenticationError,
    FriendshipBlockedError,
    FriendshipNotFoundError,
    IncomingFriendRequestExistsError,
    SelfFriendshipError,
)
from users.services.friendship_service import FriendshipService


@pytest.mark.django_db
class TestSendFriendRequest:
    def test_send_request_creates_pending_relation(self, user_a, user_b):
        friendship = FriendshipService.send_request(
            user_a,
            user_b,
        )

        assert friendship.from_user == user_a
        assert friendship.to_user == user_b
        assert friendship.status == Friendship.Status.PENDING
        assert friendship.accepted_at is None

    def test_anonymous_cannot_send_request(self, user_a):
        with pytest.raises(FriendshipAuthenticationError):
            FriendshipService.send_request(
                AnonymousUser(),
                user_a,
            )

    def test_user_cannot_send_request_to_self(self, user_a):
        with pytest.raises(SelfFriendshipError):
            FriendshipService.send_request(
                user_a,
                user_a,
            )

    def test_duplicate_outgoing_request_is_rejected(self, user_a, user_b):
        FriendshipService.send_request(user_a, user_b)

        with pytest.raises(FriendRequestAlreadyExistsError):
            FriendshipService.send_request(user_a, user_b)

    def test_existing_incoming_request_is_rejected(self, user_a, user_b):
        FriendshipService.send_request(user_b, user_a)

        with pytest.raises(IncomingFriendRequestExistsError):
            FriendshipService.send_request(user_a, user_b)

    def test_existing_friendship_rejects_new_request(
        self,
        accepted_friendship,
        user_a,
        user_b,
    ):
        with pytest.raises(AlreadyFriendsError):
            FriendshipService.send_request(user_a, user_b)

    def test_blocked_users_cannot_send_request(self, user_a, user_b):
        UserBlock.objects.create(
            blocker=user_a,
            blocked=user_b,
        )

        with pytest.raises(FriendshipBlockedError):
            FriendshipService.send_request(user_a, user_b)

    def test_blocking_in_reverse_direction_also_prevents_request(
        self,
        user_a,
        user_b,
    ):
        UserBlock.objects.create(
            blocker=user_b,
            blocked=user_a,
        )

        with pytest.raises(FriendshipBlockedError):
            FriendshipService.send_request(user_a, user_b)


@pytest.mark.django_db
class TestCancelFriendRequest:
    def test_sender_can_cancel_request(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        FriendshipService.cancel_request(
            user_a,
            user_b,
        )

        assert not Friendship.objects.filter(
            pk=pending_friend_request.pk,
        ).exists()

    def test_recipient_cannot_cancel_incoming_request(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        with pytest.raises(FriendRequestNotFoundError):
            FriendshipService.cancel_request(
                user_b,
                user_a,
            )

    def test_missing_request_cannot_be_cancelled(self, user_a, user_b):
        with pytest.raises(FriendRequestNotFoundError):
            FriendshipService.cancel_request(
                user_a,
                user_b,
            )


@pytest.mark.django_db
class TestAcceptFriendRequest:
    def test_recipient_can_accept_request(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        friendship = FriendshipService.accept_request(
            user_b,
            user_a,
        )

        friendship.refresh_from_db()

        assert friendship.status == Friendship.Status.ACCEPTED
        assert friendship.accepted_at is not None

    def test_sender_cannot_accept_own_request(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        with pytest.raises(FriendRequestNotFoundError):
            FriendshipService.accept_request(
                user_a,
                user_b,
            )

    def test_missing_request_cannot_be_accepted(self, user_a, user_b):
        with pytest.raises(FriendRequestNotFoundError):
            FriendshipService.accept_request(
                user_b,
                user_a,
            )

    def test_blocked_request_cannot_be_accepted(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        UserBlock.objects.create(
            blocker=user_a,
            blocked=user_b,
        )

        with pytest.raises(FriendshipBlockedError):
            FriendshipService.accept_request(
                user_b,
                user_a,
            )


@pytest.mark.django_db
class TestDeclineFriendRequest:
    def test_recipient_can_decline_request(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        FriendshipService.decline_request(
            user_b,
            user_a,
        )

        assert not Friendship.objects.filter(
            pk=pending_friend_request.pk,
        ).exists()

    def test_sender_cannot_decline_own_request(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        with pytest.raises(FriendRequestNotFoundError):
            FriendshipService.decline_request(
                user_a,
                user_b,
            )


@pytest.mark.django_db
class TestRemoveFriend:
    def test_first_user_can_remove_friendship(
        self,
        accepted_friendship,
        user_a,
        user_b,
    ):
        FriendshipService.remove_friend(
            user_a,
            user_b,
        )

        assert not Friendship.objects.filter(
            pk=accepted_friendship.pk,
        ).exists()

    def test_second_user_can_remove_friendship(
        self,
        accepted_friendship,
        user_a,
        user_b,
    ):
        FriendshipService.remove_friend(
            user_b,
            user_a,
        )

        assert not Friendship.objects.filter(
            pk=accepted_friendship.pk,
        ).exists()

    def test_pending_request_is_not_removable_as_friendship(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        with pytest.raises(FriendshipNotFoundError):
            FriendshipService.remove_friend(
                user_a,
                user_b,
            )

    def test_missing_friendship_cannot_be_removed(self, user_a, user_b):
        with pytest.raises(FriendshipNotFoundError):
            FriendshipService.remove_friend(
                user_a,
                user_b,
            )
