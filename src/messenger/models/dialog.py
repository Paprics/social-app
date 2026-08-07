# src/messenger/models/dialog.py
"""
Модель диалога.

Диалог объединяет участников и сообщения.
Поддерживает как личные, так и групповые чаты.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
import uuid


def generate_public_id():
    return uuid.uuid4().hex[:16]


class DialogType(models.TextChoices):
    """Тип диалога."""

    PRIVATE = "private", _("Private")
    GROUP = "group", _("Group")


class Dialog(models.Model):
    """Диалог между двумя или несколькими пользователями."""

    public_id = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
        db_index=True,
        default=generate_public_id,
        verbose_name="Public ID",
    )

    # Тип диалога.
    dialog_type = models.CharField(
        max_length=20,
        choices=DialogType.choices,
        default=DialogType.PRIVATE,
        db_index=True,
        verbose_name=_("Dialog type"),
    )

    # Заголовок используется только для групповых чатов.
    title = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_("Title"),
    )

    # Владелец (создатель) диалога.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_dialogs",
        verbose_name=_("Owner"),
    )

    # Последнее сообщение.
    # Позволяет быстро сортировать список диалогов.
    last_message = models.ForeignKey(
        "messenger.Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name=_("Last message"),
    )

    # Время последней активности.
    last_activity_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name=_("Last activity"),
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created"),
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated"),
    )

    class Meta:
        verbose_name = _("Dialog")
        verbose_name_plural = _("Dialogs")

        ordering = ("-last_activity_at",)

        indexes = [
            models.Index(fields=["dialog_type"]),
            models.Index(fields=["-last_activity_at"]),
        ]

    def __str__(self) -> str:
        if self.dialog_type == DialogType.PRIVATE:
            return f"Private dialog #{self.pk}"

        return self.title or f"Group dialog #{self.pk}"

    @property
    def is_private(self) -> bool:
        """Является ли диалог личным."""

        return self.dialog_type == DialogType.PRIVATE

    @property
    def is_group(self) -> bool:
        """Является ли диалог групповым."""

        return self.dialog_type == DialogType.GROUP

    @property
    def other_user(self):
        """
        Возвращает второго участника личного диалога.

        Работает только если participants уже были
        загружены через prefetch_related().
        """
        if hasattr(self, "_current_user"):
            for participant in self.participants.all():
                if participant.user_id != self._current_user.id:
                    return participant.user

        return None

    @property
    def current_participant(self):
        if hasattr(self, "_current_user"):
            for participant in self.participants.all():
                if participant.user_id == self._current_user.id:
                    return participant

        return None
