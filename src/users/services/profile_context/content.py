# src/users/services/profile_context/content.py
"""Build profile content such as albums, friends, and mutual friends."""

from gallery.selectors.albums import get_profile_albums
from users.selectors.friendship import (
    get_friends_count,
    get_friends_preview,
    get_mutual_friends,
)


def build_profile_content(
    *,
    viewer,
    target,
    is_friend,
    access,
):
    """Build data displayed on profile pages."""

    albums, albums_count = _get_albums(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        access=access,
    )

    friends, friends_count = _get_friends(
        target=target,
        access=access,
    )

    mutual_friends, mutual_friends_count = _get_mutual_friends(
        viewer=viewer,
        target=target,
        access=access,
    )

    return {
        "albums": albums,
        "albums_count": albums_count,
        "friends": friends,
        "friends_count": friends_count,
        "mutual_friends": mutual_friends,
        "mutual_friends_count": mutual_friends_count,
    }


def _get_albums(
    *,
    viewer,
    target,
    is_friend,
    access,
):
    """Return profile albums visible to the current viewer."""

    if not access["can_view_profile"]:
        return [], 0

    return get_profile_albums(
        viewer=viewer,
        target=target,
        is_friend=is_friend,
        limit=3,
        preview_limit=4,
    )


def _get_friends(
    *,
    target,
    access,
):
    """Return friends preview and total friends count."""

    if not access["can_view_friends"]:
        return [], 0

    friends = get_friends_preview(
        target,
        limit=6,
    )

    friends_count = get_friends_count(
        target,
    )

    return friends, friends_count


def _get_mutual_friends(
    *,
    viewer,
    target,
    access,
):
    """Return mutual friends preview and total mutual friends count."""

    if not viewer.is_authenticated:
        return [], 0

    if viewer == target:
        return [], 0

    if not access["can_view_friends"]:
        return [], 0

    queryset = get_mutual_friends(
        viewer,
        target,
    )

    count = queryset.count()

    if not count:
        return [], 0

    return list(queryset[:6]), count
