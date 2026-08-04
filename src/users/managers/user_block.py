from django.db import models
from django.db.models import Q


class UserBlockManager(models.Manager):
    """Query helpers for the UserBlock model."""

    def is_blocked(self, user1, user2):
        """
        Return True if either user has blocked the other.
        """
        return self.filter(Q(blocker=user1, blocked=user2) | Q(blocker=user2, blocked=user1)).exists()

    def is_blocked_by(self, user1, user2):
        """
        Return True if user2 has blocked user1.
        """
        return self.filter(
            blocker=user2,
            blocked=user1,
        ).exists()

    def blocked_users(self, user):
        """
        Return block relations created by the given user.
        """
        return self.filter(
            blocker=user,
        ).select_related("blocked")

    def blockers(self, user):
        """
        Return all users who have blocked the given user.
        """
        return self.filter(
            blocked=user,
        ).select_related("blocker")

    def blockers_count(self, user):
        """
        Return the number of users who have blocked the given user.
        """
        return self.filter(
            blocked=user,
        ).count()
