from django.shortcuts import get_object_or_404

from posts.models.comment import Comment


def get_post_comments(*, post):
    """Return top-level comments for the given post."""

    return (
        Comment.objects.filter(
            post=post,
            parent__isnull=True,
        )
        .select_related(
            "author",
            "author__profile",
            "author__profile__avatar_photo",
            "post",
            "post__author",
            "post__owner",
            "post__owner__settings",
        )
        .order_by(
            "-id",
        )
    )


def get_comment(*, comment_id):
    """Return one comment prepared for access checks and rendering."""

    return get_object_or_404(
        Comment.objects.select_related(
            "author",
            "author__profile",
            "author__profile__avatar_photo",
            "post",
            "post__author",
            "post__owner",
            "post__owner__profile",
            "post__owner__settings",
        ),
        pk=comment_id,
    )
