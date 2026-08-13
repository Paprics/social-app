"""Selectors for retrieving wall posts and their rendering dependencies."""

from django.contrib.auth import get_user_model
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from posts.models import Post, PostMedia

User = get_user_model()


def _post_media_prefetch():
    """Return the optimized prefetch used when rendering post media."""

    return Prefetch(
        "media_items",
        queryset=PostMedia.objects.select_related(
            "photo",
            "photo__album",
        ).order_by(
            "position",
            "id",
        ),
    )


def get_wall_owner(*, user_id):
    """Return the wall owner with relations required by post access rules."""

    return get_object_or_404(
        User.objects.select_related(
            "profile",
            "settings",
        ),
        pk=user_id,
    )


def get_wall_posts(*, owner):
    """Return posts published on the given user's wall."""

    return (
        Post.objects.filter(
            owner=owner,
        )
        .select_related(
            "owner",
            "owner__settings",
            "author",
            "author__profile",
            "author__profile__avatar_photo",
        )
        .prefetch_related(
            _post_media_prefetch(),
        )
        .order_by(
            "-created_at",
            "-id",
        )
    )


def get_post(*, post_id):
    """Return one post prepared for access checks and rendering."""

    return get_object_or_404(
        Post.objects.select_related(
            "owner",
            "owner__profile",
            "owner__settings",
            "author",
            "author__profile",
            "author__profile__avatar_photo",
        ).prefetch_related(
            _post_media_prefetch(),
        ),
        pk=post_id,
    )
