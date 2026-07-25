# premium.py
from django.conf import settings
from django.db import models


class PremiumPurchase(models.Model):
    """
    Reserved for future premium purchase functionality.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="premium_purchases",
    )

    stars = models.PositiveIntegerField()

    days = models.PositiveIntegerField()

    source = models.CharField(
        max_length=20,
    )

    created_at = models.DateTimeField(auto_now_add=True)
