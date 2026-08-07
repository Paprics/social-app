from django.db import models

from .message import Message


class Attachment(models.Model):
    """Файл, прикрепленный к сообщению."""

    class AttachmentType(models.TextChoices):
        IMAGE = "image", "Изображение"
        VIDEO = "video", "Видео"
        FILE = "file", "Файл"
        AUDIO = "audio", "Аудио"

    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Сообщение",
    )

    file = models.FileField(
        upload_to="messenger/attachments/%Y/%m/",
        verbose_name="Файл",
    )

    attachment_type = models.CharField(
        max_length=20,
        choices=AttachmentType.choices,
        verbose_name="Тип",
    )

    original_name = models.CharField(
        max_length=255,
        verbose_name="Исходное имя файла",
    )

    file_size = models.PositiveBigIntegerField(
        verbose_name="Размер файла (байт)",
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="MIME-тип",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Создано",
    )

    class Meta:
        ordering = ("id",)
        indexes = [
            models.Index(fields=["message"]),
            models.Index(fields=["attachment_type"]),
        ]
        verbose_name = "Вложение"
        verbose_name_plural = "Вложения"

    def __str__(self):
        return self.original_name
