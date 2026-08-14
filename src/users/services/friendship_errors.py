# src/users/services/friendship_errors.py
"""Domain exceptions raised by friendship operations."""


class FriendshipError(Exception):
    """Base exception for friendship business-rule violations."""


class FriendshipAuthenticationError(FriendshipError):
    """Raised when an unauthenticated user attempts a friendship mutation."""


class SelfFriendshipError(FriendshipError):
    """Raised when a user attempts to create a relation with themselves."""


class AlreadyFriendsError(FriendshipError):
    """Raised when users already have an accepted friendship."""


class FriendRequestAlreadyExistsError(FriendshipError):
    """Raised when the same outgoing friend request already exists."""


class IncomingFriendRequestExistsError(FriendshipError):
    """Raised when the target has already sent a request to the actor."""


class FriendRequestNotFoundError(FriendshipError):
    """Raised when the requested pending friendship relation does not exist."""


class FriendshipNotFoundError(FriendshipError):
    """Raised when an accepted friendship cannot be found."""


class FriendshipBlockedError(FriendshipError):
    """Raised when blocking rules prohibit a friendship operation."""


class InvalidFriendshipStateError(FriendshipError):
    """Raised when a friendship has an unsupported state."""
