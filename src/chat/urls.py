from django.urls import path
from chat.views import ChatView, ModeratorListView, ModeratorRoomView

app_name = "chat"

urlpatterns = [
    path("chat/", ChatView.as_view(), name="chat_view"),
    path("chat/moderate/", ModeratorListView.as_view(), name="moderator_list"),
    path(
        "chat/moderate/<str:room_id>/",
        ModeratorRoomView.as_view(),
        name="moderator_room",
    ),
]
