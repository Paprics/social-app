# src/video_chat/tests/test_rtc_config.py

import json

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from video_chat.services.rtc_config import get_rtc_config


@override_settings(
    TURN_URL=None,
    TURN_USER=None,
    TURN_PASSWORD=None,
    VIDEO_CHAT_REQUIRE_TURN=False,
)
def test_rtc_config_contains_only_stun_without_turn_credentials():
    config = json.loads(
        get_rtc_config()
    )

    assert config == {
        "iceServers": [
            {
                "urls": "stun:stun.l.google.com:19302",
            },
        ]
    }


@override_settings(
    TURN_URL="turn:turn.example.com:3478",
    TURN_USER="video-user",
    TURN_PASSWORD="video-password",
    VIDEO_CHAT_REQUIRE_TURN=False,
)
def test_rtc_config_adds_turn_when_all_credentials_are_present():
    config = json.loads(
        get_rtc_config()
    )

    assert config == {
        "iceServers": [
            {
                "urls": "stun:stun.l.google.com:19302",
            },
            {
                "urls": "turn:turn.example.com:3478",
                "username": "video-user",
                "credential": "video-password",
            },
        ]
    }


@override_settings(
    TURN_URL="turn:turn.example.com:3478",
    TURN_USER="video-user",
    TURN_PASSWORD=None,
    VIDEO_CHAT_REQUIRE_TURN=False,
)
def test_rtc_config_ignores_incomplete_turn_credentials():
    config = json.loads(
        get_rtc_config()
    )

    assert config == {
        "iceServers": [
            {
                "urls": "stun:stun.l.google.com:19302",
            },
        ]
    }


@override_settings(
    TURN_URL=None,
    TURN_USER=None,
    TURN_PASSWORD=None,
    VIDEO_CHAT_REQUIRE_TURN=True,
)
def test_rtc_config_requires_turn_when_enabled():
    with pytest.raises(
        ImproperlyConfigured,
        match="requires TURN_URL",
    ):
        get_rtc_config()


@override_settings(
    TURN_URL="turn:turn.example.com:3478",
    TURN_USER="video-user",
    TURN_PASSWORD="video-password",
    VIDEO_CHAT_REQUIRE_TURN=True,
)
def test_rtc_config_accepts_complete_turn_when_required():
    config = json.loads(
        get_rtc_config()
    )

    assert len(
        config["iceServers"]
    ) == 2
