# src/users/selectors/friendship.py
"""Read-only queries for friendships and friend requests."""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.functions import Coalesce, Random

from users.models.friendship import Friendship

User = get_user_model()


def get_relation_record(user1, user2):
    """Return the friendship record between two users regardless of direction."""

    return (
        Friendship.objects.filter(Q(from_user=user1, to_user=user2) | Q(from_user=user2, to_user=user1))
        .only(
            "from_user_id",
            "to_user_id",
            "status",
            "accepted_at",
        )
        .first()
    )


def get_friends(user):
    """Return accepted friendship records involving the user."""

    return (
        Friendship.objects.filter(
            Q(from_user=user) | Q(to_user=user),
            status=Friendship.Status.ACCEPTED,
        )
        .select_related(
            "from_user",
            "from_user__profile",
            "from_user__profile__avatar_photo",
            "to_user",
            "to_user__profile",
            "to_user__profile__avatar_photo",
        )
        .order_by(
            Coalesce(
                "accepted_at",
                "updated_at",
            ).desc(),
            "-pk",
        )
    )


def get_incoming_requests(user):
    """Return pending friend requests received by the user."""

    return (
        Friendship.objects.filter(
            to_user=user,
            status=Friendship.Status.PENDING,
        )
        .select_related(
            "from_user",
            "from_user__profile",
            "from_user__profile__avatar_photo",
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )


def get_outgoing_requests(user):
    """Return pending friend requests sent by the user."""

    return (
        Friendship.objects.filter(
            from_user=user,
            status=Friendship.Status.PENDING,
        )
        .select_related(
            "to_user",
            "to_user__profile",
            "to_user__profile__avatar_photo",
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )


def _get_friend_ids(user):
    """Return IDs of all users with an accepted friendship to the user."""

    friendships = Friendship.objects.filter(
        Q(from_user=user) | Q(to_user=user),
        status=Friendship.Status.ACCEPTED,
    ).values_list(
        "from_user_id",
        "to_user_id",
    )

    return {to_user_id if from_user_id == user.pk else from_user_id for from_user_id, to_user_id in friendships}


def _get_mutual_friend_ids(user1, user2):
    """Return IDs of users who are accepted friends with both users."""

    return _get_friend_ids(user1) & _get_friend_ids(user2)


def get_mutual_friends(user1, user2):
    """Return users who are accepted friends with both supplied users."""

    mutual_ids = _get_mutual_friend_ids(
        user1,
        user2,
    )

    return (
        User.objects.filter(
            pk__in=mutual_ids,
        )
        .select_related(
            "profile",
            "profile__avatar_photo",
        )
        .order_by("pk")
    )


def get_friends_count(user):
    """Return the number of accepted friends."""

    return Friendship.objects.filter(
        Q(from_user=user) | Q(to_user=user),
        status=Friendship.Status.ACCEPTED,
    ).count()


def get_incoming_requests_count(user):
    """Return the number of pending requests received by the user."""

    return Friendship.objects.filter(
        to_user=user,
        status=Friendship.Status.PENDING,
    ).count()


def get_outgoing_requests_count(user):
    """Return the number of pending requests sent by the user."""

    return Friendship.objects.filter(
        from_user=user,
        status=Friendship.Status.PENDING,
    ).count()


def get_mutual_friends_count(user1, user2):
    """Return the number of mutual accepted friends."""

    return len(
        _get_mutual_friend_ids(
            user1,
            user2,
        )
    )


def get_friendship_counts(user):
    """
    Return Account Center friendship counters in one database query.

    Keys:
        friends: accepted friendships
        incoming: pending requests received by the user
        outgoing: pending requests sent by the user
    """

    return Friendship.objects.filter(
        Q(from_user=user) | Q(to_user=user),
    ).aggregate(
        friends=Count(
            "pk",
            filter=Q(
                status=Friendship.Status.ACCEPTED,
            ),
        ),
        incoming=Count(
            "pk",
            filter=Q(
                status=Friendship.Status.PENDING,
                to_user=user,
            ),
        ),
        outgoing=Count(
            "pk",
            filter=Q(
                status=Friendship.Status.PENDING,
                from_user=user,
            ),
        ),
    )


def get_friends_preview(user, limit=5):
    """Return a random limited list of accepted friend users."""

    friendships = (
        Friendship.objects.filter(
            Q(from_user=user) | Q(to_user=user),
            status=Friendship.Status.ACCEPTED,
        )
        .select_related(
            "from_user",
            "from_user__profile",
            "from_user__profile__avatar_photo",
            "to_user",
            "to_user__profile",
            "to_user__profile__avatar_photo",
        )
        .order_by(Random())[:limit]
    )

    return [
        (friendship.to_user if friendship.from_user_id == user.pk else friendship.from_user)
        for friendship in friendships
    ]
