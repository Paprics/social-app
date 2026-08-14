# src/posts/services/access/context.py
"""Build post access context and UI permissions."""

from users.selectors.user_block import get_block_state
from users.services.access import ProfileAccessService
from users.services.friendship_service import FriendshipService

from .post import PostAccessService


def build_post_access(*, viewer, target):
    """
    Build post access rules for the viewer and wall owner.

    Relationship queries are resolved once and then passed into
    the access services as simple boolean facts.
    """

    if not viewer.is_authenticated or viewer == target:
        is_friend = False
        block_state = {
            "is_blocked": False,
            "target_has_blocked": False,
        }
    else:
        block_state = get_block_state(
            viewer,
            target,
        )

        is_friend = (
            False
            if block_state["is_blocked"]
            else FriendshipService.are_friends(
                viewer,
                target,
            )
        )

    profile_access = ProfileAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        is_blocked=block_state["is_blocked"],
        target_has_blocked=block_state["target_has_blocked"],
    )

    return PostAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        is_blocked=block_state["is_blocked"],
        can_view_profile=profile_access.can_view_profile(),
    )


def get_post_permissions(*, access, post):
    """Return UI permissions for one post."""

    return {
        "can_edit": access.can_edit_post(post),
        "can_delete": access.can_delete_post(post),
    }
