from django.db import transaction
from django.db.models import Q

from users.models.friendship import Friendship


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

# FriendshipService.get_friends(user)
# Возвращает список друзей пользователя.

# FriendshipService.get_mutual_friends(user1, user2)
# Возвращает список общих друзей двух пользователей.

# FriendshipService.get_friends_count(user)
# Возвращает количество друзей.

# FriendshipService.get_mutual_friends_count(user1, user2)
# Возвращает количество общих друзей.

# -------------------------------------------------------------------------
# Friend requests
# -------------------------------------------------------------------------

# FriendshipService.get_incoming_requests(user)
# Возвращает входящие заявки.

# FriendshipService.get_outgoing_requests(user)
# Возвращает исходящие заявки.

# FriendshipService.get_incoming_requests_count(user)
# Возвращает количество входящих заявок.

# FriendshipService.get_outgoing_requests_count(user)
# Возвращает количество исходящих заявок.
