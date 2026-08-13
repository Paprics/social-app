"""Tests for the relation between posts and gallery photos."""

import pytest
from django.db import IntegrityError, transaction

from gallery.models import Photo, UserAlbum
from posts.models import PostMedia


@pytest.fixture
def post_photo(author):
    """Create a gallery photo owned by the post author."""

    album = UserAlbum.objects.create(
        user=author,
        title="Post Photos",
        slug="test-post-photos",
        purpose=UserAlbum.Purpose.POST_PHOTOS,
        album_type=UserAlbum.AlbumType.PHOTO,
        visibility=UserAlbum.Visibility.PRIVATE,
    )

    return Photo.objects.create(
        album=album,
        image="tests/post-photo.webp",
        title="Post photo",
    )


@pytest.mark.django_db
class TestPostMedia:
    def test_photo_can_be_attached_to_post(
        self,
        wall_post,
        post_photo,
    ):
        media = PostMedia.objects.create(
            post=wall_post,
            photo=post_photo,
            position=0,
        )

        assert media.post == wall_post
        assert media.photo == post_photo

        assert list(wall_post.media_items.all()) == [media]

    def test_media_items_are_ordered_by_position(
        self,
        wall_post,
        author,
    ):
        album = UserAlbum.objects.create(
            user=author,
            title="Post Photos",
            slug="ordered-post-photos",
            purpose=UserAlbum.Purpose.POST_PHOTOS,
            album_type=UserAlbum.AlbumType.PHOTO,
            visibility=UserAlbum.Visibility.PRIVATE,
        )

        first_photo = Photo.objects.create(
            album=album,
            image="tests/first.webp",
        )

        second_photo = Photo.objects.create(
            album=album,
            image="tests/second.webp",
        )

        second_media = PostMedia.objects.create(
            post=wall_post,
            photo=second_photo,
            position=1,
        )

        first_media = PostMedia.objects.create(
            post=wall_post,
            photo=first_photo,
            position=0,
        )

        assert list(wall_post.media_items.all()) == [
            first_media,
            second_media,
        ]

    def test_same_photo_cannot_be_attached_twice_to_same_post(
        self,
        wall_post,
        post_photo,
    ):
        PostMedia.objects.create(
            post=wall_post,
            photo=post_photo,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                PostMedia.objects.create(
                    post=wall_post,
                    photo=post_photo,
                )

    def test_deleting_post_deletes_media_relation(
        self,
        wall_post,
        post_photo,
    ):
        media = PostMedia.objects.create(
            post=wall_post,
            photo=post_photo,
        )

        media_id = media.pk
        photo_id = post_photo.pk

        wall_post.delete()

        assert not PostMedia.objects.filter(pk=media_id).exists()

        # The gallery photo itself is not automatically deleted here.
        # Cleanup of Post Photos belongs to the service layer.
        assert Photo.objects.filter(pk=photo_id).exists()

    def test_deleting_photo_deletes_media_relation_but_keeps_post(
        self,
        wall_post,
        post_photo,
    ):
        post_id = wall_post.pk

        media = PostMedia.objects.create(
            post=wall_post,
            photo=post_photo,
        )

        media_id = media.pk

        post_photo.delete()

        assert not PostMedia.objects.filter(pk=media_id).exists()
        assert wall_post.__class__.objects.filter(pk=post_id).exists()
