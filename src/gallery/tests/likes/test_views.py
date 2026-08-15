# src/gallery/tests/likes/test_views.py

"""Tests for gallery like views."""

import pytest
from django.urls import reverse

from gallery.models import Like, UserAlbum


@pytest.mark.django_db
class TestPhotoLikeToggleView:
    """Test the photo like toggle endpoint."""

    def test_authenticated_user_can_like_photo(
        self,
        client,
        gallery_other,
        gallery_photo,
    ):
        """An authenticated viewer can like an accessible photo."""
        client.force_login(gallery_other)

        response = client.post(
            reverse(
                "gallery:photo_like_toggle",
                kwargs={"photo_pk": gallery_photo.pk},
            )
        )

        assert response.status_code == 200
        assert Like.objects.filter(
            user=gallery_other,
            photo=gallery_photo,
        ).exists()

    def test_second_request_removes_like(
        self,
        client,
        gallery_other,
        gallery_photo,
    ):
        """A second toggle removes the existing like."""
        client.force_login(gallery_other)

        url = reverse(
            "gallery:photo_like_toggle",
            kwargs={"photo_pk": gallery_photo.pk},
        )

        first_response = client.post(url)
        second_response = client.post(url)

        assert first_response.status_code == 200
        assert second_response.status_code == 200

        assert not Like.objects.filter(
            user=gallery_other,
            photo=gallery_photo,
        ).exists()

    def test_anonymous_user_cannot_toggle_like(
        self,
        client,
        gallery_photo,
    ):
        """Anonymous viewers cannot mutate likes."""
        response = client.post(
            reverse(
                "gallery:photo_like_toggle",
                kwargs={"photo_pk": gallery_photo.pk},
            )
        )

        assert response.status_code == 302
        assert Like.objects.count() == 0

    def test_user_cannot_like_inaccessible_photo(
        self,
        client,
        gallery_other,
        gallery_album,
        gallery_photo,
    ):
        """A viewer cannot like an inaccessible photo."""
        gallery_album.visibility = UserAlbum.Visibility.PRIVATE
        gallery_album.save(update_fields=["visibility"])

        client.force_login(gallery_other)

        response = client.post(
            reverse(
                "gallery:photo_like_toggle",
                kwargs={"photo_pk": gallery_photo.pk},
            )
        )

        assert response.status_code in {403, 404}

        assert not Like.objects.filter(
            user=gallery_other,
            photo=gallery_photo,
        ).exists()


@pytest.mark.django_db
class TestPhotoLikesListView:
    """Test access to the photo liker list endpoint."""

    def test_authenticated_user_can_view_likers(
        self,
        client,
        gallery_other,
        gallery_stranger,
        gallery_photo,
    ):
        """An authenticated viewer can access likers of an accessible photo."""
        Like.objects.create(
            user=gallery_stranger,
            photo=gallery_photo,
        )

        client.force_login(gallery_other)

        response = client.get(
            reverse(
                "gallery:photo_likes_list",
                kwargs={"photo_pk": gallery_photo.pk},
            )
        )

        assert response.status_code == 200

    def test_anonymous_user_cannot_view_liker_list(
        self,
        client,
        gallery_photo,
    ):
        """Anonymous viewers cannot access the liker list."""
        response = client.get(
            reverse(
                "gallery:photo_likes_list",
                kwargs={"photo_pk": gallery_photo.pk},
            )
        )

        assert response.status_code == 302

    def test_liker_list_is_blocked_for_inaccessible_photo(
        self,
        client,
        gallery_other,
        gallery_album,
        gallery_photo,
    ):
        """Liker identities are protected by photo access rules."""
        gallery_album.visibility = UserAlbum.Visibility.PRIVATE
        gallery_album.save(update_fields=["visibility"])

        client.force_login(gallery_other)

        response = client.get(
            reverse(
                "gallery:photo_likes_list",
                kwargs={"photo_pk": gallery_photo.pk},
            )
        )

        assert response.status_code in {403, 404}
