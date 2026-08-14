# src/users/tests/friendship/test_relation.py
"""Tests for normalized friendship relationship state."""

import pytest
from django.contrib.auth.models import AnonymousUser

from users.models.friendship import Friendship
from users.models.user_block import UserBlock
from users.services.friendship_service import FriendshipService


def empty_relation():
    return {
        "is_self": False,
        "is_friend": False,
        "outgoing_request": False,
        "incoming_request": False,
        "can_send_request": False,
    }


@pytest.mark.django_db
class TestFriendshipRelation:
    def test_self_relation(self, user_a):
        assert FriendshipService.get_relation(user_a, user_a) == {
            "is_self": True,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": False,
            "can_send_request": False,
        }

    def test_anonymous_relation_is_closed(self, user_a):
        relation = FriendshipService.get_relation(
            AnonymousUser(),
            user_a,
        )

        assert relation == empty_relation()

    def test_users_without_relation_can_send_request(self, user_a, user_b):
        relation = FriendshipService.get_relation(
            user_a,
            user_b,
        )

        assert relation == {
            "is_self": False,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": False,
            "can_send_request": True,
        }

    def test_outgoing_pending_request(self, user_a, user_b):
        Friendship.objects.create(
            from_user=user_a,
            to_user=user_b,
        )

        relation = FriendshipService.get_relation(
            user_a,
            user_b,
        )

        assert relation["outgoing_request"] is True
        assert relation["incoming_request"] is False
        assert relation["can_send_request"] is False

    def test_incoming_pending_request(self, user_a, user_b):
        Friendship.objects.create(
            from_user=user_b,
            to_user=user_a,
        )

        relation = FriendshipService.get_relation(
            user_a,
            user_b,
        )

        assert relation["incoming_request"] is True
        assert relation["outgoing_request"] is False
        assert relation["can_send_request"] is False

    def test_accepted_relation_is_friend(self, accepted_friendship, user_a, user_b):
        relation = FriendshipService.get_relation(
            user_a,
            user_b,
        )

        assert relation["is_friend"] is True
        assert relation["can_send_request"] is False

    def test_accepted_relation_is_symmetric(self, accepted_friendship, user_a, user_b):
        assert FriendshipService.get_relation(
            user_a,
            user_b,
        )["is_friend"]

        assert FriendshipService.get_relation(
            user_b,
            user_a,
        )["is_friend"]

    def test_blocked_relation_is_closed(self, user_a, user_b):
        UserBlock.objects.create(
            blocker=user_a,
            blocked=user_b,
        )

        assert (
            FriendshipService.get_relation(
                user_a,
                user_b,
            )
            == empty_relation()
        )

        assert (
            FriendshipService.get_relation(
                user_b,
                user_a,
            )
            == empty_relation()
        )


@pytest.mark.django_db
class TestFriendshipFacts:
    def test_are_friends_for_accepted_relation(
        self,
        accepted_friendship,
        user_a,
        user_b,
    ):
        assert FriendshipService.are_friends(user_a, user_b)
        assert FriendshipService.are_friends(user_b, user_a)

    def test_pending_request_is_not_friendship(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        assert not FriendshipService.are_friends(user_a, user_b)

    def test_pending_request_is_detected_in_both_directions(
        self,
        pending_friend_request,
        user_a,
        user_b,
    ):
        assert FriendshipService.has_pending_request(user_a, user_b)
        assert FriendshipService.has_pending_request(user_b, user_a)

    def test_self_is_neither_friend_nor_pending(self, user_a):
        assert not FriendshipService.are_friends(user_a, user_a)
        assert not FriendshipService.has_pending_request(user_a, user_a)
