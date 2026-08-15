# src/notifications/tests/conftest.py

"""Fixtures for notification tests."""

import pytest

from gallery.models import Photo, UserAlbum
from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from gallery.models import Photo, UserAlbum


def make_test_image(name="notification-photo.jpg"):
    buffer = BytesIO()

    image = Image.new(
        "RGB",
        (100, 100),
        "white",
    )
    image.save(
        buffer,
        format="JPEG",
    )

    buffer.seek(0)

    return SimpleUploadedFile(
        name,
        buffer.read(),
        content_type="image/jpeg",
    )


@pytest.fixture
def notification_owner(django_user_model):
    return django_user_model.objects.create_user(
        username="notification_owner",
        password="test-password-123",
    )


@pytest.fixture
def notification_actor(django_user_model):
    return django_user_model.objects.create_user(
        username="notification_actor",
        password="test-password-123",
    )


@pytest.fixture
def notification_other(django_user_model):
    return django_user_model.objects.create_user(
        username="notification_other",
        password="test-password-123",
    )


@pytest.fixture
def notification_album(notification_owner):
    return UserAlbum.objects.create(
        user=notification_owner,
        album_type=UserAlbum.AlbumType.PHOTO,
        purpose=UserAlbum.Purpose.USER,
        title="Notification test album",
        slug="notification-test-album",
        visibility=UserAlbum.Visibility.PUBLIC,
        is_visible=True,
    )


@pytest.fixture
def notification_photo(notification_album):
    return Photo.objects.create(
        album=notification_album,
        image="photos/tests/notification-photo.jpg",
        title="Notification test photo",
        is_visible=True,
    )


@pytest.fixture
def notification_photo(notification_album):
    return Photo.objects.create(
        album=notification_album,
        image=make_test_image(),
        title="Notification test photo",
        is_visible=True,
    )
