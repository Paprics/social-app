from users.models.preferences import UserSettings


class ProfileAccessService:
    """Checks profile access permissions."""

    def __init__(self, viewer, target, friendship=None):
        self.viewer = viewer
        self.target = target

        self.is_owner = viewer == target
        self.is_authenticated = viewer.is_authenticated
        self.is_friend = friendship["is_friend"] if friendship else False

    def can_view_profile(self):
        """Checks profile access."""
        return self._check_access(
            self.target.settings.profile_visibility,
        )

    def can_view_friends(self):
        """Checks friends access."""
        return self._check_access(
            self.target.settings.friends_visibility,
        )

    def can_view_photo_albums(self):
        """Checks albums access."""
        return self._check_access(
            self.target.settings.photo_albums_visibility,
        )

    def can_send_message(self):
        """Checks messaging access."""
        return self._check_access(
            self.target.settings.message_permission,
        )

    def can_comment(self):
        """Checks comment access."""
        return self._check_access(
            self.target.settings.comment_permission,
        )

    def can_write_wall(self):
        """Checks wall posting."""

        if not self.target.settings.wall_enabled:
            return False

        return self._check_access(
            self.target.settings.wall_post_permission,
        )

    def _check_access(self, access_level):
        """Checks access level."""

        if self.is_owner:
            return True

        if access_level == UserSettings.AccessLevel.ONLY_ME:
            return False

        if access_level == UserSettings.AccessLevel.EVERYONE:
            return True

        if not self.is_authenticated:
            return False

        return self.is_friend
