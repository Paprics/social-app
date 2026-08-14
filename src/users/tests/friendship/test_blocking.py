# src/users/tests/friendship/test_blocking.py
"""Tests for interaction between blocking and friendship relations."""

import pytest

from users.models.friendship import Friendship
from users.models.user_block import UserBlock
from users.services.friendship_errors import FriendshipBlockedError
from users.services.friendship_service import FriendshipService
from users.services.user_block import UserBlockService


@pytest.mark.django_db
class TestFriendshipBlocking:
    def test_block_creates_block_relation(self, user_a, user_b):
        block, created = UserBlockService.block(
            user_a,
            user_b,
        )

        assert created is True
        assert block.blocker == user_a
        assert block.blocked == user_b

    def test_block_removes_outgoing_pending_request(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        UserBlockService.block(
            user_a,
            user_b,
        )

        assert not Friendship.objects.filter(
            pk=pending_friend_request.pk,
        ).exists()

    def test_block_removes_incoming_pending_request(
        self,
        user_a,
        user_b,
    ):
        request = Friendship.objects.create(
            from_user=user_b,
            to_user=user_a,
        )

        UserBlockService.block(
            user_a,
            user_b,
        )

        assert not Friendship.objects.filter(
            pk=request.pk,
        ).exists()

    def test_block_removes_existing_friendship(
        self,
        accepted_friendship,
        user_a,
        user_b,
    ):
        UserBlockService.block(
            user_a,
            user_b,
        )

        assert not Friendship.objects.filter(
            pk=accepted_friendship.pk,
        ).exists()

    def test_block_is_idempotent(self, user_a, user_b):
        first_block, first_created = UserBlockService.block(
            user_a,
            user_b,
        )

        second_block, second_created = UserBlockService.block(
            user_a,
            user_b,
        )

        assert first_created is True
        assert second_created is False
        assert first_block.pk == second_block.pk

    def test_blocked_users_cannot_send_request(self, user_a, user_b):
        UserBlockService.block(
            user_a,
            user_b,
        )

        with pytest.raises(FriendshipBlockedError):
            FriendshipService.send_request(
                user_a,
                user_b,
            )

    def test_block_works_in_both_access_directions(self, user_a, user_b):
        UserBlockService.block(
            user_a,
            user_b,
        )

        with pytest.raises(FriendshipBlockedError):
            FriendshipService.send_request(
                user_b,
                user_a,
            )

    def test_unblock_removes_block(self, user_a, user_b):
        UserBlockService.block(
            user_a,
            user_b,
        )

        assert UserBlockService.unblock(
            user_a,
            user_b,
        )

        assert not UserBlock.objects.filter(
            blocker=user_a,
            blocked=user_b,
        ).exists()

    def test_unblock_does_not_restore_friendship(
        self,
        accepted_friendship,
        user_a,
        user_b,
    ):
        UserBlockService.block(
            user_a,
            user_b,
        )

        UserBlockService.unblock(
            user_a,
            user_b,
        )

        assert not FriendshipService.are_friends(
            user_a,
            user_b,
        )

    def test_after_unblock_new_request_can_be_sent(self, user_a, user_b):
        UserBlockService.block(
            user_a,
            user_b,
        )

        UserBlockService.unblock(
            user_a,
            user_b,
        )

        friendship = FriendshipService.send_request(
            user_a,
            user_b,
        )

        assert friendship.status == Friendship.Status.PENDING

    def test_user_cannot_block_self(self, user_a):
        with pytest.raises(ValueError):
            UserBlockService.block(
                user_a,
                user_a,
            )
