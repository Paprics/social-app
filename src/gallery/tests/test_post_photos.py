"""Tests for the system Post Photos album and PostPhotoService."""

from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import override_settings
from PIL import Image

from gallery.models import Photo, UserAlbum
from gallery.services.post_photos import (
    POST_PHOTOS_SLUG,
    PostPhotoLimitReachedError,
    PostPhotoService,
)

User = get_user_model()


def make_image_file(
    *,
    name="post-photo.png",
    size=(100, 100),
):
    """Create an in-memory image suitable for upload tests."""

    output = BytesIO()

    Image.new(
        "RGB",
        size,
    ).save(
        output,
        format="PNG",
    )

    output.seek(0)

    return SimpleUploadedFile(
        name,
        output.read(),
        content_type="image/png",
    )


@pytest.mark.django_db
class TestPostPhotoAlbum:
    def test_service_creates_one_private_system_album(self):
        user = User.objects.create_user(
            username="post_photo_owner",
            password="test-password-123",
        )

        album = PostPhotoService.get_or_create_album(
            user=user,
        )

        assert album.user == user
        assert album.purpose == UserAlbum.Purpose.POST_PHOTOS
        assert album.album_type == UserAlbum.AlbumType.PHOTO
        assert album.visibility == UserAlbum.Visibility.PRIVATE
        assert album.slug == POST_PHOTOS_SLUG

    def test_get_or_create_returns_same_album(self):
        user = User.objects.create_user(
            username="post_photo_owner",
            password="test-password-123",
        )

        first = PostPhotoService.get_or_create_album(
            user=user,
        )

        second = PostPhotoService.get_or_create_album(
            user=user,
        )

        assert first.pk == second.pk

        assert (
            UserAlbum.objects.filter(
                user=user,
                purpose=UserAlbum.Purpose.POST_PHOTOS,
            ).count()
            == 1
        )

    def test_database_rejects_second_post_photos_album(self):
        user = User.objects.create_user(
            username="post_photo_owner",
            password="test-password-123",
        )

        PostPhotoService.get_or_create_album(
            user=user,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                UserAlbum.objects.create(
                    user=user,
                    purpose=UserAlbum.Purpose.POST_PHOTOS,
                    title="Another Post Photos",
                    slug="another-post-photos",
                    album_type=UserAlbum.AlbumType.PHOTO,
                    visibility=UserAlbum.Visibility.PRIVATE,
                )


@pytest.mark.django_db
class TestPostPhotoService:
    @override_settings(
        MEDIA_ROOT="/tmp/social-network-test-media",
    )
    def test_create_photo_uses_post_photos_album(self):
        user = User.objects.create_user(
            username="post_photo_owner",
            password="test-password-123",
        )

        photo = PostPhotoService.create_photo(
            user=user,
            file=make_image_file(),
        )

        assert isinstance(photo, Photo)
        assert photo.album.user == user
        assert photo.album.purpose == UserAlbum.Purpose.POST_PHOTOS
        assert photo.image.name.endswith(".webp")

    @override_settings(
        GALLERY_MAX_PHOTOS=0,
    )
    def test_create_photo_respects_global_gallery_limit(self):
        user = User.objects.create_user(
            username="post_photo_owner",
            password="test-password-123",
        )

        with pytest.raises(PostPhotoLimitReachedError):
            PostPhotoService.create_photo(
                user=user,
                file=make_image_file(),
            )

        assert (
            Photo.objects.filter(
                album__user=user,
            ).count()
            == 0
        )
