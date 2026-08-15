# src/gallery/services/likes.py

"""Business operations for gallery likes."""

from django.db import transaction

from gallery.models import Like, Photo
from notifications.services import NotificationService


class LikeService:
    """Manage likes placed on gallery photos."""

    @staticmethod
    @transaction.atomic
    def toggle(*, user, photo: Photo) -> bool:
        """Toggle a user's like on a photo."""

        like = Like.objects.filter(
            user=user,
            photo=photo,
        ).first()

        if like is not None:
            like.delete()

            NotificationService.remove_photo_like(
                actor=user,
                photo=photo,
            )

            return False

        Like.objects.create(
            user=user,
            photo=photo,
        )

        NotificationService.notify_photo_like(
            actor=user,
            photo=photo,
        )

        return True
