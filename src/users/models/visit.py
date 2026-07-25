from django.conf import settings
from django.db import models
from django.db.models import F, Q


class ProfileVisit(models.Model):
    """
    Stores the most recent profile visit between two users.
    Each visitor can have only one visit record per profile.
    """

    visitor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_visits_made",
        help_text="The user who visited the profile.",
    )

    profile = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_visits_received",
        help_text="The owner of the visited profile.",
    )

    visited_at = models.DateTimeField(
        auto_now=True,
        help_text="Date and time of the most recent profile visit.",
    )

    class Meta:
        verbose_name = "Profile Visit"
        verbose_name_plural = "Profile Visits"

        constraints = [
            models.UniqueConstraint(
                fields=["visitor", "profile"],
                name="unique_profile_visit",
            ),
            models.CheckConstraint(
                condition=~Q(visitor=F("profile")),
                name="prevent_self_profile_visit",
            ),
        ]

        indexes = [
            models.Index(fields=["profile", "-visited_at"]),
            models.Index(fields=["visitor"]),
        ]

    def __str__(self):
        return f"{self.visitor} → {self.profile}"
