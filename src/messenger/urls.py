# src/messenger/urls.py

"""
URL configuration для messenger.

Модуль содержит маршруты страниц диалогов,
сообщений и вспомогательных HTMX endpoints.
"""

from django.urls import path

from messenger.views.actions import StartPrivateDialogView
from messenger.views.conversation import (
    ConversationSendView,
    ConversationView,
)
from messenger.views.dialog import (
    DialogDeleteView,
    DialogDetailView,
    DialogListView,
    DialogMessagesBeforeView,
    DialogSidebarPageView,
    DialogSidebarView,
)
from messenger.views.message import (
    MessageCreateView,
    MessageDeleteView,
    MessageItemView,
)

app_name = "messenger"


urlpatterns = [
    path(
        "",
        DialogListView.as_view(),
        name="dialog_list",
    ),
    path(
        "sidebar/",
        DialogSidebarView.as_view(),
        name="sidebar",
    ),
    path(
        "sidebar/page/",
        DialogSidebarPageView.as_view(),
        name="sidebar_page",
    ),
    path(
        "messages/<int:message_id>/delete/",
        MessageDeleteView.as_view(),
        name="message_delete",
    ),
    path(
        "messages/<int:message_id>/",
        MessageItemView.as_view(),
        name="message_item",
    ),
    path(
        "start/<int:user_id>/",
        StartPrivateDialogView.as_view(),
        name="dialog_start",
    ),
    path(
        "conversation/<int:user_id>/",
        ConversationView.as_view(),
        name="conversation",
    ),
    path(
        "conversation/<int:user_id>/send/",
        ConversationSendView.as_view(),
        name="conversation_send",
    ),
    path(
        "<str:public_id>/delete/",
        DialogDeleteView.as_view(),
        name="dialog_delete",
    ),
    path(
        "<str:public_id>/messages/older/",
        DialogMessagesBeforeView.as_view(),
        name="dialog_messages_older",
    ),
    path(
        "<str:public_id>/messages/create/",
        MessageCreateView.as_view(),
        name="message_create",
    ),
    path(
        "<str:public_id>/",
        DialogDetailView.as_view(),
        name="dialog_detail",
    ),
]
