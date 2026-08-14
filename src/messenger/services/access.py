# src/messenger/services/access.py
"""Access rules for private messaging."""

from users.models.preferences import UserSettings
from users.selectors.user_block import is_blocked_between
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
    ):
        self.viewer = viewer
        self.target = target

        self.is_authenticated = viewer.is_authenticated
        self.is_owner = viewer == target

        self._is_friend = is_friend
        self._is_blocked = is_blocked

    def can_send_message(self) -> bool:
        """Return whether viewer may send a private message to target."""

        if not self.is_authenticated:
            return False

        if self.is_owner:
            return False

        if self._get_is_blocked():
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

        return self._is_friend

    def _get_is_blocked(self) -> bool:
        """Return whether either user has blocked the other."""

        if self._is_blocked is None:
            self._is_blocked = is_blocked_between(
                self.viewer,
                self.target,
            )

        return self._is_blocked
