# src/users/services/friendship_service.py

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.db.models.functions import Random

from users.models.friendship import Friendship

User = get_user_model()


class FriendshipService:
    """
    Service for friendship relations between users.

    Public API
    ----------

    Relationship:
        get_relation(user1, user2)
        are_friends(user1, user2)
        has_pending_request(user1, user2)

    Commands:
        send_request(actor, target)
        cancel_request(actor, target)
        accept_request(actor, target)
        decline_request(actor, target)
        remove_friend(actor, target)

    Lists:
        get_friends(user)
        get_incoming_requests(user)
        get_outgoing_requests(user)
        get_mutual_friends(user1, user2)

    Counts:
        get_friends_count(user)
        get_incoming_requests_count(user)
        get_outgoing_requests_count(user)
        get_mutual_friends_count(user1, user2)

    UI:
        get_friends_preview(user, limit=5)
    """

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _between(user1, user2):
        """
        Return friendship records between two users in either direction.

        Direction does not matter:

            user1 -> user2
            user2 -> user1
        """
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
        """
        Build normalized friendship state for UI and access services.

        Keeping construction in one place prevents different branches of
        get_relation() from returning dictionaries with different keys.
        """
        return {
            "is_self": is_self,
            "is_friend": is_friend,
            "outgoing_request": outgoing_request,
            "incoming_request": incoming_request,
            "can_send_request": can_send_request,
        }

    @staticmethod
    def _validate_actor(actor):
        """
        Require an authenticated user for friendship-changing operations.
        """
        if not getattr(actor, "is_authenticated", False):
            raise ValueError("Authentication is required.")

    @staticmethod
    def _validate_distinct_users(user1, user2):
        """
        Prevent friendship operations with the same user on both sides.
        """
        if user1 == user2:
            raise ValueError("A user cannot have a friendship relation with themselves.")

    @staticmethod
    def _lock_pair(user1, user2):
        """
        Lock both users for friendship-changing operations.

        Locks are always acquired in primary-key order. This prevents
        concurrent requests such as:

            user1 -> user2
            user2 -> user1

        from creating two separate friendship records.

        This is important because the model's unique constraint is
        directional and only protects an exact (from_user, to_user) pair.
        """
        list(
            User.objects.select_for_update()
            .filter(pk__in=[user1.pk, user2.pk])
            .order_by("pk")
            .values_list("pk", flat=True)
        )

    @classmethod
    def _friend_ids(cls, user):
        """
        Return IDs of all users who are accepted friends with user.
        """
        friendships = cls.get_friends(user).values_list(
            "from_user_id",
            "to_user_id",
        )

        return {to_user_id if from_user_id == user.pk else from_user_id for from_user_id, to_user_id in friendships}

    @classmethod
    def _mutual_friend_ids(cls, user1, user2):
        """
        Return IDs present in both users' accepted friend sets.
        """
        return cls._friend_ids(user1) & cls._friend_ids(user2)

    # -------------------------------------------------------------------------
    # Relationship
    # -------------------------------------------------------------------------

    @classmethod
    def get_relation(cls, user1, user2):
        """
        Return normalized friendship state between two users.

        Returns:
            dict: {
                "is_self": bool,
                "is_friend": bool,
                "outgoing_request": bool,
                "incoming_request": bool,
                "can_send_request": bool,
            }

        Direction is interpreted relative to user1.

        Examples:

            user1 sent request to user2:
                outgoing_request = True

            user2 sent request to user1:
                incoming_request = True
        """
        if user1 == user2:
            return cls._relation_state(
                is_self=True,
            )

        if not getattr(user1, "is_authenticated", False):
            return cls._relation_state()

        friendship = (
            cls._between(user1, user2)
            .only(
                "from_user_id",
                "status",
            )
            .first()
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

        # Defensive fallback in case new statuses are added later.
        return cls._relation_state()

    @classmethod
    def are_friends(cls, user1, user2) -> bool:
        """
        Return whether two users have an accepted friendship.

        This method is intended for access services and other business rules
        that only need a boolean friendship fact.
        """
        if user1 == user2:
            return False

        if not getattr(user1, "is_authenticated", False):
            return False

        if not getattr(user2, "is_authenticated", False):
            return False

        return (
            cls._between(
                user1,
                user2,
            )
            .filter(
                status=Friendship.Status.ACCEPTED,
            )
            .exists()
        )

    @classmethod
    def has_pending_request(cls, user1, user2) -> bool:
        """
        Return whether a pending friend request exists in either direction.
        """
        if user1 == user2:
            return False

        if not getattr(user1, "is_authenticated", False):
            return False

        if not getattr(user2, "is_authenticated", False):
            return False

        return (
            cls._between(
                user1,
                user2,
            )
            .filter(
                status=Friendship.Status.PENDING,
            )
            .exists()
        )

    # -------------------------------------------------------------------------
    # Commands
    # -------------------------------------------------------------------------

    @classmethod
    @transaction.atomic
    def send_request(cls, actor, target):
        """
        Send a friend request from actor to target.

        Raises:
            ValueError:
                If actor is not authenticated.
                If actor and target are the same user.
                If the users are already friends.
                If an outgoing request already exists.
                If an incoming request already exists.

        Returns:
            Friendship: Newly created pending friendship request.
        """
        cls._validate_actor(actor)
        cls._validate_distinct_users(actor, target)

        cls._lock_pair(actor, target)

        relation = cls._between(actor, target).select_for_update().first()

        if relation is not None:
            if relation.status == Friendship.Status.ACCEPTED:
                raise ValueError("Users are already friends.")

            if relation.status == Friendship.Status.PENDING:
                if relation.from_user_id == actor.pk:
                    raise ValueError("Friend request has already been sent.")

                raise ValueError("Incoming friend request already exists.")

            raise ValueError("Friendship relation already exists.")

        return Friendship.objects.create(
            from_user=actor,
            to_user=target,
            status=Friendship.Status.PENDING,
        )

    @classmethod
    @transaction.atomic
    def cancel_request(cls, actor, target):
        """
        Cancel actor's outgoing pending friend request.

        Raises:
            ValueError:
                If the request does not exist.
        """
        cls._validate_actor(actor)
        cls._validate_distinct_users(actor, target)

        cls._lock_pair(actor, target)

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
            raise ValueError("Friend request not found.")

        friendship.delete()

    @classmethod
    @transaction.atomic
    def accept_request(cls, actor, target):
        """
        Accept an incoming friend request.

        actor:
            User accepting the request.

        target:
            User who originally sent the request.

        Expected relation:

            target -> actor
        """
        cls._validate_actor(actor)
        cls._validate_distinct_users(actor, target)

        cls._lock_pair(actor, target)

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
            raise ValueError("Friend request not found.")

        friendship.status = Friendship.Status.ACCEPTED
        friendship.save(
            update_fields=[
                "status",
            ]
        )

    @classmethod
    @transaction.atomic
    def decline_request(cls, actor, target):
        """
        Decline an incoming friend request.

        actor:
            User declining the request.

        target:
            User who originally sent the request.

        Expected relation:

            target -> actor
        """
        cls._validate_actor(actor)
        cls._validate_distinct_users(actor, target)

        cls._lock_pair(actor, target)

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
            raise ValueError("Friend request not found.")

        friendship.delete()

    @classmethod
    @transaction.atomic
    def remove_friend(cls, actor, target):
        """
        Remove an accepted friendship between two users.

        Friendship direction does not matter once the relation is accepted.
        """
        cls._validate_actor(actor)
        cls._validate_distinct_users(actor, target)

        cls._lock_pair(actor, target)

        friendship = (
            cls._between(actor, target)
            .select_for_update()
            .filter(
                status=Friendship.Status.ACCEPTED,
            )
            .first()
        )

        if friendship is None:
            raise ValueError("Friendship not found.")

        friendship.delete()

    # -------------------------------------------------------------------------
    # Lists
    # -------------------------------------------------------------------------

    @classmethod
    def get_friends(cls, user):
        """
        Return accepted Friendship records involving user.

        Important:
            This method returns a QuerySet of Friendship objects,
            not User objects.

        The actual friend is:

            friendship.to_user
                if friendship.from_user == user

            otherwise:

            friendship.from_user
        """
        return (
            Friendship.objects.filter(
                Q(from_user=user) | Q(to_user=user),
                status=Friendship.Status.ACCEPTED,
            )
            .select_related(
                "from_user",
                "to_user",
            )
            .order_by("-updated_at")
        )

    @staticmethod
    def get_incoming_requests(user):
        """
        Return pending friend requests received by user.
        """
        return (
            Friendship.objects.filter(
                to_user=user,
                status=Friendship.Status.PENDING,
            )
            .select_related(
                "from_user",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def get_outgoing_requests(user):
        """
        Return pending friend requests sent by user.
        """
        return (
            Friendship.objects.filter(
                from_user=user,
                status=Friendship.Status.PENDING,
            )
            .select_related(
                "to_user",
            )
            .order_by("-created_at")
        )

    @classmethod
    def get_mutual_friends(cls, user1, user2):
        """
        Return users who are accepted friends with both users.

        Returns:
            QuerySet[User]
        """
        mutual_ids = cls._mutual_friend_ids(
            user1,
            user2,
        )

        return User.objects.filter(
            pk__in=mutual_ids,
        ).select_related(
            "profile",
        )

    # -------------------------------------------------------------------------
    # Counts
    # -------------------------------------------------------------------------

    @classmethod
    def get_friends_count(cls, user) -> int:
        """
        Return number of accepted friends.
        """
        return cls.get_friends(
            user,
        ).count()

    @classmethod
    def get_incoming_requests_count(cls, user) -> int:
        """
        Return number of pending incoming friend requests.
        """
        return cls.get_incoming_requests(
            user,
        ).count()

    @classmethod
    def get_outgoing_requests_count(cls, user) -> int:
        """
        Return number of pending outgoing friend requests.
        """
        return cls.get_outgoing_requests(
            user,
        ).count()

    @classmethod
    def get_mutual_friends_count(cls, user1, user2) -> int:
        """
        Return number of mutual accepted friends.
        """
        return len(
            cls._mutual_friend_ids(
                user1,
                user2,
            )
        )

    # -------------------------------------------------------------------------
    # UI
    # -------------------------------------------------------------------------

    @staticmethod
    def get_friends_preview(user, limit=5):
        """
        Return a random list of friend users for profile preview.

        This method is intended specifically for compact UI blocks such as
        the friends preview displayed on a profile page.

        Returns:
            list[User]
        """
        friendships = (
            Friendship.objects.filter(
                Q(from_user=user) | Q(to_user=user),
                status=Friendship.Status.ACCEPTED,
            )
            .select_related(
                "from_user__profile__avatar_photo",
                "to_user__profile__avatar_photo",
            )
            .order_by(Random())[:limit]
        )

        return [
            (friendship.to_user if friendship.from_user_id == user.pk else friendship.from_user)
            for friendship in friendships
        ]
