# src/notifications/models.py

"""Notification models."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from gallery.models import Photo
from posts.models import Comment


class Notification(models.Model):
    """Activity notification addressed to a user."""

    class Kind(models.TextChoices):
        PHOTO_LIKE = "photo_like", _("Photo like")
        PHOTO_COMMENT = "photo_comment", _("Photo comment")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Recipient"),
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_notifications",
        verbose_name=_("Actor"),
    )

    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        db_index=True,
        verbose_name=_("Type"),
    )

    photo = models.ForeignKey(
        Photo,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("Photo"),
    )

    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("Comment"),
    )

    is_read = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name=_("Read"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created"),
    )

    last_triggered_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=_("Last triggered"),
    )

    class Meta:
        ordering = [
            "-last_triggered_at",
            "-pk",
        ]

        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")

        indexes = [
            models.Index(
                fields=[
                    "recipient",
                    "is_read",
                    "kind",
                ],
                name="notif_rec_read_kind_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(~Q(kind="photo_like") | Q(photo__isnull=False)),
                name="photo_like_requires_photo",
            ),
            models.CheckConstraint(
                condition=(~Q(kind="photo_like") | ~Q(recipient=F("actor"))),
                name="photo_like_actor_not_recipient",
            ),
            models.UniqueConstraint(
                fields=[
                    "recipient",
                    "actor",
                    "kind",
                    "photo",
                ],
                condition=Q(kind="photo_like"),
                name="unique_photo_like_notification",
            ),
            models.CheckConstraint(
                condition=(~Q(kind="photo_comment") | (Q(photo__isnull=False) & Q(comment__isnull=False))),
                name="photo_comment_requires_photo_comment",
            ),
            models.CheckConstraint(
                condition=(~Q(kind="photo_comment") | ~Q(recipient=F("actor"))),
                name="photo_comment_actor_not_recipient",
            ),
            models.UniqueConstraint(
                fields=[
                    "recipient",
                    "actor",
                    "kind",
                    "comment",
                ],
                condition=Q(kind="photo_comment"),
                name="unique_photo_comment_notification",
            ),
        ]

    def __str__(self):
        return f"{self.kind}: " f"{self.actor_id} -> {self.recipient_id}"
