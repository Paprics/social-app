"""
views.py — Django views для чата и панели модератора.

Маршруты:
    /chat/                      → ChatView
    /chat/moderate/             → ModeratorListView
    /chat/moderate/{room_id}/   → ModeratorRoomView
"""

import time

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, render
from django.views.generic import View

from chat.services.room_storage import RoomStorage
from chat.services.rtc_config import get_rtc_config


class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class ChatView(View):
    """Главная страница видеочата.

    Передаём RTC_CONFIG в шаблон — там STUN и (на проде) TURN сервер.
    Вся логика на фронте через WebSocket и WebRTC.
    """

    def get(self, request):
        # get_rtc_config() читает TURN_URL/TURN_USER/TURN_PASSWORD из env.
        # На локалке эти переменные не заданы — вернёт только STUN.
        # На проде — вернёт STUN + TURN автоматически.
        return render(
            request,
            "chat/room.html",
            {
                "rtc_config": get_rtc_config(),
            },
        )


class ModeratorListView(StaffRequiredMixin, View):
    """Список активных комнат для модератора с HTMX polling каждые 5с."""

    def get(self, request):
        storage = RoomStorage()
        rooms = storage.list_rooms()

        now = time.time()
        for room in rooms:
            age_seconds = int(now - room.get("created_at", now))
            minutes, seconds = divmod(age_seconds, 60)
            room["age"] = f"{minutes}м {seconds}с"

        if request.headers.get("HX-Request"):
            return render(request, "chat/partials/room_list.html", {"rooms": rooms})

        return render(request, "chat/moderator_list.html", {"rooms": rooms})


class ModeratorRoomView(StaffRequiredMixin, View):
    """Страница просмотра комнаты модератором."""

    def get(self, request, room_id):
        storage = RoomStorage()
        room = storage.get_room(room_id)

        if not room:
            return redirect("chat:moderator_list")

        return render(
            request,
            "chat/moderator_room.html",
            {
                "room_id": room_id,
                "caller": room["caller"],
                "callee": room["callee"],
                "rtc_config": get_rtc_config(),
            },
        )
