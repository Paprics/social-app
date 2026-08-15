# src/gallery/tests/likes/test_model.py

"""Tests for the gallery Like model."""

import pytest
from django.db import IntegrityError, transaction

from gallery.models import Like


@pytest.mark.django_db
class TestLikeModel:
    """Test persistence rules for photo likes."""

    def test_user_can_like_photo(
        self,
        gallery_other,
        gallery_photo,
    ):
        """A user can create a like for a photo."""
        like = Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        assert like.user == gallery_other
        assert like.photo == gallery_photo

    def test_same_user_cannot_like_photo_twice(
        self,
        gallery_other,
        gallery_photo,
    ):
        """A user cannot create duplicate likes for the same photo."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Like.objects.create(
                    user=gallery_other,
                    photo=gallery_photo,
                )

    def test_different_users_can_like_same_photo(
        self,
        gallery_other,
        gallery_stranger,
        gallery_photo,
    ):
        """Different users can like the same photo."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )
        Like.objects.create(
            user=gallery_stranger,
            photo=gallery_photo,
        )

        assert (
            Like.objects.filter(
                photo=gallery_photo,
            ).count()
            == 2
        )

    def test_deleting_photo_deletes_its_likes(
        self,
        gallery_other,
        gallery_photo,
    ):
        """Deleting a photo removes its likes."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        gallery_photo.delete()

        assert Like.objects.count() == 0

    def test_deleting_user_deletes_their_likes(
        self,
        gallery_other,
        gallery_photo,
    ):
        """Deleting a user removes likes created by that user."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        gallery_other.delete()

        assert Like.objects.count() == 0
