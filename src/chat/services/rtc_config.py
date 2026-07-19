# chat/services/rtc_config.py
# Утилита для получения RTC_CONFIG из переменных окружения.
# Используется во views чтобы передать TURN настройки в шаблон.

import os
import json


def get_rtc_config() -> str:
    """Вернуть RTC_CONFIG как JSON строку для вставки в шаблон.

    В dev (localhost): только STUN Google.
    На проде: STUN + TURN из переменных окружения.

    Использование в view:
        context["rtc_config"] = get_rtc_config()

    Использование в шаблоне:
        const RTC_CONFIG = {{ rtc_config|safe }};
    """
    ice_servers = [
        {"urls": "stun:stun.l.google.com:19302"},
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

    return json.dumps({"iceServers": ice_servers})
