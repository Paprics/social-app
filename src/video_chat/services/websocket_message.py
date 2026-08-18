# src/video_chat/services/websocket_message.py

"""Валидация входящих WebSocket JSON-сообщений видеочата."""

import json

MAX_WEBSOCKET_MESSAGE_BYTES = 65536


class InvalidWebSocketMessage(ValueError):
    """Сообщение не является допустимым JSON-object."""


class WebSocketMessageTooLarge(ValueError):
    """WebSocket message превышает допустимый размер."""


def decode_websocket_message(
    text_data: str | None,
) -> dict:
    """Декодировать и проверить входящий WebSocket JSON-object."""

    if not isinstance(text_data, str):
        raise InvalidWebSocketMessage

    if (
        len(
            text_data.encode("utf-8")
        )
        > MAX_WEBSOCKET_MESSAGE_BYTES
    ):
        raise WebSocketMessageTooLarge

    try:
        data = json.loads(
            text_data
        )
    except json.JSONDecodeError as exc:
        raise InvalidWebSocketMessage from exc

    if not isinstance(data, dict):
        raise InvalidWebSocketMessage

    return data
