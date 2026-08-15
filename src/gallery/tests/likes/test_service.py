# src/gallery/tests/likes/test_service.py

"""Tests for gallery like business operations."""

import pytest

from gallery.models import Like
from gallery.services.likes import LikeService


@pytest.mark.django_db
class TestLikeService:
    """Test mutations performed by LikeService."""

    def test_toggle_creates_like(
        self,
        gallery_other,
        gallery_photo,
    ):
        """The first toggle creates a like."""
        is_liked = LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        assert is_liked is True
        assert Like.objects.filter(
            user=gallery_other,
            photo=gallery_photo,
        ).exists()

    def test_second_toggle_removes_like(
        self,
        gallery_other,
        gallery_photo,
    ):
        """The second toggle removes an existing like."""
        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        is_liked = LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        assert is_liked is False
        assert not Like.objects.filter(
            user=gallery_other,
            photo=gallery_photo,
        ).exists()

    def test_toggle_does_not_affect_another_user(
        self,
        gallery_other,
        gallery_stranger,
        gallery_photo,
    ):
        """Toggling one user's like does not affect another user's like."""
        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )
        LikeService.toggle(
            user=gallery_stranger,
            photo=gallery_photo,
        )

        LikeService.toggle(
            user=gallery_other,
            photo=gallery_photo,
        )

        assert not Like.objects.filter(
            user=gallery_other,
            photo=gallery_photo,
        ).exists()

        assert Like.objects.filter(
            user=gallery_stranger,
            photo=gallery_photo,
        ).exists()
