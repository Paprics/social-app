from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class UserBlock(models.Model):
    """
    Stores information about users blocked by other users.

    TODO:
        - Create UserBlockManager.
        - Assign objects = UserBlockManager().
        - Create BlockService.
        - Add admin registration.
        - Implement block/unblock views.
        - Add blocked users page.
        - Hide blocked users from search.
        - Prevent private messages.
        - Prevent friend requests.
        - Prevent video chat.
        - Prevent profile viewing (according to privacy settings).
        - Remove recommendations.
        - Handle existing friendships after blocking.
        - Handle existing dialogs after blocking.
        - Add notifications if required.
        - Add tests.
    """

    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blocking",
        verbose_name="Block owner",
    )

    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blocked_by",
        verbose_name="Blocked user",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User block"
        verbose_name_plural = "User blocks"

        ordering = ("-created_at",)

        constraints = [
            models.UniqueConstraint(
                fields=("blocker", "blocked"),
                name="unique_user_block",
            ),
            models.CheckConstraint(
                condition=~models.Q(blocker=models.F("blocked")),
                name="prevent_self_block",
            ),
        ]

        indexes = [
            models.Index(fields=("blocker", "blocked")),
            models.Index(fields=("blocked",)),
        ]

    def __str__(self):
        return f"{self.blocker} blocked {self.blocked}"
