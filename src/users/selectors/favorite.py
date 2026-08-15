from django.contrib.auth import get_user_model

from gallery.models import Photo
from users.models import Favorite

User = get_user_model()


def get_favorite_profiles(user):
    """Return profile favorites ordered from newest to oldest."""
    return Favorite.objects.for_user(user).for_model(User).order_by("-created_at")


def get_favorite_photos(user):
    """Return photo favorites ordered from newest to oldest."""
    return Favorite.objects.for_user(user).for_model(Photo).order_by("-created_at")


def get_favorites_count(user):
    """Return total number of objects saved by the user."""
    return Favorite.objects.for_user(user).count()


def get_profile_favorites_count(user):
    """Return how many other users saved this user's profile."""
    return Favorite.objects.for_model(User).filter(object_id=user.pk).exclude(user=user).count()
