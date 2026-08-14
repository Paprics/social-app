# src/posts/services/access/post.py
"""Access rules for user walls and wall posts."""

from users.models.preferences import UserSettings


class PostAccessService:
    """Access rules for user walls and wall posts."""

    def __init__(
        self,
        *,
        viewer,
        target,
        is_friend=False,
        is_blocked=False,
        target_has_blocked=False,
        can_view_profile=True,
    ):
        self.viewer = viewer
        self.target = target

        self.is_authenticated = bool(
            getattr(
                viewer,
                "is_authenticated",
                False,
            )
        )
        self.is_owner = self.is_authenticated and viewer.pk == target.pk

        self.is_friend = bool(is_friend)

        # Symmetric relationship state:
        # either user has blocked the other.
        #
        # This must not by itself restrict the viewer's access
        # to the target user's wall.
        self.is_blocked = bool(is_blocked)

        # Directional access state:
        # target has blocked viewer.
        #
        # Only this block direction restricts viewer access
        # to target-owned resources.
        self.target_has_blocked = bool(target_has_blocked)

        self.can_view_profile = bool(can_view_profile)

    def can_view_wall(self) -> bool:
        """Return whether viewer may access the target user's wall."""

        if not self.can_view_profile:
            return False

        if self.target_has_blocked and not self.is_owner:
            return False

        return self.target.settings.wall_enabled

    def can_post_on_wall(self) -> bool:
        """Return whether viewer may publish a post on target's wall."""

        if not self.can_view_wall():
            return False

        if not self.is_authenticated:
            return False

        if self.is_owner:
            return True

        if self.target_has_blocked:
            return False

        access_level = self.target.settings.wall_post_permission

        if access_level == UserSettings.AccessLevel.EVERYONE:
            return True

        if access_level == UserSettings.AccessLevel.FRIENDS:
            return self.is_friend

        if access_level == UserSettings.AccessLevel.ONLY_ME:
            return False

        return False

    def can_view_post(self, post) -> bool:
        """Return whether viewer may access the given wall post."""

        if post.owner_id != self.target.pk:
            return False

        return self.can_view_wall()

    def can_edit_post(self, post) -> bool:
        """Return whether viewer may edit the post."""

        if not self.is_authenticated:
            return False

        if post.owner_id != self.target.pk:
            return False

        if post.author_id != self.viewer.pk:
            return False

        if self.target_has_blocked and not self.is_owner:
            return False

        return True

    def can_delete_post(self, post) -> bool:
        """
        Return whether viewer may delete the post.

        A post may be deleted by the post author or the wall owner.
        """

        if not self.is_authenticated:
            return False

        if post.owner_id != self.target.pk:
            return False

        if self.target_has_blocked and not self.is_owner:
            return False

        return post.author_id == self.viewer.pk or post.owner_id == self.viewer.pk
