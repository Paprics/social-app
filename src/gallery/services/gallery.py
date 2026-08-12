from django.conf import settings

from gallery.models import Photo


def get_remaining_slots(user) -> int:
    """Return the number of photo slots still available to the user."""
    used = Photo.objects.filter(album__user=user).count()
    return max(0, settings.GALLERY_MAX_PHOTOS - used)
