# src/users/services/access.py

from users.models.preferences import UserSettings


class ProfileAccessService:
    """Access rules for user profiles."""

    def __init__(self, *, viewer, target, is_friend=False):
        self.viewer = viewer
        self.target = target

        self.is_owner = viewer == target
        self.is_authenticated = viewer.is_authenticated
        self.is_friend = is_friend

    def can_view_profile(self):
        """Return whether the viewer can access the profile."""
        return self._check_access(
            self.target.settings.profile_visibility,
        )

    def can_view_friends(self):
        """Return whether the viewer can access the user's friends."""
        return self._check_access(
            self.target.settings.friends_visibility,
        )

    def _check_access(self, access_level):
        """Evaluate an access level for the current viewer."""

        if self.is_owner:
            return True

        if access_level == UserSettings.AccessLevel.EVERYONE:
            return True

        if access_level == UserSettings.AccessLevel.ONLY_ME:
            return False

        if access_level == UserSettings.AccessLevel.FRIENDS:
            return self.is_authenticated and self.is_friend

        return False
