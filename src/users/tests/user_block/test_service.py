# src/users/tests/user_block/test_service.py
"""Tests for user blocking business logic."""

import pytest

from users.models.friendship import Friendship
from users.models.user_block import UserBlock
from users.services.friendship_errors import FriendshipBlockedError
from users.services.friendship_service import FriendshipService
from users.services.user_block import UserBlockService


@pytest.mark.django_db
def test_block_creates_relation_and_is_idempotent(user_a, user_b):
    block, created = UserBlockService.block(
        user_a,
        user_b,
    )

    assert created is True
    assert block.blocker_id == user_a.pk
    assert block.blocked_id == user_b.pk

    second_block, second_created = UserBlockService.block(
        user_a,
        user_b,
    )

    assert second_created is False
    assert second_block.pk == block.pk
    assert UserBlock.objects.count() == 1


@pytest.mark.django_db
def test_user_cannot_block_self(user_a):
    with pytest.raises(ValueError):
        UserBlockService.block(
            user_a,
            user_a,
        )


@pytest.mark.django_db
def test_block_removes_accepted_friendship(user_a, user_b):
    Friendship.objects.create(
        from_user=user_a,
        to_user=user_b,
        status=Friendship.Status.ACCEPTED,
    )

    UserBlockService.block(
        user_a,
        user_b,
    )

    assert not Friendship.objects.filter(
        from_user=user_a,
        to_user=user_b,
    ).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("reverse_direction", [False, True])
def test_block_removes_pending_request(
    user_a,
    user_b,
    reverse_direction,
):
    from_user = user_b if reverse_direction else user_a
    to_user = user_a if reverse_direction else user_b

    Friendship.objects.create(
        from_user=from_user,
        to_user=to_user,
        status=Friendship.Status.PENDING,
    )

    UserBlockService.block(
        user_a,
        user_b,
    )

    assert not Friendship.objects.filter(
        from_user=from_user,
        to_user=to_user,
    ).exists()


@pytest.mark.django_db
def test_block_prevents_new_friend_request(user_a, user_b):
    UserBlockService.block(
        user_a,
        user_b,
    )

    with pytest.raises(FriendshipBlockedError):
        FriendshipService.send_request(
            user_b,
            user_a,
        )


@pytest.mark.django_db
def test_unblock_does_not_restore_friendship_and_allows_new_request(
    user_a,
    user_b,
):
    Friendship.objects.create(
        from_user=user_a,
        to_user=user_b,
        status=Friendship.Status.ACCEPTED,
    )

    UserBlockService.block(
        user_a,
        user_b,
    )

    assert (
        UserBlockService.unblock(
            user_a,
            user_b,
        )
        is True
    )

    assert not Friendship.objects.filter(
        from_user=user_a,
        to_user=user_b,
    ).exists()

    request = FriendshipService.send_request(
        user_a,
        user_b,
    )

    assert request.status == Friendship.Status.PENDING
