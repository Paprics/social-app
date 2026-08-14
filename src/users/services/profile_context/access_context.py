# src/users/services/profile_context/access_context.py
"""Build access permissions for profile-related resources."""

from messenger.services.access import MessengerAccessService
from posts.services.access import PostAccessService
from users.services.access import ProfileAccessService


def build_access_context(
    *,
    viewer,
    target,
    is_friend,
    is_blocked,
    target_has_blocked,
):
    """Build permissions for profile-related resources."""

    profile_access = ProfileAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        is_blocked=is_blocked,
        target_has_blocked=target_has_blocked,
    )

    can_view_profile = profile_access.can_view_profile()

    messenger_access = MessengerAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        is_blocked=is_blocked,
    )

    post_access = PostAccessService(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        is_blocked=is_blocked,
        can_view_profile=can_view_profile,
    )

    return {
        "can_view_profile": can_view_profile,
        "can_view_friends": profile_access.can_view_friends(),
        "can_send_message": messenger_access.can_send_message(),
        "can_view_wall": post_access.can_view_wall(),
        "can_post_on_wall": post_access.can_post_on_wall(),
    }
