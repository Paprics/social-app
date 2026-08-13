# src/posts/models/media.py
"""Models connecting wall posts with gallery media."""

from django.db import models

from gallery.models import Photo


class PostMedia(models.Model):
    """
    Attach one gallery photo to a post.

    The photo itself remains owned and stored by the gallery app.
    This model only describes its use inside a post and its display order.
    """

    post = models.ForeignKey(
        "posts.Post",
        on_delete=models.CASCADE,
        related_name="media_items",
    )

    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name="post_media_items",
    )

    position = models.PositiveSmallIntegerField(
        default=0,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ("position", "id")
        constraints = [
            models.UniqueConstraint(
                fields=["post", "photo"],
                name="unique_photo_per_post",
            ),
        ]
        indexes = [
            models.Index(
                fields=["post", "position"],
                name="post_media_position_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"PostMedia #{self.pk}: post={self.post_id}, photo={self.photo_id}"
