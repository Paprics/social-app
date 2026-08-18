# src/messenger/views/message.py
"""
HTTP views для работы с сообщениями.

View отвечает только за:
- получение HTTP-запроса;
- валидацию формы;
- вызов сервисов;
- возврат HTML.

Вся бизнес-логика находится в services.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views import View

from messenger.forms.message import MessageForm
from messenger.selectors.dialog import get_dialog_by_public_id
from messenger.selectors.message import get_message
from messenger.services.dialog import DialogService
from messenger.services.message import MessageService
from messenger.views.mixins import DialogAccessMixin


class MessageCreateView(LoginRequiredMixin, View):
    """Создает новое сообщение."""

    http_method_names = ["post"]

    def post(self, request, public_id: str) -> HttpResponse:
        """Создает сообщение в диалоге."""

        dialog = get_dialog_by_public_id(public_id)

        if not DialogService.user_has_access(
            dialog.id,
            request.user.id,
        ):
            raise Http404()

        form = MessageForm(request.POST)

        if not form.is_valid():
            return render(
                request,
                "messenger/partials/dialog/message_form.html",
                {
                    "dialog": dialog,
                    "form": form,
                },
                status=400,
            )

        message = MessageService.create_message(
            dialog=dialog,
            sender=request.user,
            text=form.cleaned_data["text"],
        )

        return HttpResponse(status=204)


class MessageItemView(
    LoginRequiredMixin,
    DialogAccessMixin,
    View,
):
    """Возвращает read-only HTML одного сообщения."""

    http_method_names = ["get"]

    def get(
        self,
        request,
        message_id: int,
    ) -> HttpResponse:
        """Получает сообщение и возвращает partial без DB side effects."""

        message = get_message(message_id)

        self.check_dialog_access(
            message.dialog_id,
            request.user.id,
        )

        # Временная compatibility-привязка для outgoing.html.
        # Удаляется вместе с Dialog._current_user при переходе на DTO.
        dialog = message.dialog
        dialog._current_user = request.user

        return render(
            request,
            "messenger/partials/dialog/message_item.html",
            {
                "dialog": dialog,
                "message": message,
                "current_user": request.user,
            },
        )


class MessageDeleteView(LoginRequiredMixin, DialogAccessMixin, View):
    http_method_names = ["post"]

    def post(
        self,
        request,
        message_id: int,
    ):
        message = get_message(message_id)

        self.check_dialog_access(
            message.dialog_id,
            request.user.id,
        )

        if message.sender_id != request.user.id:
            raise Http404()

        dialog_id = message.dialog_id

        deleted_message_id = MessageService.delete_message(
            message=message,
        )

        return HttpResponse(status=204)
