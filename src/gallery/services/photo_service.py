# src/gallery/services/photo_service.py

from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image, ImageOps

from gallery.models import Photo, UserAlbum
from gallery.services.gallery import get_remaining_slots


class InvalidPhotoTitleError(Exception):
    """Raised when a photo title is invalid."""


def process_image(image) -> ContentFile:
    """
    Process an uploaded image before persistence.

    - fixes EXIF orientation;
    - converts to RGB;
    - resizes to configured maximum size;
    - converts to configured output format;
    - optionally strips metadata.
    """

    img = Image.open(
        image,
    )

    img = ImageOps.exif_transpose(
        img,
    )

    if img.mode != "RGB":
        img = img.convert(
            "RGB",
        )

    img.thumbnail(
        (
            settings.GALLERY_IMAGE_MAX_SIZE,
            settings.GALLERY_IMAGE_MAX_SIZE,
        ),
        Image.Resampling.LANCZOS,
    )

    output = BytesIO()

    save_kwargs = {
        "format": settings.GALLERY_IMAGE_FORMAT,
        "quality": settings.GALLERY_IMAGE_QUALITY,
        "optimize": True,
    }

    if not settings.GALLERY_IMAGE_STRIP_METADATA:
        exif = img.info.get(
            "exif",
        )

        if exif:
            save_kwargs["exif"] = exif

    img.save(
        output,
        **save_kwargs,
    )

    output.seek(
        0,
    )

    filename = f"{Path(image.name).stem}." f"{settings.GALLERY_IMAGE_FORMAT.lower()}"

    return ContentFile(
        output.read(),
        name=filename,
    )


class PhotoService:
    """Apply photo business rules and persist photo mutations."""

    @staticmethod
    def upload_to_album(
        *,
        user,
        album_id,
        files,
    ) -> dict | None:
        """
        Upload files into one ordinary photo album owned by user.
        """

        album = UserAlbum.objects.filter(
            pk=album_id,
            user=user,
            album_type=UserAlbum.AlbumType.PHOTO,
            purpose=UserAlbum.Purpose.USER,
        ).first()

        if album is None:
            return None

        files = list(
            files,
        )

        slots = get_remaining_slots(
            user,
        )

        accepted = files[:slots]

        skipped = max(
            0,
            len(files) - len(accepted),
        )

        saved = []

        for file in accepted:
            processed = process_image(
                file,
            )

            photo = Photo.objects.create(
                album=album,
                image=processed,
                title=Path(file.name).name[:100],
            )

            saved.append(
                photo,
            )

        return {
            "saved": saved,
            "skipped": skipped,
        }

    @classmethod
    @transaction.atomic
    def update_album_photos(
        cls,
        *,
        user,
        album_id,
        updates,
    ) -> bool:
        """
        Update titles and visibility for photos inside one user album.

        Expected structure:

            {
                10: {
                    "title": "Beach",
                    "is_visible": True,
                },
                11: {
                    "title": "",
                    "is_visible": False,
                },
            }
        """

        album = (
            UserAlbum.objects.select_for_update()
            .filter(
                pk=album_id,
                user=user,
                album_type=UserAlbum.AlbumType.PHOTO,
                purpose=UserAlbum.Purpose.USER,
            )
            .first()
        )

        if album is None:
            return False

        if not updates:
            return True

        photo_ids = list(updates.keys())

        photos = list(
            Photo.objects.filter(
                album=album,
                pk__in=photo_ids,
            )
        )

        for photo in photos:
            data = updates.get(
                photo.pk,
                {},
            )

            photo.title = cls._normalize_title(
                data.get(
                    "title",
                    "",
                )
            )

            photo.is_visible = bool(
                data.get(
                    "is_visible",
                    False,
                )
            )

        if photos:
            Photo.objects.bulk_update(
                photos,
                [
                    "title",
                    "is_visible",
                ],
            )

        return True

    @staticmethod
    @transaction.atomic
    def delete(
        *,
        user,
        photo_id,
    ) -> bool:
        """
        Delete one photo from a regular user album.

        The database row is deleted first. The physical image is
        removed only after the transaction commits successfully.
        """

        photo = (
            Photo.objects.select_for_update()
            .select_related(
                "album",
            )
            .filter(
                pk=photo_id,
                album__user=user,
                album__purpose=UserAlbum.Purpose.USER,
            )
            .first()
        )

        if photo is None:
            return False

        storage = None
        image_name = None

        if photo.image:
            storage = photo.image.storage
            image_name = photo.image.name

        photo.delete()

        if storage and image_name:
            transaction.on_commit(lambda: storage.delete(image_name))

        return True

    @staticmethod
    def _normalize_title(title) -> str:
        """Normalize and validate a photo title."""

        normalized = (title or "").strip()

        if len(normalized) > 100:
            raise InvalidPhotoTitleError("Photo title is too long.")

        return normalized
