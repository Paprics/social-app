# src/gallery/services/profile_photos.py

from gallery.models import Photo, UserAlbum
from gallery.services.gallery import get_remaining_slots
from gallery.services.photo_service import process_image
from gallery.validators.image import validate_uploaded_image

PROFILE_PHOTOS_TITLE = "Profile Photos"
PROFILE_PHOTOS_SLUG = "system-profile-photos"


class ProfilePhotoLimitReachedError(Exception):
    """Raised when the user has reached the gallery photo limit."""


class ProfilePhotoService:
    """Manage photos uploaded specifically for use as profile photos."""

    @classmethod
    def get_or_create_album(cls, *, user) -> UserAlbum:
        """Return the user's Profile Photos album, creating it if needed."""

        album, _ = UserAlbum.objects.get_or_create(
            user=user,
            purpose=UserAlbum.Purpose.PROFILE_PHOTOS,
            defaults={
                "title": PROFILE_PHOTOS_TITLE,
                "slug": PROFILE_PHOTOS_SLUG,
                "album_type": UserAlbum.AlbumType.PHOTO,
                "visibility": UserAlbum.Visibility.PRIVATE,
                "is_visible": True,
            },
        )

        return album

    @classmethod
    def create_photo(cls, *, user, file) -> Photo:
        """Validate, process and save a new profile photo."""

        validate_uploaded_image(file)

        if get_remaining_slots(user) <= 0:
            raise ProfilePhotoLimitReachedError(
                "Photo limit reached.",
            )

        processed_image = process_image(file)

        album = cls.get_or_create_album(
            user=user,
        )

        photo = Photo(
            album=album,
            image=processed_image,
            title=file.name,
        )
        photo.save()

        return photo
