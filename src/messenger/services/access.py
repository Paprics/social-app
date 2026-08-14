# src/messenger/services/access.py
"""Access rules for private messaging."""

from users.models.preferences import UserSettings
from users.selectors.user_block import has_blocked
from users.services.friendship_service import FriendshipService


class MessengerAccessService:
    """
    Access rules for private messaging between users.

    Friendship and block state may be passed explicitly when already resolved.
    Otherwise, they are loaded lazily when required.
    """

    def __init__(
        self,
        *,
        viewer,
        target,
        is_friend=None,
        is_blocked=None,
        target_has_blocked=None,
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
        self.is_owner = (
            self.is_authenticated
            and viewer.pk == target.pk
        )

        self._is_friend = is_friend

        # Symmetric relationship state.
        # Kept for compatibility with existing callers, but it does not
        # restrict the viewer's access to the target.
        self._is_blocked = is_blocked

        # Directional state: target has explicitly blocked viewer.
        self._target_has_blocked = target_has_blocked

    def can_send_message(self) -> bool:
        """Return whether viewer may send a private message to target."""

        if not self.is_authenticated:
            return False

        if self.is_owner:
            return False

        if self._get_target_has_blocked():
            return False

        return self._check_access(
            self.target.settings.message_permission,
        )

    def _check_access(self, access_level) -> bool:
        """Evaluate target user's message access level."""

        if access_level == UserSettings.AccessLevel.EVERYONE:
            return True

        if access_level == UserSettings.AccessLevel.FRIENDS:
            return self._get_is_friend()

        if access_level == UserSettings.AccessLevel.ONLY_ME:
            return False

        return False

    def _get_is_friend(self) -> bool:
        """Return whether viewer and target are accepted friends."""

        if self._is_friend is None:
            self._is_friend = FriendshipService.are_friends(
                self.viewer,
                self.target,
            )

        return bool(self._is_friend)

    def _get_target_has_blocked(self) -> bool:
        """Return whether target has explicitly blocked viewer."""

        if self._target_has_blocked is None:
            self._target_has_blocked = has_blocked(
                self.target,
                self.viewer,
            )

        return bool(self._target_has_blocked)