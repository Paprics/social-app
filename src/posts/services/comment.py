# src/posts/services/comment.py

from posts.models.comment import Comment


class CommentService:
    """Business operations for comments."""

    @staticmethod
    def create(
        *,
        author,
        content,
        post=None,
        photo=None,
        parent=None,
    ):
        """Create a validated comment."""

        comment = Comment(
            author=author,
            post=post,
            photo=photo,
            parent=parent,
            content=content,
        )

        comment.full_clean()
        comment.save()

        return comment

    @staticmethod
    def update(
        *,
        comment,
        content,
    ):
        """Update an existing comment."""

        comment.content = content

        comment.full_clean()

        comment.save(
            update_fields=[
                "content",
                "updated_at",
            ],
        )

        return comment

    @staticmethod
    def delete(
        *,
        comment,
    ) -> None:
        """Delete an existing comment."""

        comment.delete()
