# src/video_chat/tests/test_rtc_config.py

import json

from video_chat.services.rtc_config import get_rtc_config

TURN_ENV_VARS = ("TURN_URL", "TURN_USER", "TURN_PASSWORD")


def clear_turn_env(monkeypatch):
    for name in TURN_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_rtc_config_contains_only_stun_without_turn_credentials(monkeypatch):
    clear_turn_env(monkeypatch)

    config = json.loads(get_rtc_config())

    assert config == {
        "iceServers": [
            {"urls": "stun:stun.l.google.com:19302"},
        ]
    }


def test_rtc_config_adds_turn_when_all_credentials_are_present(monkeypatch):
    monkeypatch.setenv("TURN_URL", "turn:turn.example.com:3478")
    monkeypatch.setenv("TURN_USER", "video-user")
    monkeypatch.setenv("TURN_PASSWORD", "video-password")

    config = json.loads(get_rtc_config())

    assert config == {
        "iceServers": [
            {"urls": "stun:stun.l.google.com:19302"},
            {
                "urls": "turn:turn.example.com:3478",
                "username": "video-user",
                "credential": "video-password",
            },
        ]
    }


def test_rtc_config_ignores_incomplete_turn_credentials(monkeypatch):
    clear_turn_env(monkeypatch)
    monkeypatch.setenv("TURN_URL", "turn:turn.example.com:3478")
    monkeypatch.setenv("TURN_USER", "video-user")

    config = json.loads(get_rtc_config())

    assert config == {
        "iceServers": [
            {"urls": "stun:stun.l.google.com:19302"},
        ]
    }
