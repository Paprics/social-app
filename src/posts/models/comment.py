from django.conf import settings
from django.db import models

from posts.models.post import Post
from users.models.gallery import Photo


class Comment(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True,
    )

    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        related_name="comments",
        null=True,
        blank=True,
    )

    # Future extension:
    # video = models.ForeignKey(
    #     Video,
    #     on_delete=models.CASCADE,
    #     related_name="comments",
    #     null=True,
    #     blank=True,
    # )

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )

    content = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ("created_at",)

    def __str__(self) -> str:
        return f"Comment #{self.pk}"
