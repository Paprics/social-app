"""Services for photos uploaded specifically as post attachments."""

from gallery.models import Photo, UserAlbum
from gallery.services.gallery import get_remaining_slots
from gallery.services.photo_service import process_image
from gallery.validators.image import validate_uploaded_image

POST_PHOTOS_TITLE = "Post Photos"
POST_PHOTOS_SLUG = "system-post-photos"


class PostPhotoLimitReachedError(Exception):
    """Raised when the user has reached the global gallery photo limit."""


class PostPhotoService:
    """
    Manage photos uploaded specifically for use in posts.

    Post photos belong to the user who uploaded them and are stored in one
    private system album per user. The album is a storage container and does
    not define whether a photo may be displayed inside a post; post visibility
    is controlled by the posts access layer.
    """

    @classmethod
    def get_or_create_album(cls, *, user) -> UserAlbum:
        """Return the user's Post Photos album, creating it if necessary."""

        album, _ = UserAlbum.objects.get_or_create(
            user=user,
            purpose=UserAlbum.Purpose.POST_PHOTOS,
            defaults={
                "title": POST_PHOTOS_TITLE,
                "slug": POST_PHOTOS_SLUG,
                "album_type": UserAlbum.AlbumType.PHOTO,
                "visibility": UserAlbum.Visibility.PRIVATE,
                "is_visible": True,
            },
        )

        return album

    @classmethod
    def create_photo(cls, *, user, file) -> Photo:
        """
        Validate, process and save one photo uploaded for a post.

        The common gallery validation and Pillow processing pipeline is reused,
        so post uploads follow the same file safety and normalization rules as
        the rest of the gallery.
        """

        validate_uploaded_image(file)

        if get_remaining_slots(user) <= 0:
            raise PostPhotoLimitReachedError(
                "Photo limit reached.",
            )

        processed_image = process_image(file)

        album = cls.get_or_create_album(
            user=user,
        )

        photo = Photo(
            album=album,
            image=processed_image,
        )
        photo.save()

        return photo
