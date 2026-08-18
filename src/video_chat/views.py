# src/video_chat/views.py

"""HTTP views основной страницы и staff-панели видеочата."""

import time

from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic import View

from users.models.profile import Profile
from video_chat.services.room_storage import RoomStorage
from video_chat.services.rtc_config import get_rtc_config


def _decorate_participant(metadata: dict | None) -> dict:
    """Подготовить Redis metadata участника для отображения staff-пользователю."""

    participant = dict(metadata or {})
    gender_labels = dict(Profile.Gender.choices)

    user_id = participant.get("user_id")
    profile_gender = participant.get("profile_gender", "")
    chat_gender = participant.get("chat_gender", "")

    participant["is_authenticated"] = bool(
        participant.get("is_authenticated")
        and user_id
    )
    participant["username"] = (
        participant.get("username")
        or ""
    )
    participant["profile_gender_label"] = (
        gender_labels.get(
            profile_gender,
            profile_gender,
        )
        if profile_gender
        else ""
    )
    participant["chat_gender_label"] = (
        gender_labels.get(
            chat_gender,
            chat_gender,
        )
        if chat_gender
        else ""
    )
    participant["profile_url"] = (
        reverse(
            "users:profile",
            args=[user_id],
        )
        if user_id
        else None
    )

    return participant


def _decorate_room(room: dict) -> dict:
    """Добавить display metadata caller/callee без изменения Redis."""

    decorated = dict(room)
    decorated["caller_participant"] = _decorate_participant(
        room.get("caller_participant")
    )
    decorated["callee_participant"] = _decorate_participant(
        room.get("callee_participant")
    )
    return decorated


class StaffRequiredMixin(
    LoginRequiredMixin,
    UserPassesTestMixin,
):
    """Ограничить HTTP staff-пользователями."""

    def test_func(self):
        return self.request.user.is_staff


class ChatView(View):
    """Показать страницу случайного видеочата."""

    def get(self, request):
        return render(
            request,
            "chat/room.html",
            {
                "rtc_config": get_rtc_config(),
                "gender_choices": Profile.Gender.choices,
            },
        )


class ModeratorListView(
    StaffRequiredMixin,
    View,
):
    """Показать список активных комнат для staff."""

    def get(self, request):
        storage = RoomStorage()
        rooms = []

        now = time.time()

        for room in storage.list_rooms():
            room = _decorate_room(
                room
            )

            age_seconds = int(
                now
                - room.get(
                    "created_at",
                    now,
                )
            )
            minutes, seconds = divmod(
                age_seconds,
                60,
            )
            room["age"] = (
                f"{minutes}м {seconds}с"
            )
            rooms.append(room)

        context = {
            "rooms": rooms,
        }

        if request.headers.get(
            "HX-Request"
        ):
            return render(
                request,
                "chat/partials/room_list.html",
                context,
            )

        return render(
            request,
            "chat/moderator_list.html",
            context,
        )


class ModeratorRoomView(
    StaffRequiredMixin,
    View,
):
    """Показать staff-модератору одну активную комнату."""

    def get(
        self,
        request,
        room_id,
    ):
        storage = RoomStorage()
        room = storage.get_room(
            room_id
        )

        if not room:
            return redirect(
                "chat:moderator_list"
            )

        room = _decorate_room(
            room
        )

        return render(
            request,
            "chat/moderator_room.html",
            {
                "room_id": room_id,
                "caller": room["caller"],
                "callee": room["callee"],
                "room": room,
                "rtc_config": get_rtc_config(),
            },
        )
