from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from posts.models.comment import Comment


def _photo_comment_queryset():
    """Base queryset for photo comments prepared for rendering."""

    return Comment.objects.select_related(
        "author",
        "author__profile",
        "author__profile__avatar_photo",
        "photo",
        "photo__album",
        "photo__album__user",
        "photo__album__user__settings",
        "parent",
    )


def get_photo_comments(*, photo):
    """
    Return top-level comments for a photo.

    Replies are prefetched and rendered immediately below
    their parent comment.

    Pagination must be applied to this queryset by the view.
    Therefore only root comments count toward the page size.
    """

    replies = (
        _photo_comment_queryset()
        .filter(
            photo=photo,
            parent__isnull=False,
        )
        .order_by(
            "created_at",
            "id",
        )
    )

    return (
        _photo_comment_queryset()
        .filter(
            photo=photo,
            parent__isnull=True,
        )
        .prefetch_related(
            Prefetch(
                "replies",
                queryset=replies,
                to_attr="loaded_replies",
            ),
        )
        .order_by(
            "created_at",
            "id",
        )
    )


def get_photo_comment(*, photo, comment_id):
    """Return one comment belonging to the specified photo."""

    return get_object_or_404(
        _photo_comment_queryset(),
        pk=comment_id,
        photo=photo,
    )


def get_photo_comments_count(*, photo) -> int:
    """Return total number of comments and replies for the photo."""

    return Comment.objects.filter(
        photo=photo,
    ).count()
