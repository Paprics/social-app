# src/users/models/friendship.py
"""Database model for friend requests and accepted friendships."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Greatest, Least


class Friendship(models.Model):
    """
    Represents a friendship relation between two users.

    Pending relations are directional:
        from_user -> to_user

    Accepted relations are treated as an undirected friendship pair.
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
        help_text="Current status of the friendship relation.",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Date and time when the friend request was created.",
    )

    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date and time when the friend request was accepted.",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time when the friendship relation was last updated.",
    )

    class Meta:
        verbose_name = "Friendship"
        verbose_name_plural = "Friendships"

        constraints = [
            models.UniqueConstraint(
                Least("from_user", "to_user"),
                Greatest("from_user", "to_user"),
                name="unique_friendship_pair",
            ),
            models.CheckConstraint(
                condition=~Q(from_user=F("to_user")),
                name="prevent_self_friendship",
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "pending",
                        "accepted",
                    ]
                ),
                name="valid_friendship_status",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "from_user",
                    "status",
                ]
            ),
            models.Index(
                fields=[
                    "to_user",
                    "status",
                ]
            ),
        ]

    def __str__(self):
        return f"{self.from_user} -> {self.to_user} " f"({self.get_status_display()})"
