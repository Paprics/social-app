# friendship.py
from django.conf import settings
from django.db import models
from django.db.models import F, Q


class Friendship(models.Model):
    """
    Represents a friendship request and its current status between two users.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"

    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="initiated_friendships",
        help_text="The user who initiated the friendship request.",
    )

    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_friendships",
        help_text="The user who received the friendship request.",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        help_text="Current status of the friendship request.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the friendship request was created.",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the friendship request was last updated.",
    )

    class Meta:
        verbose_name = "Friendship"
        verbose_name_plural = "Friendships"
        constraints = [
            models.UniqueConstraint(
                fields=["from_user", "to_user"],
                name="unique_friendship_request",
            ),
            models.CheckConstraint(
                condition=~Q(from_user=F("to_user")),
                name="prevent_self_friendship",
            ),
        ]
        indexes = [
            models.Index(fields=["to_user"]),
            models.Index(fields=["from_user", "status"]),
            models.Index(fields=["to_user", "status"]),
        ]

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} " f"({self.get_status_display()})"
