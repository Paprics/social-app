# src/messenger/views/dialog.py

"""
HTTP views для работы с диалогами.

Модуль отвечает за:
- страницу списка диалогов;
- страницу открытого диалога;
- динамическую загрузку sidebar;
- постраничную подгрузку диалогов;
- ленивую загрузку истории сообщений;
- отметку сообщений прочитанными;
- удаление диалогов.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Page, Paginator
from django.http import Http404, HttpResponse
from django.template.response import TemplateResponse
from django.views import View
from django.views.generic import DetailView, ListView

from messenger.models import Dialog, Message, Participant
from messenger.selectors.dialog import (
    get_dialog_by_public_id,
    get_user_dialogs,
)
from messenger.selectors.message import (
    MESSAGE_BATCH_SIZE,
    get_messages_before,
    has_messages_before,
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
        """Возвращает queryset активных диалогов пользователя."""

        return get_user_dialogs(
            self.request.user,
        )

    def get_context_data(self, **kwargs):
        """Формирует контекст страницы списка диалогов."""

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
    """Отображает страницу одного диалога."""

    template_name = "messenger/dialog_detail.html"
    context_object_name = "dialog"

    def get_object(self, queryset=None):
        """
        Загружает диалог, проверяет доступ
        и отмечает текущие сообщения прочитанными.
        """

        dialog = get_dialog_by_public_id(
            self.kwargs["public_id"],
        )

        if not DialogService.user_has_access(
            dialog.id,
            self.request.user.id,
        ):
            raise Http404()

        dialog._current_user = self.request.user

        last_message = dialog.messages.order_by("-id").first()

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
        """Возвращает sidebar с первой страницей диалогов."""

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


class DialogMarkReadView(
    LoginRequiredMixin,
    View,
):
    """
    Отмечает входящее сообщение прочитанным.

    Используется, когда сообщение приходит
    в уже открытый диалог без перезагрузки страницы.
    """

    http_method_names = ["post"]

    def post(
        self,
        request,
        public_id: str,
    ) -> HttpResponse:
        """Продвигает read cursor текущего участника."""

        try:
            dialog = get_dialog_by_public_id(
                public_id,
            )
        except Dialog.DoesNotExist as error:
            raise Http404() from error

        if not DialogService.user_has_access(
            dialog.id,
            request.user.id,
        ):
            raise Http404()

        try:
            message_id = int(
                request.POST["message_id"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise Http404() from error

        try:
            message = Message.objects.get(
                pk=message_id,
                dialog_id=dialog.id,
            )
        except Message.DoesNotExist as error:
            raise Http404() from error

        # Собственные сообщения не являются входящими
        # и не должны двигать read cursor пользователя.
        if message.sender_id == request.user.id:
            return HttpResponse(
                status=204,
            )

        try:
            participant = Participant.objects.get(
                dialog_id=dialog.id,
                user_id=request.user.id,
                is_active=True,
            )
        except Participant.DoesNotExist as error:
            raise Http404() from error

        ReadService.mark_as_read(
            participant,
            message,
        )

        return HttpResponse(
            status=204,
        )


class DialogMessagesBeforeView(
    LoginRequiredMixin,
    View,
):
    """
    Возвращает предыдущую порцию сообщений диалога.

    Использует cursor pagination по ID самого старого
    сообщения, уже загруженного клиентом.
    """

    http_method_names = ["get"]

    def get(
        self,
        request,
        public_id: str,
    ) -> TemplateResponse:
        """Возвращает сообщения старше переданного cursor."""

        try:
            dialog = get_dialog_by_public_id(
                public_id,
            )
        except Dialog.DoesNotExist as error:
            raise Http404() from error

        if not DialogService.user_has_access(
            dialog.id,
            request.user.id,
        ):
            raise Http404()

        dialog._current_user = request.user

        try:
            before_message_id = int(
                request.GET["before"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise Http404() from error

        if before_message_id <= 0:
            raise Http404()

        messages = get_messages_before(
            dialog.id,
            before_message_id,
            limit=MESSAGE_BATCH_SIZE,
        )

        oldest_message_id = messages[0].id if messages else None

        has_more = (
            has_messages_before(
                dialog.id,
                oldest_message_id,
            )
            if oldest_message_id
            else False
        )

        response = TemplateResponse(
            request,
            "messenger/partials/dialog/message_batch.html",
            {
                "dialog": dialog,
                "messages": messages,
            },
        )

        response.headers["X-Messenger-Has-More"] = "1" if has_more else "0"

        response.headers["X-Messenger-Oldest-Id"] = str(oldest_message_id) if oldest_message_id else ""

        return response


class DialogDeleteView(
    LoginRequiredMixin,
    View,
):
    """Полностью удаляет диалог из базы данных."""

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
