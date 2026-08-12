# src/gallery/services/albums.py

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils.translation import gettext_lazy as _

from gallery.models import UserAlbum


class AlbumServiceError(Exception):
    """Base exception for album business-rule failures."""


class InvalidAlbumTitleError(AlbumServiceError):
    """Raised when an album title is invalid."""


class InvalidAlbumTypeError(AlbumServiceError):
    """Raised when an unknown album type is requested."""


class AlbumTypeUnavailableError(AlbumServiceError):
    """Raised when a known album type is not enabled yet."""


class InvalidAlbumVisibilityError(AlbumServiceError):
    """Raised when album visibility is invalid."""


class DuplicateAlbumTitleError(AlbumServiceError):
    """Raised when an album title is already used for this type."""


class AlbumService:
    """Apply album business rules and persist album mutations."""

    @classmethod
    def create(
        cls,
        *,
        user,
        title: str,
        visibility: str,
        album_type: str,
    ) -> UserAlbum:
        """Create a regular user album."""

        normalized_title = cls._normalize_title(
            title,
        )

        normalized_type = cls._validate_album_type(
            album_type,
        )

        normalized_visibility = cls._validate_visibility(
            visibility,
        )

        cls._ensure_unique_title(
            user=user,
            title=normalized_title,
            album_type=normalized_type,
        )

        try:
            with transaction.atomic():
                return UserAlbum.objects.create(
                    user=user,
                    title=normalized_title,
                    visibility=normalized_visibility,
                    album_type=normalized_type,
                    purpose=UserAlbum.Purpose.USER,
                )

        except IntegrityError as error:
            raise DuplicateAlbumTitleError(_("You already have an album with this title.")) from error

    @classmethod
    @transaction.atomic
    def update(
        cls,
        *,
        user,
        album_id,
        title,
        description,
        visibility,
        is_visible,
    ) -> UserAlbum | None:
        """
        Update one regular user album.

        System albums cannot be modified through this service method.
        """

        album = (
            UserAlbum.objects.select_for_update()
            .filter(
                pk=album_id,
                user=user,
                purpose=UserAlbum.Purpose.USER,
            )
            .first()
        )

        if album is None:
            return None

        normalized_title = cls._normalize_title(
            title,
        )

        normalized_visibility = cls._validate_visibility(
            visibility,
        )

        cls._ensure_unique_title(
            user=user,
            title=normalized_title,
            album_type=album.album_type,
            exclude_album_id=album.pk,
        )

        album.title = normalized_title
        album.description = (description or "").strip()
        album.visibility = normalized_visibility
        album.is_visible = bool(is_visible)

        album.save(
            update_fields=[
                "title",
                "description",
                "visibility",
                "is_visible",
                "updated_at",
            ],
        )

        return album

    @classmethod
    @transaction.atomic
    def delete(
        cls,
        *,
        user,
        album_id,
    ) -> bool:
        """
        Delete one regular user album and its stored image files.

        System albums are protected from this operation.
        """

        album = (
            UserAlbum.objects.select_for_update()
            .prefetch_related(
                "photos",
            )
            .filter(
                pk=album_id,
                user=user,
                purpose=UserAlbum.Purpose.USER,
            )
            .first()
        )

        if album is None:
            return False

        image_files = [
            (
                photo.image.storage,
                photo.image.name,
            )
            for photo in album.photos.all()
            if photo.image
        ]

        album.delete()

        for storage, image_name in image_files:
            transaction.on_commit(lambda storage=storage, name=image_name: storage.delete(name))

        return True

    @staticmethod
    def _normalize_title(title: str) -> str:
        """Normalize and validate album title."""

        normalized = (title or "").strip()

        if not normalized:
            raise InvalidAlbumTitleError(_("Album title is required."))

        if len(normalized) > 100:
            raise InvalidAlbumTitleError(_("Album title is too long."))

        return normalized

    @staticmethod
    def _validate_album_type(
        album_type: str,
    ) -> UserAlbum.AlbumType:
        """Validate album type."""

        try:
            normalized_type = UserAlbum.AlbumType(album_type)

        except ValueError as error:
            raise InvalidAlbumTypeError(_("Invalid album type.")) from error

        enabled_types = getattr(
            settings,
            "GALLERY_ENABLED_ALBUM_TYPES",
            {
                UserAlbum.AlbumType.PHOTO,
            },
        )

        if normalized_type.value not in enabled_types:
            raise AlbumTypeUnavailableError(_("This album type is not available yet."))

        return normalized_type

    @staticmethod
    def _validate_visibility(
        visibility: str,
    ) -> UserAlbum.Visibility:
        """Validate album visibility."""

        try:
            return UserAlbum.Visibility(visibility)

        except ValueError as error:
            raise InvalidAlbumVisibilityError(_("Invalid album visibility.")) from error

    @staticmethod
    def _ensure_unique_title(
        *,
        user,
        title,
        album_type,
        exclude_album_id=None,
    ) -> None:
        """Reject duplicate titles for regular user albums."""

        albums = UserAlbum.objects.filter(
            user=user,
            purpose=UserAlbum.Purpose.USER,
            album_type=album_type,
            title__iexact=title,
        )

        if exclude_album_id is not None:
            albums = albums.exclude(
                pk=exclude_album_id,
            )

        if albums.exists():
            raise DuplicateAlbumTitleError(_("You already have an album with this title."))
