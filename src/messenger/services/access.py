# src/messenger/services/access.py

from users.models.preferences import UserSettings
from users.services.friendship_service import FriendshipService
from users.services.user_block import UserBlockService


class MessengerAccessService:
    """
    Access rules for private messaging between users.

    Public API
    ----------
    can_send_message()

    The service checks:
        - authentication;
        - attempts to message oneself;
        - user blocks;
        - target user's message permission;
        - friendship when required by the permission level.

    Friendship and block state may be passed explicitly when they have
    already been resolved by another service or context builder. Otherwise,
    they are loaded lazily when required.
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

        # None means that the value has not been resolved yet.
        self._is_friend = is_friend
        self._is_blocked = is_blocked

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def can_send_message(self) -> bool:
        """
        Return whether viewer may send a private message to target.

        Access is denied when:
            - viewer is anonymous;
            - viewer and target are the same user;
            - either user has blocked the other;
            - target's communication settings deny access.

        Friendship is checked only when target allows messages from
        friends only.
        """
        if not self.is_authenticated:
            return False

        if self.is_owner:
            return False

        if self._get_is_blocked():
            return False

        return self._check_access(
            self.target.settings.message_permission,
        )

    # -------------------------------------------------------------------------
    # Access rules
    # -------------------------------------------------------------------------

    def _check_access(self, access_level) -> bool:
        """
        Evaluate target user's message access level.

        EVERYONE:
            Any authenticated and non-blocked user may send messages.

        FRIENDS:
            Only accepted friends may send messages.

        ONLY_ME:
            No other user may send messages.
        """
        if access_level == UserSettings.AccessLevel.EVERYONE:
            return True

        if access_level == UserSettings.AccessLevel.FRIENDS:
            return self._get_is_friend()

        if access_level == UserSettings.AccessLevel.ONLY_ME:
            return False

        # Deny access for unknown or unsupported values.
        return False

    # -------------------------------------------------------------------------
    # Relationship state
    # -------------------------------------------------------------------------

    def _get_is_friend(self) -> bool:
        """
        Return whether viewer and target are accepted friends.

        Uses a precomputed value when available. Otherwise, resolves the
        friendship through FriendshipService and caches the result for the
        lifetime of this service instance.
        """
        if self._is_friend is None:
            self._is_friend = FriendshipService.are_friends(
                self.viewer,
                self.target,
            )

        return self._is_friend

    def _get_is_blocked(self) -> bool:
        """
        Return whether either user has blocked the other.

        Uses a precomputed value when available. Otherwise, resolves the
        block state through UserBlockService and caches the result for the
        lifetime of this service instance.
        """
        if self._is_blocked is None:
            self._is_blocked = UserBlockService.is_blocked(
                self.viewer,
                self.target,
            )

        return self._is_blocked