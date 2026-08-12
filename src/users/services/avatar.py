# src/users/services/avatar.py

from django.core.exceptions import PermissionDenied
from django.db import transaction

from gallery.models import Photo
from gallery.services.profile_photos import ProfilePhotoService


class AvatarService:
    """Manage the avatar assigned to a user profile."""

    @staticmethod
    @transaction.atomic
    def set_existing(*, user, photo_id) -> Photo:
        """Set one of the user's existing photos as the profile avatar."""

        photo = Photo.objects.filter(
            pk=photo_id,
            album__user=user,
        ).first()

        if photo is None:
            raise PermissionDenied(
                "Photo does not exist or does not belong to this user.",
            )

        profile = user.profile
        profile.avatar_photo = photo
        profile.save(update_fields=["avatar_photo"])

        return photo

    @staticmethod
    @transaction.atomic
    def upload_and_set(*, user, file) -> Photo:
        """Create a profile photo and assign it as the current avatar."""

        photo = ProfilePhotoService.create_photo(
            user=user,
            file=file,
        )

        profile = user.profile
        profile.avatar_photo = photo
        profile.save(update_fields=["avatar_photo"])

        return photo

    @staticmethod
    @transaction.atomic
    def remove(*, user) -> None:
        """Remove the current avatar without deleting the photo."""

        profile = user.profile

        if profile.avatar_photo_id is None:
            return

        profile.avatar_photo = None
        profile.save(update_fields=["avatar_photo"])
