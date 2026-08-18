# src/video_chat/tests/test_views.py

"""HTTP regression tests страниц видеочата."""

import pytest
from django.urls import reverse

from users.models.profile import Profile

pytestmark = pytest.mark.django_db


@pytest.fixture
def regular_user(
    django_user_model,
):
    return django_user_model.objects.create_user(
        username="videochat_user",
        password="test-password",
    )


@pytest.fixture
def staff_user(
    django_user_model,
):
    return django_user_model.objects.create_user(
        username="videochat_staff",
        password="test-password",
        is_staff=True,
    )


def test_chat_view_returns_rtc_config_and_gender_choices(
    client,
    monkeypatch,
):
    rtc_config = (
        '{"iceServers": '
        '[{"urls": "stun:test.example.com"}]}'
    )

    monkeypatch.setattr(
        "video_chat.views.get_rtc_config",
        lambda: rtc_config,
    )

    response = client.get(
        reverse(
            "chat:chat_view"
        )
    )

    assert response.status_code == 200
    assert (
        response.context["rtc_config"]
        == rtc_config
    )
    assert list(
        response.context["gender_choices"]
    ) == list(
        Profile.Gender.choices
    )
    assert (
        "chat/room.html"
        in [
            template.name
            for template in response.templates
        ]
    )


def test_moderator_list_rejects_authenticated_non_staff(
    client,
    regular_user,
):
    client.force_login(
        regular_user
    )

    response = client.get(
        reverse(
            "chat:moderator_list"
        )
    )

    assert response.status_code == 403


def test_moderator_list_exposes_participant_identity_for_staff(
    client,
    staff_user,
    regular_user,
    monkeypatch,
):
    client.force_login(
        staff_user
    )

    monkeypatch.setattr(
        "video_chat.views.RoomStorage.list_rooms",
        lambda self: [
            {
                "room_id": "room-1",
                "caller": "caller-channel",
                "callee": "callee-channel",
                "caller_participant": {
                    "user_id": regular_user.pk,
                    "username": regular_user.username,
                    "is_authenticated": True,
                    "profile_gender": "male",
                    "chat_gender": "couple",
                },
                "callee_participant": {
                    "user_id": None,
                    "username": "",
                    "is_authenticated": False,
                    "profile_gender": "",
                    "chat_gender": "female",
                },
                "created_at": 1000.0,
            }
        ],
    )
    monkeypatch.setattr(
        "video_chat.views.time.time",
        lambda: 1120.0,
    )

    response = client.get(
        reverse(
            "chat:moderator_list"
        )
    )

    room = (
        response.context["rooms"][0]
    )

    assert response.status_code == 200
    assert room["age"] == "2м 0с"

    caller = room[
        "caller_participant"
    ]
    callee = room[
        "callee_participant"
    ]

    assert (
        caller["username"]
        == regular_user.username
    )
    assert (
        caller["profile_url"]
        == reverse(
            "users:profile",
            args=[regular_user.pk],
        )
    )
    assert (
        str(
            caller[
                "profile_gender_label"
            ]
        )
        == str(
            Profile.Gender.MALE.label
        )
    )
    assert (
        str(
            caller[
                "chat_gender_label"
            ]
        )
        == str(
            Profile.Gender.COUPLE.label
        )
    )

    assert (
        callee["is_authenticated"]
        is False
    )
    assert (
        str(
            callee[
                "chat_gender_label"
            ]
        )
        == str(
            Profile.Gender.FEMALE.label
        )
    )


def test_moderator_list_returns_partial_for_htmx_request(
    client,
    staff_user,
    monkeypatch,
):
    client.force_login(
        staff_user
    )
    monkeypatch.setattr(
        "video_chat.views.RoomStorage.list_rooms",
        lambda self: [],
    )

    response = client.get(
        reverse(
            "chat:moderator_list"
        ),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200

    template_names = [
        template.name
        for template in response.templates
    ]

    assert (
        "chat/partials/room_list.html"
        in template_names
    )
    assert (
        "chat/moderator_list.html"
        not in template_names
    )


def test_moderator_room_redirects_when_room_does_not_exist(
    client,
    staff_user,
    monkeypatch,
):
    client.force_login(
        staff_user
    )

    monkeypatch.setattr(
        "video_chat.views.RoomStorage.get_room",
        lambda self, room_id: None,
    )

    response = client.get(
        reverse(
            "chat:moderator_room",
            kwargs={
                "room_id": "missing-room",
            },
        )
    )

    assert response.status_code == 302
    assert response.url == reverse(
        "chat:moderator_list"
    )


def test_moderator_room_renders_active_room(
    client,
    staff_user,
    regular_user,
    monkeypatch,
):
    client.force_login(
        staff_user
    )

    monkeypatch.setattr(
        "video_chat.views.RoomStorage.get_room",
        lambda self, room_id: {
            "caller": "caller-channel",
            "callee": "callee-channel",
            "caller_participant": {
                "user_id": regular_user.pk,
                "username": regular_user.username,
                "is_authenticated": True,
                "profile_gender": "male",
                "chat_gender": "couple",
            },
            "callee_participant": {
                "user_id": None,
                "username": "",
                "is_authenticated": False,
                "profile_gender": "",
                "chat_gender": "female",
            },
            "created_at": 1000.0,
        },
    )
    monkeypatch.setattr(
        "video_chat.views.get_rtc_config",
        lambda: '{"iceServers": []}',
    )

    response = client.get(
        reverse(
            "chat:moderator_room",
            kwargs={
                "room_id": "room-1",
            },
        )
    )

    assert response.status_code == 200
    assert (
        response.context["room_id"]
        == "room-1"
    )
    assert (
        response.context["caller"]
        == "caller-channel"
    )
    assert (
        response.context["callee"]
        == "callee-channel"
    )
    assert (
        response.context["rtc_config"]
        == '{"iceServers": []}'
    )
    assert (
        response.context["room"][
            "caller_participant"
        ]["profile_url"]
        == reverse(
            "users:profile",
            args=[regular_user.pk],
        )
    )

    assert (
        "chat/moderator_room.html"
        in [
            template.name
            for template in response.templates
        ]
    )
