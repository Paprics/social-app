# src/gallery/tests/likes/test_account_center.py

"""Tests for liked photos in Account Center."""

import pytest
from django.urls import reverse

from gallery.models import Like, UserAlbum
from users.views.account_center import AccountCenterLikedPhotosView


def get_view_context(*, rf, user):
    """Build Account Center liked photos context without rendering HTML."""

    request = rf.get(
        reverse("users:account_center_liked_photos"),
    )
    request.user = user

    view = AccountCenterLikedPhotosView()
    view.setup(request)

    view.object_list = view.get_queryset()

    return view.get_context_data()


@pytest.mark.django_db
class TestAccountCenterLikedPhotosView:
    """Test liked photo data in Account Center."""

    def test_login_is_required(
        self,
        client,
    ):
        """Anonymous users cannot access liked photos."""
        response = client.get(reverse("users:account_center_liked_photos"))

        assert response.status_code == 302

    def test_liked_accessible_photo_is_available(
        self,
        rf,
        gallery_other,
        gallery_photo,
    ):
        """An accessible liked photo is returned for the current user."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        context = get_view_context(
            rf=rf,
            user=gallery_other,
        )

        assert gallery_photo in context["photos"]

    def test_other_users_like_is_not_available(
        self,
        rf,
        gallery_other,
        gallery_stranger,
        gallery_photo,
    ):
        """Likes created by another user are not returned."""
        Like.objects.create(
            user=gallery_stranger,
            photo=gallery_photo,
        )

        context = get_view_context(
            rf=rf,
            user=gallery_other,
        )

        assert gallery_photo not in context["photos"]

    def test_inaccessible_liked_photo_is_not_available(
        self,
        rf,
        gallery_other,
        gallery_album,
        gallery_photo,
    ):
        """A previously liked photo disappears after access is revoked."""
        Like.objects.create(
            user=gallery_other,
            photo=gallery_photo,
        )

        gallery_album.visibility = UserAlbum.Visibility.PRIVATE
        gallery_album.save(
            update_fields=["visibility"],
        )

        context = get_view_context(
            rf=rf,
            user=gallery_other,
        )

        assert gallery_photo not in context["photos"]
