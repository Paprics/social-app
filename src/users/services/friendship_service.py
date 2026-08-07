from django.db.models.functions import Random

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from users.models.friendship import Friendship

User = get_user_model()


class FriendshipService:

    @staticmethod
    def get_relation(viewer, profile_user):
        """
        Returns friendship relation between viewer and profile_user.
        """

        if viewer == profile_user:
            return {
                "is_self": True,
                "is_friend": False,
                "outgoing_request": False,
                "incoming_request": False,
                "can_send_request": False,
            }

        # Анонимный пользователь
        if not viewer.is_authenticated:
            return {
                "is_self": False,
                "is_friend": False,
                "outgoing_request": False,
                "incoming_request": False,
                "can_send_request": False,
            }

        friendship = (
            Friendship.objects.filter(
                Q(from_user=viewer, to_user=profile_user) | Q(from_user=profile_user, to_user=viewer)
            )
            .only("from_user_id", "status")
            .first()
        )

        if friendship is None:
            return {
                "is_self": False,
                "is_friend": False,
                "outgoing_request": False,
                "incoming_request": False,
                "can_send_request": True,
            }

        if friendship.status == Friendship.Status.ACCEPTED:
            return {
                "is_self": False,
                "is_friend": True,
                "outgoing_request": False,
                "incoming_request": False,
                "can_send_request": False,
            }

        if friendship.from_user_id == viewer.id:
            return {
                "is_self": False,
                "is_friend": False,
                "outgoing_request": True,
                "incoming_request": False,
                "can_send_request": False,
            }

        return {
            "is_self": False,
            "is_friend": False,
            "outgoing_request": False,
            "incoming_request": True,
            "can_send_request": False,
        }

    @staticmethod
    @transaction.atomic
    def send_request(viewer, profile_user):
        """
        Отправляет заявку в друзья.
        """

        if viewer == profile_user:
            raise ValueError("You cannot send a friend request to yourself.")

        relation = Friendship.objects.filter(
            Q(from_user=viewer, to_user=profile_user) | Q(from_user=profile_user, to_user=viewer)
        ).first()

        if relation:

            if relation.status == Friendship.Status.ACCEPTED:
                raise ValueError("Users are already friends.")

            if relation.from_user == viewer:
                raise ValueError("Friend request has already been sent.")

            raise ValueError("Incoming friend request already exists.")

        return Friendship.objects.create(
            from_user=viewer,
            to_user=profile_user,
            status=Friendship.Status.PENDING,
        )

    @staticmethod
    def cancel_request(viewer, profile_user):
        deleted, _ = Friendship.objects.filter(
            from_user=viewer,
            to_user=profile_user,
            status=Friendship.Status.PENDING,
        ).delete()

        if deleted == 0:
            raise ValueError("Friend request not found.")

    @staticmethod
    def decline_request(viewer, profile_user):
        friendship = Friendship.objects.filter(
            from_user=profile_user,
            to_user=viewer,
            status=Friendship.Status.PENDING,
        ).first()

        if friendship is None:
            raise ValueError("Friend request not found.")

        friendship.delete()

    @staticmethod
    def accept_request(viewer, profile_user):
        friendship = Friendship.objects.filter(
            from_user=profile_user,
            to_user=viewer,
            status=Friendship.Status.PENDING,
        ).first()

        if friendship is None:
            raise ValueError("Friend request not found.")

        friendship.status = Friendship.Status.ACCEPTED
        friendship.save(update_fields=["status"])

    @staticmethod
    def remove_friend(viewer, profile_user):
        friendship = Friendship.objects.filter(
            Q(from_user=viewer, to_user=profile_user) | Q(from_user=profile_user, to_user=viewer),
            status=Friendship.Status.ACCEPTED,
        ).first()

        if friendship is None:
            raise ValueError("Friendship not found.")

        friendship.delete()

    @classmethod
    def get_incoming_requests(cls, user):
        return (
            Friendship.objects.filter(
                to_user=user,
                status=Friendship.Status.PENDING,
            )
            .select_related("from_user")
            .order_by("-created_at")
        )

    @classmethod
    def get_outgoing_requests(cls, user):
        return (
            Friendship.objects.filter(
                from_user=user,
                status=Friendship.Status.PENDING,
            )
            .select_related("to_user")
            .order_by("-created_at")
        )

    @classmethod
    def get_friends(cls, user):
        """Возвращает список друзей пользователя."""
        return (
            Friendship.objects.filter(
                Q(from_user=user) | Q(to_user=user),
                status=Friendship.Status.ACCEPTED,
            )
            .select_related("from_user", "to_user")
            .order_by("-updated_at")
        )

    @staticmethod
    def are_friends(user1, user2) -> bool:
        """Checks friendship status."""

        if not user1.is_authenticated:
            return False

        return Friendship.objects.filter(
            Q(from_user=user1, to_user=user2) | Q(from_user=user2, to_user=user1),
            status=Friendship.Status.ACCEPTED,
        ).exists()

    @staticmethod
    def get_friends_count(profile_user):
        """Возвращает количество друзей."""

        return Friendship.objects.filter(
            Q(from_user=profile_user) | Q(to_user=profile_user),
            status=Friendship.Status.ACCEPTED,
        ).count()

    @staticmethod
    def get_mutual_friends(user1, user2):
        """Возвращает QuerySet общих друзей двух пользователей."""

        user1_friends = Friendship.objects.filter(
            Q(from_user=user1) | Q(to_user=user1),
            status=Friendship.Status.ACCEPTED,
        )

        user2_friends = Friendship.objects.filter(
            Q(from_user=user2) | Q(to_user=user2),
            status=Friendship.Status.ACCEPTED,
        )

        user1_ids = {
            friendship.to_user_id if friendship.from_user_id == user1.id else friendship.from_user_id
            for friendship in user1_friends
        }

        user2_ids = {
            friendship.to_user_id if friendship.from_user_id == user2.id else friendship.from_user_id
            for friendship in user2_friends
        }

        mutual_ids = user1_ids & user2_ids

        return User.objects.filter(pk__in=mutual_ids).select_related("profile")

    @staticmethod
    def get_incoming_requests_count(user) -> int:
        """
        Возвращает количество входящих заявок в друзья.
        """
        return Friendship.objects.filter(
            to_user=user,
            status=Friendship.Status.PENDING,
        ).count()

    @classmethod
    def get_friends_preview(cls, user, limit=5):
        """Return a random preview of the user's friends."""

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
            friendship.to_user if friendship.from_user_id == user.id else friendship.from_user
            for friendship in friendships
        ]


# -------------------------------------------------------------------------
# Friendship status
# -------------------------------------------------------------------------

# FriendshipService.are_friends(user1, user2)
# Проверяет, являются ли пользователи друзьями.

# FriendshipService.has_pending_request(user1, user2)
# Проверяет, существует ли заявка между пользователями.

# FriendshipService.get_relation(user1, user2)
# Возвращает текущее состояние отношений между пользователями.

# -------------------------------------------------------------------------
# Friend lists
# -------------------------------------------------------------------------

# FriendshipService.get_mutual_friends_count(user1, user2)
# Возвращает количество общих друзей.

# -------------------------------------------------------------------------
# Friend requests
# -------------------------------------------------------------------------

# FriendshipService.get_outgoing_requests_count(user)
# Возвращает количество исходящих заявок.
