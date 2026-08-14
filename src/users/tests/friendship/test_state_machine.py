# src/users/tests/friendship/test_state_machine.py
"""End-to-end tests for friendship state transitions."""

import pytest

from users.models.friendship import Friendship
from users.services.friendship_service import FriendshipService


@pytest.mark.django_db
class TestFriendshipStateMachine:
    def test_send_accept_remove_cycle(self, user_a, user_b):
        initial = FriendshipService.get_relation(
            user_a,
            user_b,
        )

        assert initial["can_send_request"] is True

        request = FriendshipService.send_request(
            user_a,
            user_b,
        )

        assert request.status == Friendship.Status.PENDING

        sender_state = FriendshipService.get_relation(
            user_a,
            user_b,
        )
        recipient_state = FriendshipService.get_relation(
            user_b,
            user_a,
        )

        assert sender_state["outgoing_request"] is True
        assert recipient_state["incoming_request"] is True

        FriendshipService.accept_request(
            user_b,
            user_a,
        )

        assert FriendshipService.get_relation(
            user_a,
            user_b,
        )["is_friend"]

        assert FriendshipService.get_relation(
            user_b,
            user_a,
        )["is_friend"]

        FriendshipService.remove_friend(
            user_a,
            user_b,
        )

        final_a = FriendshipService.get_relation(
            user_a,
            user_b,
        )
        final_b = FriendshipService.get_relation(
            user_b,
            user_a,
        )

        assert final_a["can_send_request"] is True
        assert final_b["can_send_request"] is True
        assert not final_a["is_friend"]

    def test_send_decline_cycle(self, user_a, user_b):
        FriendshipService.send_request(
            user_a,
            user_b,
        )

        FriendshipService.decline_request(
            user_b,
            user_a,
        )

        assert not Friendship.objects.filter(
            from_user=user_a,
            to_user=user_b,
        ).exists()

        assert FriendshipService.get_relation(
            user_a,
            user_b,
        )["can_send_request"]

    def test_send_cancel_cycle(self, user_a, user_b):
        FriendshipService.send_request(
            user_a,
            user_b,
        )

        FriendshipService.cancel_request(
            user_a,
            user_b,
        )

        assert not Friendship.objects.filter(
            from_user=user_a,
            to_user=user_b,
        ).exists()

        assert FriendshipService.get_relation(
            user_a,
            user_b,
        )["can_send_request"]
