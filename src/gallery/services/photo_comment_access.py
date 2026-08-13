# src/gallery/services/photo_comment_access.py

from users.models.preferences import UserSettings


class PhotoCommentAccessService:
    """Access rules for comments on gallery photos."""

    def __init__(
        self,
        *,
        viewer,
        target,
        gallery_access,
        is_friend=False,
        is_blocked=False,
        can_view_profile=True,
    ):
        self.viewer = viewer
        self.target = target
        self.gallery_access = gallery_access

        self.is_friend = bool(is_friend)
        self.is_blocked = bool(is_blocked)
        self.can_view_profile = bool(can_view_profile)

    @property
    def is_authenticated(self) -> bool:
        return bool(
            getattr(
                self.viewer,
                "is_authenticated",
                False,
            ),
        )

    @property
    def is_owner(self) -> bool:
        return self.is_authenticated and self.viewer.pk == self.target.pk

    def can_comment_on_photo(self, photo) -> bool:
        """Return whether viewer may leave a comment on the photo."""

        if not self.can_view_comments(photo):
            return False

        # Global switch disables creation for everyone,
        # including the content owner.
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

    def can_reply_to_comment(
        self,
        *,
        photo,
        comment,
    ) -> bool:
        """Return whether viewer may reply to a root photo comment."""

        if not self.can_comment_on_photo(photo):
            return False

        if comment.photo_id != photo.pk:
            return False

        if comment.parent_id is not None:
            return False

        return True

    def can_edit_comment(self, comment) -> bool:
        """
        Only the comment author may edit their photo comment.
        """

        if not self.is_authenticated:
            return False

        if comment.photo_id is None:
            return False

        if comment.author_id != self.viewer.pk:
            return False

        if not self.can_view_comments(comment.photo):
            return False

        if self.is_blocked and not self.is_owner:
            return False

        return True

    def can_delete_comment(self, comment) -> bool:
        """
        Only the comment author may delete their photo comment.

        The photo owner does not receive implicit permission
        to delete somebody else's comment.
        """

        if not self.is_authenticated:
            return False

        if comment.photo_id is None:
            return False

        if comment.author_id != self.viewer.pk:
            return False

        return self.can_view_comments(
            comment.photo,
        )

    def can_view_comments(self, photo) -> bool:
        """Return whether viewer may access comments of this photo."""

        if not self.can_view_profile:
            return False

        if photo.album.user_id != self.target.pk:
            return False

        if not self.target.settings.comments_enabled and not self.is_owner:
            return False

        return self.gallery_access.can_view_photo(photo)
