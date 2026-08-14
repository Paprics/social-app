# src/users/services/user_block.py
"""Business logic for blocking and unblocking users."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from users.models.friendship import Friendship
from users.models.user_block import UserBlock

User = get_user_model()


class UserBlockService:
    """Manage block-changing operations."""

    @staticmethod
    def _lock_pair(user1, user2):
        """Lock both users in deterministic primary-key order."""

        list(
            User.objects.select_for_update()
            .filter(
                pk__in=[
                    user1.pk,
                    user2.pk,
                ]
            )
            .order_by("pk")
            .values_list(
                "pk",
                flat=True,
            )
        )

    @classmethod
    @transaction.atomic
    def block(cls, user, target):
        """
        Block target and remove any friendship relation between the users.

        Both pending requests and accepted friendships are removed.
        """

        if user == target:
            raise ValueError("A user cannot block themselves.")

        cls._lock_pair(
            user,
            target,
        )

        block, created = UserBlock.objects.get_or_create(
            blocker=user,
            blocked=target,
        )

        Friendship.objects.filter(
            Q(from_user=user, to_user=target)
            | Q(from_user=target, to_user=user)
        ).delete()

        return block, created

    @staticmethod
    def unblock(user, target):
        """Remove the blocking relation created by user."""

        deleted_count, _ = UserBlock.objects.filter(
            blocker=user,
            blocked=target,
        ).delete()

        return deleted_count > 0
