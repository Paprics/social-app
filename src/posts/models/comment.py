from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from gallery.models import Photo
from posts.models.post import Post


class Comment(models.Model):
    """
    Universal comment for supported content types.

    A comment belongs to exactly one target:
    - post;
    - photo;
    - video in the future.

    Replies support only one nesting level.
    """

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
    #
    # video = models.ForeignKey(
    #     Video,
    #     on_delete=models.CASCADE,
    #     related_name="comments",
    #     null=True,
    #     blank=True,
    # )
    #
    # IMPORTANT:
    # After adding video, update:
    # - clean()
    # - comment_exactly_one_target constraint
    # so a comment still belongs to exactly one target.

    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )

    content = models.CharField(
        max_length=100,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = (
            "created_at",
            "id",
        )

        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(post__isnull=False) & Q(photo__isnull=True)) | (Q(post__isnull=True) & Q(photo__isnull=False))
                ),
                name="comment_exactly_one_target",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "post",
                    "created_at",
                ],
                name="comment_post_created_idx",
            ),
            models.Index(
                fields=[
                    "photo",
                    "created_at",
                ],
                name="comment_photo_created_idx",
            ),
            models.Index(
                fields=[
                    "parent",
                    "created_at",
                ],
                name="comment_parent_created_idx",
            ),
        ]

    def clean(self):
        super().clean()

        targets_count = sum(
            target_id is not None
            for target_id in (
                self.post_id,
                self.photo_id,
            )
        )

        if targets_count != 1:
            raise ValidationError(
                "Comment must belong to exactly one target.",
            )

        if self.parent_id is None:
            return

        if self.pk and self.parent_id == self.pk:
            raise ValidationError(
                {
                    "parent": ("Comment cannot be a reply to itself."),
                },
            )

        parent = self.parent

        if parent.parent_id is not None:
            raise ValidationError(
                {
                    "parent": ("Only one level of comment replies is allowed."),
                },
            )

        if parent.post_id != self.post_id or parent.photo_id != self.photo_id:
            raise ValidationError(
                {
                    "parent": ("Reply must belong to the same target " "as its parent comment."),
                },
            )

    def __str__(self) -> str:
        return f"Comment #{self.pk}"
