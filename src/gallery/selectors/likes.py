# src/gallery/selectors/likes.py

"""Read queries for gallery likes."""

from django.contrib.auth import get_user_model

from gallery.models import Like, Photo

User = get_user_model()


def get_photo_likes_count(*, photo: Photo) -> int:
    """Return the number of likes placed on a photo."""

    return Like.objects.filter(
        photo=photo,
    ).count()


def is_photo_liked_by_user(*, photo: Photo, user) -> bool:
    """Return whether the user has liked the photo."""

    if not user.is_authenticated:
        return False

    return Like.objects.filter(
        user=user,
        photo=photo,
    ).exists()


def get_photo_likers(*, photo: Photo):
    """Return users who liked the photo, newest likes first."""

    return (
        User.objects.filter(
            gallery_likes__photo=photo,
        )
        .select_related("profile")
        .order_by("-gallery_likes__created_at")
    )


def get_user_liked_photos(*, user):
    """Return photos liked by the user, newest likes first."""

    return (
        Photo.objects.filter(
            likes__user=user,
        )
        .select_related(
            "album",
            "album__user",
            "album__user__profile",
            "album__user__settings",
        )
        .order_by("-likes__created_at")
    )
