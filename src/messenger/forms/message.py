# src/messenger/forms/message.py

"""
Формы для работы с сообщениями.

Используются только для валидации входящих данных.
HTML полностью описывается в шаблонах.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from messenger.constants import MAX_MESSAGE_LENGTH


class MessageForm(forms.Form):
    """
    Форма валидации сообщения.
    """

    text = forms.CharField(
        required=False,
        max_length=MAX_MESSAGE_LENGTH,
        strip=True,
    )

    def clean(self):
        """
        Проверяет корректность сообщения.

        Сообщение должно содержать текст
        или хотя бы одно вложение.
        """

        cleaned_data = super().clean()

        text = cleaned_data.get("text", "").strip()

        # Позже здесь будет проверка attachments.
        if not text:
            raise forms.ValidationError(
                _("Message cannot be empty."),
            )

        cleaned_data["text"] = text

        return cleaned_data
