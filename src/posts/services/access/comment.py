# src/posts/services/access/comment.py
"""Access rules for comments on wall posts."""

from users.models.preferences import UserSettings


class CommentAccessService:
    """Access rules for comments on wall posts."""

    def __init__(
        self,
        *,
        viewer,
        target,
        is_friend=False,
        is_blocked=False,
        can_view_profile=True,
    ):
        self.viewer = viewer
        self.target = target

        self.is_authenticated = bool(getattr(viewer, "is_authenticated", False))
        self.is_owner = self.is_authenticated and viewer.pk == target.pk

        self.is_friend = bool(is_friend)
        self.is_blocked = bool(is_blocked)
        self.can_view_profile = bool(can_view_profile)

    def can_view_comments(self, post) -> bool:
        """Return whether viewer may access comments of the given post."""

        if not self.can_view_profile:
            return False

        if self.is_blocked and not self.is_owner:
            return False

        if not self.target.settings.wall_enabled:
            return False

        if post.owner_id != self.target.pk:
            return False

        if not self.target.settings.comments_enabled and not self.is_owner:
            return False

        return True

    def can_comment_on_post(self, post) -> bool:
        """Return whether viewer may leave a comment on the given post."""

        if not self.can_view_comments(post):
            return False

        if not self.target.settings.comments_enabled:
            return False

        if not self.is_authenticated:
            return False

        if self.is_blocked:
            return False

        if self.is_owner:
            return True

        access_level = self.target.settings.comment_permission

        if access_level == UserSettings.AccessLevel.EVERYONE:
            return True

        if access_level == UserSettings.AccessLevel.FRIENDS:
            return self.is_friend

        if access_level == UserSettings.AccessLevel.ONLY_ME:
            return False

        return False

    def can_edit_comment(self, comment) -> bool:
        """Return whether viewer may edit the comment."""

        if not self.is_authenticated:
            return False

        if not self.can_view_comments(comment.post):
            return False

        if comment.author_id != self.viewer.pk:
            return False

        if self.is_blocked and not self.is_owner:
            return False

        return True

    def can_delete_comment(self, comment) -> bool:
        """
        Return whether viewer may delete the comment.

        Allowed for comment author, post author, or wall owner.
        """

        if not self.is_authenticated:
            return False

        if not self.can_view_comments(comment.post):
            return False

        if self.is_blocked and not self.is_owner:
            return False

        return (
            comment.author_id == self.viewer.pk
            or comment.post.author_id == self.viewer.pk
            or comment.post.owner_id == self.viewer.pk
        )
