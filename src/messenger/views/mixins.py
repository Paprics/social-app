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
