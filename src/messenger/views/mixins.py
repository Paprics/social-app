# src/messenger/views/mixins.py

"""
Общие mixin-классы для messenger views.
"""

from django.http import Http404

from messenger.services.dialog import DialogService


class DialogAccessMixin:
    """
    Проверяет доступ пользователя к диалогу.
    """

    @staticmethod
    def check_dialog_access(dialog_id: int, user_id: int) -> None:
        """
        Проверяет доступ пользователя.

        Если доступа нет — возбуждает Http404.
        """

        if not DialogService.user_has_access(
            dialog_id,
            user_id,
        ):
            raise Http404()


class MessengerThreadLayoutMixin:
    """Marks pages that should display the conversation panel on mobile."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["messenger_thread_active"] = True
        return context
