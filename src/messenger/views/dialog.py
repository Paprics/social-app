# src/messenger/views/dialog.py

"""
HTTP views для работы с диалогами.

Модуль отвечает за:
- страницу списка диалогов;
- страницу открытого диалога;
- динамическую загрузку sidebar;
- постраничную подгрузку диалогов;
- удаление диалогов.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Page, Paginator
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

DIALOGS_PAGE_SIZE = 15


def _bind_current_user(dialogs, user) -> None:
    """
    Привязывает текущего пользователя к объектам Dialog.

    Используется свойствами Dialog.other_user
    и Dialog.current_participant.
    """

    for dialog in dialogs:
        dialog._current_user = user


def _get_dialogs_page(
    *,
    user,
    page_number,
) -> Page:
    """
    Возвращает одну страницу диалогов пользователя.

    Диалоги загружаются порциями по DIALOGS_PAGE_SIZE.
    Для каждого объекта устанавливается текущий пользователь.
    """

    paginator = Paginator(
        get_user_dialogs(user),
        DIALOGS_PAGE_SIZE,
    )

    page_obj = paginator.get_page(
        page_number,
    )

    _bind_current_user(
        page_obj.object_list,
        user,
    )

    return page_obj


class DialogListView(
    LoginRequiredMixin,
    ListView,
):
    """
    Отображает список диалогов пользователя.

    На первой загрузке возвращает только первую
    страницу диалогов.
    """

    template_name = "messenger/dialog_list.html"
    context_object_name = "dialogs"
    paginate_by = DIALOGS_PAGE_SIZE

    def get_queryset(self):
        """
        Возвращает queryset активных диалогов пользователя.
        """

        return get_user_dialogs(
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        """
        Формирует контекст страницы списка диалогов.
        """

        context = super().get_context_data(
            **kwargs,
        )

        _bind_current_user(
            context["dialogs"],
            self.request.user,
        )

        return context


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

        Sidebar получает только первую страницу
        диалогов пользователя.
        """

        context = super().get_context_data(
            **kwargs,
        )

        page_obj = _get_dialogs_page(
            user=self.request.user,
            page_number=1,
        )

        context["dialogs"] = page_obj.object_list
        context["page_obj"] = page_obj

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
    Возвращает полный HTML sidebar.

    Используется JavaScript-клиентом для обновления
    списка диалогов после событий messenger.
    """

    http_method_names = ["get"]

    def get(self, request):
        """
        Возвращает sidebar с первой страницей диалогов.
        """

        page_obj = _get_dialogs_page(
            user=request.user,
            page_number=1,
        )

        return TemplateResponse(
            request,
            "messenger/partials/sidebar.html",
            {
                "dialogs": page_obj.object_list,
                "page_obj": page_obj,
                "hide_sidebar_mobile": True,
            },
        )


class DialogSidebarPageView(
    LoginRequiredMixin,
    View,
):
    """
    Возвращает следующую страницу элементов sidebar.

    Используется HTMX для ленивой загрузки
    диалогов при прокрутке списка.
    """

    http_method_names = ["get"]

    def get(self, request):
        """
        Возвращает порцию диалогов для добавления
        в конец текущего списка.
        """

        page_obj = _get_dialogs_page(
            user=request.user,
            page_number=request.GET.get("page", 1),
        )

        return TemplateResponse(
            request,
            "messenger/partials/dialog_list_items.html",
            {
                "dialogs": page_obj.object_list,
                "page_obj": page_obj,
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
        Проверяет доступ пользователя
        и удаляет указанный диалог.
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
