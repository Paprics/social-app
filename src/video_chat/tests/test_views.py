# src/video_chat/tests/test_views.py

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


@pytest.fixture
def regular_user(django_user_model):
    return django_user_model.objects.create_user(
        username="videochat_user",
        password="test-password",
    )


@pytest.fixture
def staff_user(django_user_model):
    return django_user_model.objects.create_user(
        username="videochat_staff",
        password="test-password",
        is_staff=True,
    )


def test_chat_view_returns_rtc_config(client, monkeypatch):
    rtc_config = '{"iceServers": [{"urls": "stun:test.example.com"}]}'
    monkeypatch.setattr("video_chat.views.get_rtc_config", lambda: rtc_config)

    response = client.get(reverse("chat:chat_view"))

    assert response.status_code == 200
    assert response.context["rtc_config"] == rtc_config
    assert "chat/room.html" in [template.name for template in response.templates]


def test_moderator_list_rejects_authenticated_non_staff(
    client,
    regular_user,
):
    client.force_login(regular_user)

    response = client.get(reverse("chat:moderator_list"))

    assert response.status_code == 403


def test_moderator_list_allows_staff_and_calculates_room_age(
    client,
    staff_user,
    monkeypatch,
):
    client.force_login(staff_user)

    monkeypatch.setattr(
        "video_chat.views.RoomStorage.list_rooms",
        lambda self: [
            {
                "room_id": "room-1",
                "caller": "caller-channel",
                "callee": "callee-channel",
                "created_at": 1000.0,
            }
        ],
    )
    monkeypatch.setattr("video_chat.views.time.time", lambda: 1120.0)

    response = client.get(reverse("chat:moderator_list"))

    assert response.status_code == 200
    assert response.context["rooms"][0]["age"] == "2м 0с"
    assert "chat/moderator_list.html" in [template.name for template in response.templates]


def test_moderator_list_returns_partial_for_htmx_request(
    client,
    staff_user,
    monkeypatch,
):
    client.force_login(staff_user)
    monkeypatch.setattr(
        "video_chat.views.RoomStorage.list_rooms",
        lambda self: [],
    )

    response = client.get(
        reverse("chat:moderator_list"),
        HTTP_HX_REQUEST="true",
    )

    assert response.status_code == 200

    template_names = [template.name for template in response.templates]

    assert "chat/partials/room_list.html" in template_names
    assert "chat/moderator_list.html" not in template_names


def test_moderator_room_redirects_when_room_does_not_exist(
    client,
    staff_user,
    monkeypatch,
):
    client.force_login(staff_user)

    monkeypatch.setattr(
        "video_chat.views.RoomStorage.get_room",
        lambda self, room_id: None,
    )

    response = client.get(
        reverse(
            "chat:moderator_room",
            kwargs={"room_id": "missing-room"},
        )
    )

    assert response.status_code == 302
    assert response.url == reverse("chat:moderator_list")


def test_moderator_room_renders_active_room(
    client,
    staff_user,
    monkeypatch,
):
    client.force_login(staff_user)

    monkeypatch.setattr(
        "video_chat.views.RoomStorage.get_room",
        lambda self, room_id: {
            "caller": "caller-channel",
            "callee": "callee-channel",
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
            kwargs={"room_id": "room-1"},
        )
    )

    assert response.status_code == 200
    assert response.context["room_id"] == "room-1"
    assert response.context["caller"] == "caller-channel"
    assert response.context["callee"] == "callee-channel"
    assert response.context["rtc_config"] == '{"iceServers": []}'

    assert "chat/moderator_room.html" in [template.name for template in response.templates]
