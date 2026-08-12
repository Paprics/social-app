# src/posts/services/access.py

from users.models.preferences import UserSettings


class PostAccessService:
    """Access rules for wall posts."""

    def __init__(self, *, viewer, target, is_friend=False):
        self.viewer = viewer
        self.target = target

        self.is_authenticated = viewer.is_authenticated
        self.is_owner = viewer == target
        self.is_friend = is_friend

    # -------------------------------------------------------------------------
    # Wall
    # -------------------------------------------------------------------------

    def can_view_wall(self) -> bool:
        """Return whether the target user's wall is enabled."""
        return self.target.settings.wall_enabled

    def can_post_on_wall(self) -> bool:
        """Return whether viewer may publish a post on target's wall."""

        if not self.target.settings.wall_enabled:
            return False

        if not self.is_authenticated:
            return False

        if self.is_owner:
            return True

        access_level = self.target.settings.wall_post_permission

        if access_level == UserSettings.AccessLevel.EVERYONE:
            return True

        if access_level == UserSettings.AccessLevel.FRIENDS:
            return self.is_friend

        if access_level == UserSettings.AccessLevel.ONLY_ME:
            return False

        return False

    # -------------------------------------------------------------------------
    # Post management
    # -------------------------------------------------------------------------

    def can_edit_post(self, post) -> bool:
        """Return whether viewer may edit the post."""

        if not self.is_authenticated:
            return False

        return post.author_id == self.viewer.pk

    def can_delete_post(self, post) -> bool:
        """
        Return whether viewer may delete the post.

        A post may be deleted by:
            - the post author;
            - the owner of the wall where the post was published.
        """

        if not self.is_authenticated:
            return False

        return post.author_id == self.viewer.pk or post.owner_id == self.viewer.pk
