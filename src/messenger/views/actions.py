# src/messenger/views/actions.py

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib.auth import get_user_model

from messenger.services.dialog import DialogService

User = get_user_model()


class StartPrivateDialogView(LoginRequiredMixin, View):
    """
    Создает личный диалог или возвращает существующий.
    """

    def get(self, request, user_id):
        target_user = get_object_or_404(
            User,
            pk=user_id,
        )

        dialog = DialogService.get_or_create_private_dialog(
            request.user,
            target_user,
        )

        return redirect(
            "messenger:dialog_detail",
            dialog_id=dialog.pk,
        )
