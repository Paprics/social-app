# src/gallery/services/likes.py

"""Business operations for gallery likes."""

from django.db import transaction

from gallery.models import Like, Photo


class LikeService:
    """Manage likes placed on gallery photos."""

    @staticmethod
    @transaction.atomic
    def toggle(*, user, photo: Photo) -> bool:
        """Toggle a user's like on a photo."""

        like, created = Like.objects.get_or_create(
            user=user,
            photo=photo,
        )

        if created:
            return True

        like.delete()
        return False
