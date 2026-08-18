"""
Entry point for private conversations.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from messenger.forms.message import MessageForm
from messenger.selectors.dialog import get_private_dialog
from messenger.services.dialog import DialogService
from messenger.services.message import MessageService
from messenger.views.mixins import MessengerThreadLayoutMixin

User = get_user_model()


class ConversationView(
    MessengerThreadLayoutMixin,
    LoginRequiredMixin,
    TemplateView,
):
    """
    Точка входа в приватную переписку.

    Если диалог существует —
    открывает его.

    Если диалога нет —
    открывает пустую страницу создания.
    """

    template_name = "messenger/conversation_new.html"

    def dispatch(self, request, *args, **kwargs):

        self.target_user = get_object_or_404(
            User.objects.select_related("profile"),
            pk=self.kwargs["user_id"],
        )

        dialog = get_private_dialog(
            request.user,
            self.target_user,
        )

        if dialog:
            return redirect(
                "messenger:dialog_detail",
                public_id=dialog.public_id,
            )

        return super().dispatch(
            request,
            *args,
            **kwargs,
        )

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        context.update(
            {
                "dialog": None,
                "other_user": self.target_user,
                "messages": [],
            }
        )

        return context


class ConversationSendView(LoginRequiredMixin, View):
    """
    Создание первого сообщения.
    Создаёт диалог если его ещё нет.
    """

    def post(self, request, user_id):

        target_user = get_object_or_404(
            User,
            pk=user_id,
        )

        form = MessageForm(request.POST)

        if not form.is_valid():
            return HttpResponse(status=400)

        dialog = DialogService.get_or_create_private_dialog(
            request.user,
            target_user,
        )

        message = MessageService.create_message(
            dialog=dialog,
            sender=request.user,
            text=form.cleaned_data["text"],
        )

        return HttpResponse(
            status=204,
            headers={
                "HX-Redirect": reverse(
                    "messenger:dialog_detail",
                    kwargs={
                        "public_id": dialog.public_id,
                    },
                )
            },
        )
