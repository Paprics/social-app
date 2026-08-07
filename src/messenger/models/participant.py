# src/messenger/models/participant.py
from django.conf import settings
from django.db import models

from .dialog import Dialog
from .message import Message


class ParticipantQuerySet(models.QuerySet):
    """Запросы для участников диалогов."""

    def active(self):
        """Только активные участники."""
        return self.filter(is_active=True)


class Participant(models.Model):
    """Участник диалога."""

    dialog = models.ForeignKey(
        Dialog,
        on_delete=models.CASCADE,
        related_name="participants",
        verbose_name="Диалог",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dialog_participations",
        verbose_name="Пользователь",
    )

    # Последнее прочитанное сообщение.
    last_read_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Последнее прочитанное сообщение",
    )

    # Пользователь скрыл диалог из списка.
    is_archived = models.BooleanField(
        default=False,
        verbose_name="Архивирован",
    )

    # Пользователь отключил уведомления.
    is_muted = models.BooleanField(
        default=False,
        verbose_name="Без уведомлений",
    )

    # Участник еще состоит в диалоге.
    is_active = models.BooleanField(
        default=True,
        verbose_name="Активен",
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата вступления",
    )

    objects = ParticipantQuerySet.as_manager()

    @property
    def unread_count(self):
        """
        Количество непрочитанных входящих сообщений.
        """

        queryset = self.dialog.messages.exclude(
            sender_id=self.user_id,
        )

        if self.last_read_message_id:
            queryset = queryset.filter(
                id__gt=self.last_read_message_id,
            )

        return queryset.count()

    class Meta:
        ordering = ("id",)
        constraints = [
            models.UniqueConstraint(
                fields=["dialog", "user"],
                name="unique_dialog_participant",
            ),
        ]
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["dialog"]),
        ]
        verbose_name = "Участник диалога"
        verbose_name_plural = "Участники диалогов"

    def __str__(self):
        return f"{self.user} → Dialog #{self.dialog_id}"
