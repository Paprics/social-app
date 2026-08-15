# src/gallery/services/photo_comments.py

from django.db import transaction

from notifications.services import NotificationService
from posts.services.comment import CommentService


class PhotoCommentService:
    """Business operations for comments attached to gallery photos."""

    @staticmethod
    @transaction.atomic
    def create(
        *,
        author,
        photo,
        content,
        parent=None,
    ):
        comment = CommentService.create(
            author=author,
            content=content,
            photo=photo,
            parent=parent,
        )

        NotificationService.notify_photo_comment(
            actor=author,
            comment=comment,
        )

        return comment

    @staticmethod
    def update(*, comment, content):
        return CommentService.update(
            comment=comment,
            content=content,
        )

    @staticmethod
    def delete(*, comment):
        return CommentService.delete(
            comment=comment,
        )
