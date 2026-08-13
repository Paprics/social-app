# src/posts/services/post.py""
"""Business operations for wall posts."""

from django.db import transaction

from posts.models import Post
from posts.services.media import PostMediaService


class PostService:
    """Manage wall posts."""

    @staticmethod
    def create(*, owner, author, content):
        """Create a wall post."""

        return Post.objects.create(
            owner=owner,
            author=author,
            content=content,
        )

    @staticmethod
    def update(*, post, content):
        """Update post content."""

        post.content = content
        post.save(
            update_fields=[
                "content",
            ]
        )

        return post

    @staticmethod
    @transaction.atomic
    def delete_post(post: Post) -> None:
        """Delete a post and cleanup orphaned system post photos."""

        cleanup_photos = PostMediaService.collect_cleanup_photos(
            post=post,
        )

        post.delete()

        PostMediaService.cleanup_photos(
            photos=cleanup_photos,
        )
