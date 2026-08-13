"""Tests for post media cleanup lifecycle."""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from gallery.models import Photo, UserAlbum
from posts.models import Post, PostMedia
from posts.services.media import PostMediaService
from posts.services.post import PostService
from easy_thumbnails.files import get_thumbnailer

pytestmark = pytest.mark.django_db


def make_image_file(
    *,
    name="test.png",
    size=(100, 100),
    color="red",
):
    """Return a valid in-memory PNG upload."""

    output = BytesIO()

    Image.new(
        "RGB",
        size,
        color,
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


class TestPostMediaCleanup:
    """Verify cleanup rules for images attached to posts."""

    def test_post_photo_is_deleted_with_last_post(
        self,
        owner,
        staff_user,
        settings,
        tmp_path,
        django_capture_on_commit_callbacks,
    ):
        """Deleting the last post reference removes its system photo and file."""

        settings.MEDIA_ROOT = tmp_path

        post = Post.objects.create(
            owner=owner,
            author=staff_user,
            content="Post with image",
        )

        media = PostMediaService.upload_file(
            post=post,
            actor=staff_user,
            file=make_image_file(),
        )

        photo = media.photo
        photo_id = photo.pk

        storage = photo.image.storage
        image_name = photo.image.name

        assert Photo.objects.filter(pk=photo_id).exists()
        assert PostMedia.objects.filter(
            post=post,
            photo_id=photo_id,
        ).exists()
        assert storage.exists(image_name)

        with django_capture_on_commit_callbacks(execute=True):
            PostService.delete_post(post)

        assert not Photo.objects.filter(
            pk=photo_id,
        ).exists()

        assert not PostMedia.objects.filter(
            photo_id=photo_id,
        ).exists()

        assert not storage.exists(image_name)

    def test_regular_gallery_photo_survives_post_deletion(
        self,
        owner,
        staff_user,
        settings,
        tmp_path,
    ):
        """A normal gallery photo must not be owned by the post lifecycle."""

        settings.MEDIA_ROOT = tmp_path

        album = UserAlbum.objects.create(
            user=staff_user,
            title="My album",
            slug="my-album",
            purpose=UserAlbum.Purpose.USER,
            visibility=UserAlbum.Visibility.PRIVATE,
        )

        photo = Photo.objects.create(
            album=album,
            image=make_image_file(
                name="gallery.png",
            ),
            title="Gallery photo",
        )

        photo_id = photo.pk

        post = Post.objects.create(
            owner=owner,
            author=staff_user,
            content="Using gallery photo",
        )

        PostMediaService.attach_existing(
            post=post,
            actor=staff_user,
            photo=photo,
        )

        assert post.media_items.count() == 1

        PostService.delete_post(post)

        assert Photo.objects.filter(
            pk=photo_id,
        ).exists()

        assert not PostMedia.objects.filter(
            photo_id=photo_id,
        ).exists()

    def test_shared_post_photo_survives_until_last_post_is_deleted(
        self,
        owner,
        staff_user,
        settings,
        tmp_path,
        django_capture_on_commit_callbacks,
    ):
        """A system photo shared by posts is deleted only after its final reference."""

        settings.MEDIA_ROOT = tmp_path

        first_post = Post.objects.create(
            owner=owner,
            author=staff_user,
            content="First post",
        )

        second_post = Post.objects.create(
            owner=owner,
            author=staff_user,
            content="Second post",
        )

        first_media = PostMediaService.upload_file(
            post=first_post,
            actor=staff_user,
            file=make_image_file(
                name="shared.png",
            ),
        )

        photo = first_media.photo
        photo_id = photo.pk

        storage = photo.image.storage
        image_name = photo.image.name

        PostMediaService.attach_existing(
            post=second_post,
            actor=staff_user,
            photo=photo,
        )

        assert (
            PostMedia.objects.filter(
                photo_id=photo_id,
            ).count()
            == 2
        )

        with django_capture_on_commit_callbacks(execute=True):
            PostService.delete_post(first_post)

        assert Photo.objects.filter(
            pk=photo_id,
        ).exists()

        assert (
            PostMedia.objects.filter(
                photo_id=photo_id,
            ).count()
            == 1
        )

        assert storage.exists(image_name)

        with django_capture_on_commit_callbacks(execute=True):
            PostService.delete_post(second_post)

        assert not Photo.objects.filter(
            pk=photo_id,
        ).exists()

        assert not PostMedia.objects.filter(
            photo_id=photo_id,
        ).exists()

        assert not storage.exists(image_name)

    @pytest.mark.xfail(
        reason=(
            "Post photo cleanup removes the source image but does not yet " "remove generated easy-thumbnails files."
        ),
        strict=False,
    )
    def test_post_photo_thumbnails_are_deleted_with_photo(
        self,
        owner,
        staff_user,
        settings,
        tmp_path,
        django_capture_on_commit_callbacks,
    ):
        """Deleting an orphaned post photo must also remove its thumbnails."""

        settings.MEDIA_ROOT = tmp_path

        post = Post.objects.create(
            owner=owner,
            author=staff_user,
            content="Post with thumbnail",
        )

        media = PostMediaService.upload_file(
            post=post,
            actor=staff_user,
            file=make_image_file(
                name="thumbnail-test.png",
                size=(1000, 800),
            ),
        )

        photo = media.photo

        thumbnail = get_thumbnailer(
            photo.image,
        )["photo_preview"]

        source_storage = photo.image.storage
        source_name = photo.image.name

        thumbnail_storage = thumbnail.storage
        thumbnail_name = thumbnail.name

        assert source_storage.exists(source_name)
        assert thumbnail_storage.exists(thumbnail_name)

        with django_capture_on_commit_callbacks(execute=True):
            PostService.delete_post(post)

        assert not Photo.objects.filter(
            pk=photo.pk,
        ).exists()

        assert not source_storage.exists(source_name)

        assert not thumbnail_storage.exists(thumbnail_name)
