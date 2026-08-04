from users.models.user_block import UserBlock


class UserBlockService:
    """Business logic for user blocking."""

    @staticmethod
    def block(user, target):
        """
        Block the target user.
        """
        return UserBlock.objects.get_or_create(
            blocker=user,
            blocked=target,
        )

    @staticmethod
    def unblock(user, target):
        """
        Remove the block.
        """
        deleted_count, _ = UserBlock.objects.filter(
            blocker=user,
            blocked=target,
        ).delete()

        return deleted_count > 0

    @staticmethod
    def is_blocked(user1, user2):
        """
        Return True if either user has blocked the other.
        """
        return UserBlock.objects.is_blocked(user1, user2)
