# src/users/managers/user_block.py
"""Manager for the UserBlock model."""

from django.db import models


class UserBlockManager(models.Manager):
    """Default manager; user-block reads live in selectors."""
