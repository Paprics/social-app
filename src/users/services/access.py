# src/users/services/access.py
"""Access rules for user profiles."""

from users.models.preferences import UserSettings


class ProfileAccessService:
    """Access rules for user profiles."""

    def __init__(
        self,
        *,
        viewer,
        target,
        is_friend=False,
        is_blocked=False,
        target_has_blocked=False,
    ):
        self.viewer = viewer
        self.target = target

        self.is_owner = viewer == target
        self.is_authenticated = viewer.is_authenticated
        self.is_friend = bool(is_friend)
        self.is_blocked = bool(is_blocked)
        self.target_has_blocked = bool(target_has_blocked)

    def can_view_profile(self):
        """Return whether the viewer can access the profile."""

        if self.target_has_blocked and not self.is_owner:
            return False

        return self._check_access(
            self.target.settings.profile_visibility,
        )

    def can_view_friends(self):
        """Return whether the viewer can access the user's friends."""

        if self.is_blocked and not self.is_owner:
            return False

        if not self.can_view_profile():
            return False

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
