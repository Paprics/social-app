# src/video_chat/services/rtc_config.py

"""Формирование WebRTC ICE-конфигурации для браузера."""

import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


def get_rtc_config() -> str:
    """Вернуть JSON-конфигурацию STUN/TURN серверов."""

    ice_servers = [
        {
            "urls": "stun:stun.l.google.com:19302",
        }
    ]

    turn_url = getattr(
        settings,
        "TURN_URL",
        None,
    )
    turn_user = getattr(
        settings,
        "TURN_USER",
        None,
    )
    turn_password = getattr(
        settings,
        "TURN_PASSWORD",
        None,
    )

    turn_credentials = (
        turn_url,
        turn_user,
        turn_password,
    )
    turn_is_complete = all(
        turn_credentials
    )

    if (
        getattr(
            settings,
            "VIDEO_CHAT_REQUIRE_TURN",
            False,
        )
        and not turn_is_complete
    ):
        raise ImproperlyConfigured(
            "Video chat requires TURN_URL, TURN_USER "
            "and TURN_PASSWORD in production."
        )

    if turn_is_complete:
        ice_servers.append(
            {
                "urls": turn_url,
                "username": turn_user,
                "credential": turn_password,
            }
        )

    return json.dumps(
        {
            "iceServers": ice_servers,
        }
    )
