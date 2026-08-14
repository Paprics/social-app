# src/users/selectors/user_block.py
"""Read-only queries for user blocking relations."""

from django.db.models import Count, Q

from users.models.user_block import UserBlock


def is_blocked_between(user1, user2) -> bool:
    """Return whether either user has blocked the other."""

    if not getattr(user1, "is_authenticated", False):
        return False

    if not getattr(user2, "is_authenticated", False):
        return False

    if user1 == user2:
        return False

    return UserBlock.objects.filter(Q(blocker=user1, blocked=user2) | Q(blocker=user2, blocked=user1)).exists()


def has_blocked(blocker, blocked) -> bool:
    """Return whether blocker has explicitly blocked blocked."""

    if not getattr(blocker, "is_authenticated", False):
        return False

    if not getattr(blocked, "is_authenticated", False):
        return False

    if blocker == blocked:
        return False

    return UserBlock.objects.filter(
        blocker=blocker,
        blocked=blocked,
    ).exists()


def get_block_state(viewer, target) -> dict[str, bool]:
    """Return directional blocking state between viewer and target."""

    state = {
        "is_blocked": False,
        "viewer_has_blocked": False,
        "target_has_blocked": False,
    }

    if not getattr(viewer, "is_authenticated", False):
        return state

    if not getattr(target, "is_authenticated", False):
        return state

    if viewer == target:
        return state

    relations = UserBlock.objects.filter(
        Q(blocker=viewer, blocked=target) | Q(blocker=target, blocked=viewer)
    ).values_list(
        "blocker_id",
        "blocked_id",
    )

    for blocker_id, blocked_id in relations:
        state["is_blocked"] = True

        if blocker_id == viewer.pk and blocked_id == target.pk:
            state["viewer_has_blocked"] = True

        if blocker_id == target.pk and blocked_id == viewer.pk:
            state["target_has_blocked"] = True

    return state


def get_blocked_relations(user):
    """Return block relations created by user for Account Center."""

    return (
        UserBlock.objects.filter(
            blocker_id=user.pk,
        )
        .select_related(
            "blocked",
            "blocked__profile",
            "blocked__profile__avatar_photo",
        )
        .order_by(
            "-created_at",
            "-pk",
        )
    )


def get_blocked_count(user) -> int:
    """Return the number of users blocked by user."""

    return UserBlock.objects.filter(
        blocker_id=user.pk,
    ).count()


def get_blockers_count(user) -> int:
    """Return the number of users who have blocked user."""

    return UserBlock.objects.filter(
        blocked_id=user.pk,
    ).count()


def get_user_block_counts(user) -> dict[str, int]:
    """Return Account Center block counters in one query."""

    user_id = user.pk

    counts = UserBlock.objects.filter(
        Q(blocker_id=user_id) | Q(blocked_id=user_id),
    ).aggregate(
        blocked_count=Count(
            "pk",
            filter=Q(blocker_id=user_id),
        ),
        blockers_count=Count(
            "pk",
            filter=Q(blocked_id=user_id),
        ),
    )

    return {
        "blocked": counts["blocked_count"],
        "blockers": counts["blockers_count"],
    }
