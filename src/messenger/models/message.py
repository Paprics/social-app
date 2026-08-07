# src/messenger/models/message.py
from django.conf import settings
from django.db import models

from .dialog import Dialog


class MessageQuerySet(models.QuerySet):
    """Запросы для сообщений."""

    def visible(self):
        """Сообщения, доступные пользователям."""
        return self.filter(is_deleted=False)


class Message(models.Model):
    """Сообщение в диалоге."""

    dialog = models.ForeignKey(
        Dialog,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="Диалог",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
        verbose_name="Отправитель",
    )

    reply_to = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replies",
    )

    text = models.TextField(
        blank=True,
        verbose_name="Текст",
    )

    is_edited = models.BooleanField(
        default=False,
        verbose_name="Отредактировано",
    )

    edited_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Дата редактирования",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано",
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name="Обновлено",
    )

    objects = MessageQuerySet.as_manager()

    class Meta:
        ordering = ("id",)
        indexes = [
            models.Index(fields=["dialog", "id"]),
            models.Index(fields=["dialog", "created_at"]),
            models.Index(fields=["sender"]),
        ]
        verbose_name = "Сообщение"
        verbose_name_plural = "Сообщения"

    def __str__(self):
        return f"Message #{self.pk} ({self.sender})"
