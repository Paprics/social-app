# src/users/services/friendship_service.py
"""Business logic and state transitions for user friendships."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from users.models.friendship import Friendship
from users.selectors import friendship as friendship_selectors
from users.services.friendship_errors import (
    AlreadyFriendsError,
    FriendRequestAlreadyExistsError,
    FriendRequestNotFoundError,
    FriendshipAuthenticationError,
    FriendshipBlockedError,
    FriendshipNotFoundError,
    IncomingFriendRequestExistsError,
    InvalidFriendshipStateError,
    SelfFriendshipError,
)
from users.selectors.user_block import is_blocked_between

User = get_user_model()


class FriendshipService:
    """Manage friendship state and friendship-changing operations."""

    @staticmethod
    def _between(user1, user2):
        """Return friendship records between two users in either direction."""

        return Friendship.objects.filter(Q(from_user=user1, to_user=user2) | Q(from_user=user2, to_user=user1))

    @staticmethod
    def _relation_state(
        *,
        is_self=False,
        is_friend=False,
        outgoing_request=False,
        incoming_request=False,
        can_send_request=False,
    ):
        """Build normalized friendship state for UI and access rules."""

        return {
            "is_self": is_self,
            "is_friend": is_friend,
            "outgoing_request": outgoing_request,
            "incoming_request": incoming_request,
            "can_send_request": can_send_request,
        }

    @staticmethod
    def _validate_actor(actor):
        """Require an authenticated actor for friendship mutations."""

        if not getattr(actor, "is_authenticated", False):
            raise FriendshipAuthenticationError("Authentication is required.")

    @staticmethod
    def _validate_distinct_users(user1, user2):
        """Reject friendship operations involving the same user."""

        if user1 == user2:
            raise SelfFriendshipError("A user cannot have a friendship relation with themselves.")

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

    @staticmethod
    def _validate_not_blocked(user1, user2):
        """Reject interactions when either user has blocked the other."""

        if is_blocked_between(
            user1,
            user2,
        ):
            raise FriendshipBlockedError("Friendship actions are unavailable between blocked users.")

    # ------------------------------------------------------------------
    # Relationship state
    # ------------------------------------------------------------------

    @classmethod
    def get_relation(cls, user1, user2):
        """Return normalized friendship state relative to user1."""

        if user1 == user2:
            return cls._relation_state(
                is_self=True,
            )

        if not getattr(user1, "is_authenticated", False):
            return cls._relation_state()

        if not getattr(user2, "is_authenticated", False):
            return cls._relation_state()

        if is_blocked_between(
            user1,
            user2,
        ):
            return cls._relation_state()

        friendship = friendship_selectors.get_relation_record(
            user1,
            user2,
        )

        if friendship is None:
            return cls._relation_state(
                can_send_request=True,
            )

        if friendship.status == Friendship.Status.ACCEPTED:
            return cls._relation_state(
                is_friend=True,
            )

        if friendship.status == Friendship.Status.PENDING:
            if friendship.from_user_id == user1.pk:
                return cls._relation_state(
                    outgoing_request=True,
                )

            return cls._relation_state(
                incoming_request=True,
            )

        return cls._relation_state()

    @classmethod
    def are_friends(cls, user1, user2):
        """Return whether two users have an accepted friendship."""

        if user1 == user2:
            return False

        if not getattr(user1, "is_authenticated", False):
            return False

        if not getattr(user2, "is_authenticated", False):
            return False

        if is_blocked_between(
            user1,
            user2,
        ):
            return False

        friendship = friendship_selectors.get_relation_record(
            user1,
            user2,
        )

        return bool(friendship and friendship.status == Friendship.Status.ACCEPTED)

    @classmethod
    def has_pending_request(cls, user1, user2):
        """Return whether a pending request exists in either direction."""

        if user1 == user2:
            return False

        if not getattr(user1, "is_authenticated", False):
            return False

        if not getattr(user2, "is_authenticated", False):
            return False

        friendship = friendship_selectors.get_relation_record(
            user1,
            user2,
        )

        return bool(friendship and friendship.status == Friendship.Status.PENDING)

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def send_request(cls, actor, target):
        """Create a pending friend request from actor to target."""

        cls._validate_actor(actor)
        cls._validate_distinct_users(
            actor,
            target,
        )

        cls._lock_pair(
            actor,
            target,
        )

        cls._validate_not_blocked(
            actor,
            target,
        )

        relation = (
            cls._between(
                actor,
                target,
            )
            .select_for_update()
            .first()
        )

        if relation is not None:
            if relation.status == Friendship.Status.ACCEPTED:
                raise AlreadyFriendsError("Users are already friends.")

            if relation.status == Friendship.Status.PENDING:
                if relation.from_user_id == actor.pk:
                    raise FriendRequestAlreadyExistsError("Friend request has already been sent.")

                raise IncomingFriendRequestExistsError("Incoming friend request already exists.")

            raise InvalidFriendshipStateError("Friendship relation has an unsupported state.")

        return Friendship.objects.create(
            from_user=actor,
            to_user=target,
            status=Friendship.Status.PENDING,
        )

    @classmethod
    @transaction.atomic
    def cancel_request(cls, actor, target):
        """Cancel actor's outgoing pending friend request."""

        cls._validate_actor(actor)
        cls._validate_distinct_users(
            actor,
            target,
        )

        cls._lock_pair(
            actor,
            target,
        )

        friendship = (
            Friendship.objects.select_for_update()
            .filter(
                from_user=actor,
                to_user=target,
                status=Friendship.Status.PENDING,
            )
            .first()
        )

        if friendship is None:
            raise FriendRequestNotFoundError("Outgoing friend request was not found.")

        friendship.delete()

    @classmethod
    @transaction.atomic
    def accept_request(cls, actor, target):
        """
        Accept an incoming friend request.

        Expected pending direction:
            target -> actor
        """

        cls._validate_actor(actor)
        cls._validate_distinct_users(
            actor,
            target,
        )

        cls._lock_pair(
            actor,
            target,
        )

        cls._validate_not_blocked(
            actor,
            target,
        )

        friendship = (
            Friendship.objects.select_for_update()
            .filter(
                from_user=target,
                to_user=actor,
                status=Friendship.Status.PENDING,
            )
            .first()
        )

        if friendship is None:
            raise FriendRequestNotFoundError("Incoming friend request was not found.")

        friendship.status = Friendship.Status.ACCEPTED
        friendship.accepted_at = timezone.now()

        friendship.save(
            update_fields=[
                "status",
                "accepted_at",
                "updated_at",
            ]
        )

        return friendship

    @classmethod
    @transaction.atomic
    def decline_request(cls, actor, target):
        """
        Decline an incoming friend request.

        Expected pending direction:
            target -> actor
        """

        cls._validate_actor(actor)
        cls._validate_distinct_users(
            actor,
            target,
        )

        cls._lock_pair(
            actor,
            target,
        )

        friendship = (
            Friendship.objects.select_for_update()
            .filter(
                from_user=target,
                to_user=actor,
                status=Friendship.Status.PENDING,
            )
            .first()
        )

        if friendship is None:
            raise FriendRequestNotFoundError("Incoming friend request was not found.")

        friendship.delete()

    @classmethod
    @transaction.atomic
    def remove_friend(cls, actor, target):
        """Remove an accepted friendship regardless of stored direction."""

        cls._validate_actor(actor)
        cls._validate_distinct_users(
            actor,
            target,
        )

        cls._lock_pair(
            actor,
            target,
        )

        friendship = (
            cls._between(
                actor,
                target,
            )
            .select_for_update()
            .filter(
                status=Friendship.Status.ACCEPTED,
            )
            .first()
        )

        if friendship is None:
            raise FriendshipNotFoundError("Accepted friendship was not found.")

        friendship.delete()
