# src/users/services/profile_context/relationships.py
"""Build friendship, blocking and favorite state for profile pages."""

from django.urls import reverse

from users.selectors.user_block import get_block_state
from users.services.favorite_service import FavoriteService
from users.services.friendship_service import FriendshipService


def build_relationship_context(*, viewer, target):
    """Build friendship, blocking and favorite state."""

    block_state = get_block_state(
        viewer,
        target,
    )

    if block_state["is_blocked"]:
        friendship = _blocked_friendship_state()
        is_favorite = False
    else:
        friendship = _get_friendship(
            viewer=viewer,
            target=target,
        )
        is_favorite = _get_is_favorite(
            viewer=viewer,
            target=target,
        )

    is_friend = friendship["is_friend"] if friendship else False

    favorite_url = reverse(
        "users:user_favorite_toggle",
        kwargs={
            "pk": target.pk,
        },
    )

    return {
        "friendship": friendship,
        "is_friend": is_friend,
        "is_blocked": block_state["is_blocked"],
        "viewer_has_blocked": block_state["viewer_has_blocked"],
        "target_has_blocked": block_state["target_has_blocked"],
        "is_favorite": is_favorite,
        "favorite_url": favorite_url,
    }


def _blocked_friendship_state():
    """Return the normalized friendship state for a blocked pair."""

    return {
        "is_self": False,
        "is_friend": False,
        "outgoing_request": False,
        "incoming_request": False,
        "can_send_request": False,
    }


def _get_friendship(*, viewer, target):
    if not viewer.is_authenticated:
        return None

    return FriendshipService.get_relation(
        viewer,
        target,
    )


def _get_is_favorite(*, viewer, target):
    if not viewer.is_authenticated:
        return False

    return FavoriteService.is_favorite(
        viewer,
        target,
    )
