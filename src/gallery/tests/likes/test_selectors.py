# src/gallery/tests/likes/test_selectors.py

"""Tests for gallery like read queries."""

import pytest

from gallery.models import Like
from gallery.selectors.likes import (
    get_photo_likers,
    get_photo_likes_count,
    get_user_liked_photos,
    is_photo_liked_by_user,
)


@pytest.mark.django_db
class TestLikeSelectors:
    """Test selectors used by the gallery like interface."""

    def test_photo_likes_count(
        self,
        gallery_other,
        gallery_stranger,
        gallery_photo,
    ):
        """Like count reflects all likes on the photo."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )
        Like.objects.create(
            user=gallery_stranger,
            photo=gallery_photo,
        )

        assert (
            get_photo_likes_count(
                photo=gallery_photo,
            )
            == 2
        )

    def test_is_photo_liked_by_user_returns_true(
        self,
        gallery_other,
        gallery_photo,
    ):
        """Selector returns true when the user liked the photo."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        assert (
            is_photo_liked_by_user(
                photo=gallery_photo,
                user=gallery_other,
            )
            is True
        )

    def test_is_photo_liked_by_user_returns_false(
        self,
        gallery_other,
        gallery_photo,
    ):
        """Selector returns false when the user did not like the photo."""
        assert (
            is_photo_liked_by_user(
                photo=gallery_photo,
                user=gallery_other,
            )
            is False
        )

    def test_photo_likers_contains_user_who_liked_photo(
        self,
        gallery_other,
        gallery_stranger,
        gallery_photo,
    ):
        """Photo likers contain only users who liked the photo."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        users = list(
            get_photo_likers(
                photo=gallery_photo,
            )
        )

        assert gallery_other in users
        assert gallery_stranger not in users

    def test_user_liked_photos_contains_liked_photo(
        self,
        gallery_other,
        gallery_photo,
    ):
        """Liked photos contain photos liked by the user."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        photos = list(
            get_user_liked_photos(
                user=gallery_other,
            )
        )

        assert gallery_photo in photos

    def test_user_liked_photos_excludes_other_users_likes(
        self,
        gallery_other,
        gallery_stranger,
        gallery_photo,
    ):
        """Liked photos do not include likes created by another user."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        photos = list(
            get_user_liked_photos(
                user=gallery_stranger,
            )
        )

        assert gallery_photo not in photos
