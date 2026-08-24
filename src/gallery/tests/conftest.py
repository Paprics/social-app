# src/gallery/tests/conftest.py

import itertools
from datetime import date

import pytest
from django.contrib.auth import get_user_model

from gallery.models import Photo, UserAlbum
from posts.models import Comment
from users.models.preferences import UserSettings
from users.models.profile import Profile

User = get_user_model()

TEST_PASSWORD = "test-password-123"


@pytest.fixture
def user_factory(db):
    """Create a complete user suitable for gallery comment tests."""

    counter = itertools.count(1)

    def create_user(username=None):
        number = next(counter)

        user = User.objects.create_user(
            username=username or f"gallery_test_user_{number}",
            password=TEST_PASSWORD,
        )

        # UserSettings is created by the project's user signal.
        assert hasattr(user, "settings")

        Profile.objects.create(
            user=user,
            birth_date=date(1990, 1, 1),
            gender=Profile.Gender.MALE,
        )

        assert hasattr(user, "profile")

        # Keep gallery/comment access explicit so the fixtures do not depend
        # on model defaults.
        user.settings.profile_visibility = UserSettings.AccessLevel.EVERYONE
        user.settings.photo_albums_visibility = UserSettings.AccessLevel.EVERYONE
        user.settings.comment_permission = UserSettings.AccessLevel.EVERYONE
        user.settings.comments_enabled = True
        user.settings.save(
            update_fields=[
                "profile_visibility",
                "photo_albums_visibility",
                "comment_permission",
                "comments_enabled",
            ]
        )

        return user

    return create_user


@pytest.fixture
def gallery_owner(user_factory):
    """Owner of the tested gallery."""

    return user_factory("gallery_owner")


@pytest.fixture
def gallery_other(user_factory):
    """Unrelated authenticated gallery viewer."""

    return user_factory("gallery_other")


@pytest.fixture
def gallery_stranger(user_factory):
    """Another unrelated authenticated gallery viewer."""

    return user_factory("gallery_stranger")


@pytest.fixture
def gallery_album(gallery_owner):
    """Public ordinary photo album owned by gallery_owner."""

    return UserAlbum.objects.create(
        user=gallery_owner,
        album_type=UserAlbum.AlbumType.PHOTO,
        purpose=UserAlbum.Purpose.USER,
        title="Test album",
        slug="test-album",
        visibility=UserAlbum.Visibility.PUBLIC,
        is_visible=True,
    )


@pytest.fixture
def gallery_photo(gallery_album):
    """Visible photo inside the public test album."""

    return Photo.objects.create(
        album=gallery_album,
        image="photos/tests/test-photo.jpg",
        description="Test photo description",
        is_visible=True,
    )


@pytest.fixture
def photo_comment(gallery_photo, gallery_other):
    """Root photo comment written by gallery_other."""

    return Comment.objects.create(
        photo=gallery_photo,
        author=gallery_other,
        content="Initial photo comment",
    )


@pytest.fixture
def owner_photo_comment(gallery_photo, gallery_owner):
    """Existing root photo comment written by the gallery owner."""

    return Comment.objects.create(
        photo=gallery_photo,
        author=gallery_owner,
        content="Owner photo comment",
    )
