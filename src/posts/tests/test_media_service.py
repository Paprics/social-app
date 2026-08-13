"""Tests for post image attachment business logic."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from gallery.models import Photo, UserAlbum
from posts.models import Post, PostMedia
from posts.services.media import (
    PostMediaLimitError,
    PostMediaOwnershipError,
    PostMediaPermissionError,
    PostMediaService,
)
from posts.services.post import PostService


def make_image_file(
    *,
    name="post-image.png",
    size=(120, 120),
):
    """Create a small valid image upload in memory."""

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


@pytest.fixture
def staff_user(user_factory):
    """Create a staff user allowed to use post images."""

    user = user_factory("staff_user")
    user.is_staff = True
    user.save(update_fields=["is_staff"])

    return user


@pytest.fixture
def staff_post(owner, staff_user):
    """Create a post authored by the staff user."""

    return Post.objects.create(
        owner=owner,
        author=staff_user,
        content="Staff post",
    )


@pytest.fixture
def staff_album(staff_user):
    """Create an ordinary gallery album owned by the staff user."""

    return UserAlbum.objects.create(
        user=staff_user,
        title="Regular album",
        slug="regular-album",
        purpose=UserAlbum.Purpose.USER,
        album_type=UserAlbum.AlbumType.PHOTO,
        visibility=UserAlbum.Visibility.PUBLIC,
    )


@pytest.fixture
def staff_photo(staff_album):
    """Create an existing normal gallery photo."""

    return Photo.objects.create(
        album=staff_album,
        image="tests/existing-photo.webp",
        title="Existing photo",
    )


@pytest.mark.django_db
class TestPostMediaAccess:
    def test_non_staff_cannot_attach_images(
        self,
        wall_post,
        author,
    ):
        album = UserAlbum.objects.create(
            user=author,
            title="Author album",
            slug="author-album",
        )

        photo = Photo.objects.create(
            album=album,
            image="tests/author-photo.webp",
        )

        with pytest.raises(PostMediaPermissionError):
            PostMediaService.attach_existing(
                post=wall_post,
                actor=author,
                photo=photo,
            )

    def test_staff_can_attach_own_existing_photo(
        self,
        staff_post,
        staff_user,
        staff_photo,
    ):
        media = PostMediaService.attach_existing(
            post=staff_post,
            actor=staff_user,
            photo=staff_photo,
        )

        assert media.post == staff_post
        assert media.photo == staff_photo

    def test_staff_cannot_attach_another_users_photo(
        self,
        staff_post,
        staff_user,
        owner,
    ):
        album = UserAlbum.objects.create(
            user=owner,
            title="Owner album",
            slug="owner-album",
        )

        photo = Photo.objects.create(
            album=album,
            image="tests/foreign-photo.webp",
        )

        with pytest.raises(PostMediaOwnershipError):
            PostMediaService.attach_existing(
                post=staff_post,
                actor=staff_user,
                photo=photo,
            )


@pytest.mark.django_db
class TestPostMediaLimit:
    def test_post_image_limit_is_enforced(
        self,
        settings,
        staff_post,
        staff_user,
        staff_album,
    ):
        settings.POST_MAX_IMAGES = 1

        first_photo = Photo.objects.create(
            album=staff_album,
            image="tests/first.webp",
        )

        second_photo = Photo.objects.create(
            album=staff_album,
            image="tests/second.webp",
        )

        PostMediaService.attach_existing(
            post=staff_post,
            actor=staff_user,
            photo=first_photo,
        )

        with pytest.raises(PostMediaLimitError):
            PostMediaService.attach_existing(
                post=staff_post,
                actor=staff_user,
                photo=second_photo,
            )


@pytest.mark.django_db
class TestPostMediaUpload:
    def test_uploaded_photo_uses_post_photos_album(
        self,
        settings,
        tmp_path,
        staff_post,
        staff_user,
    ):
        settings.MEDIA_ROOT = tmp_path

        media = PostMediaService.upload_file(
            post=staff_post,
            actor=staff_user,
            file=make_image_file(),
        )

        assert media.photo.album.user == staff_user
        assert media.photo.album.purpose == UserAlbum.Purpose.POST_PHOTOS

        assert media.photo.image.name.endswith(".webp")

    def test_removing_uploaded_post_photo_deletes_photo(
        self,
        settings,
        tmp_path,
        staff_post,
        staff_user,
    ):
        settings.MEDIA_ROOT = tmp_path

        media = PostMediaService.upload_file(
            post=staff_post,
            actor=staff_user,
            file=make_image_file(),
        )

        media_id = media.pk
        photo_id = media.photo_id

        PostMediaService.remove(
            media=media,
            actor=staff_user,
        )

        assert not PostMedia.objects.filter(
            pk=media_id,
        ).exists()

        assert not Photo.objects.filter(
            pk=photo_id,
        ).exists()

    def test_removing_regular_gallery_photo_keeps_photo(
        self,
        staff_post,
        staff_user,
        staff_photo,
    ):
        media = PostMediaService.attach_existing(
            post=staff_post,
            actor=staff_user,
            photo=staff_photo,
        )

        media_id = media.pk
        photo_id = staff_photo.pk

        PostMediaService.remove(
            media=media,
            actor=staff_user,
        )

        assert not PostMedia.objects.filter(
            pk=media_id,
        ).exists()

        assert Photo.objects.filter(
            pk=photo_id,
        ).exists()


@pytest.mark.django_db
class TestPostMediaCleanup:
    def test_deleting_post_deletes_uploaded_post_photo(
        self,
        settings,
        tmp_path,
        staff_post,
        staff_user,
    ):
        settings.MEDIA_ROOT = tmp_path

        media = PostMediaService.upload_file(
            post=staff_post,
            actor=staff_user,
            file=make_image_file(),
        )

        post_id = staff_post.pk
        photo_id = media.photo_id

        PostService.delete_post(
            staff_post,
        )

        assert not Post.objects.filter(
            pk=post_id,
        ).exists()

        assert not Photo.objects.filter(
            pk=photo_id,
        ).exists()

    def test_deleting_post_keeps_regular_gallery_photo(
        self,
        staff_post,
        staff_user,
        staff_photo,
    ):
        PostMediaService.attach_existing(
            post=staff_post,
            actor=staff_user,
            photo=staff_photo,
        )

        post_id = staff_post.pk
        photo_id = staff_photo.pk

        PostService.delete_post(
            staff_post,
        )

        assert not Post.objects.filter(
            pk=post_id,
        ).exists()

        assert Photo.objects.filter(
            pk=photo_id,
        ).exists()
