# src/messenger/views/dialog.py

"""
HTTP views for dialogs.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.template.response import TemplateResponse
from django.views import View
from django.views.generic import DetailView, ListView

from messenger.models import Participant
from messenger.selectors.dialog import (
    get_dialog_by_public_id,
    get_dialog_with_messages,
    get_user_dialogs,
)
from messenger.services.dialog import DialogService
from messenger.services.dialog_page import DialogPageService
from messenger.services.read import ReadService


class DialogListView(
    LoginRequiredMixin,
    ListView,
):
    """
    Отображает список диалогов пользователя.
    """

    template_name = "messenger/dialog_list.html"
    context_object_name = "dialogs"

    def get_queryset(self):
        """
        Загружает диалоги текущего пользователя.
        """

        dialogs = get_user_dialogs(
            self.request.user,
        )

        for dialog in dialogs:
            dialog._current_user = self.request.user

        return dialogs


class DialogDetailView(
    LoginRequiredMixin,
    DetailView,
):
    """
    Отображает страницу одного диалога.
    """

    template_name = "messenger/dialog_detail.html"
    context_object_name = "dialog"

    def get_object(self, queryset=None):
        """
        Загружает диалог, проверяет доступ
        и отмечает текущие сообщения прочитанными.
        """

        dialog = get_dialog_with_messages(
            self.kwargs["public_id"],
        )

        if not DialogService.user_has_access(
            dialog.id,
            self.request.user.id,
        ):
            raise Http404()

        last_message = dialog.messages.last()

        if last_message:
            participant = Participant.objects.get(
                dialog=dialog,
                user=self.request.user,
            )

            ReadService.mark_as_read(
                participant,
                last_message,
            )

        return dialog

    def get_context_data(self, **kwargs):
        """
        Формирует контекст страницы диалога.
        """

        context = super().get_context_data(**kwargs)

        dialogs = get_user_dialogs(
            self.request.user,
        )

        for dialog in dialogs:
            dialog._current_user = self.request.user

        context["dialogs"] = dialogs

        context.update(
            DialogPageService.build(
                self.object,
                self.request,
            )
        )

        return context


class DialogSidebarView(
    LoginRequiredMixin,
    View,
):
    """
    Возвращает HTML списка диалогов.

    Используется для динамического
    обновления sidebar.
    """

    http_method_names = ["get"]

    def get(self, request):
        """
        Формирует и возвращает sidebar.
        """

        dialogs = get_user_dialogs(
            request.user,
        )

        for dialog in dialogs:
            dialog._current_user = request.user

        return TemplateResponse(
            request,
            "messenger/partials/sidebar.html",
            {
                "dialogs": dialogs,
            },
        )


class DialogDeleteView(
    LoginRequiredMixin,
    View,
):
    """
    Полностью удаляет диалог из базы данных.
    """

    http_method_names = ["post"]

    def post(
        self,
        request,
        public_id: str,
    ) -> HttpResponse:
        """
        Проверяет доступ и удаляет диалог.
        """

        try:
            dialog = get_dialog_by_public_id(
                public_id,
            )

        except Exception as error:
            raise Http404() from error

        try:
            DialogService.delete_dialog(
                dialog=dialog,
                user=request.user,
            )

        except PermissionError as error:
            raise Http404() from error

        return HttpResponse(
            status=204,
        )
