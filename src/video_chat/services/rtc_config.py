# src/video_chat/services/rtc_config.py

"""Формирование WebRTC ICE-конфигурации для браузера."""

import json
import os


def get_rtc_config() -> str:
    """Вернуть JSON-конфигурацию STUN/TURN серверов."""

    ice_servers = [
        {
            "urls": "stun:stun.l.google.com:19302",
        }
    ]

    turn_url = os.environ.get("TURN_URL")
    turn_user = os.environ.get("TURN_USER")
    turn_password = os.environ.get("TURN_PASSWORD")

    if turn_url and turn_user and turn_password:
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
