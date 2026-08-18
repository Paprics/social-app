# src/video_chat/services/room_storage.py

"""Хранение активных комнат видеочата в Redis."""

import json
import os
import time

import redis as redis_lib

ROOMS_KEY = "chat:rooms"
ROOM_TTL = 7200


class RoomStorage:
    """Управляет метаданными активных видеочат-комнат в Redis."""

    def __init__(self):
        self.redis = redis_lib.from_url(
            os.environ.get(
                "REDIS_URL",
                "redis://localhost:6379/0",
            )
        )

    def create_room(
        self,
        room_id: str,
        caller_channel: str,
        callee_channel: str,
        *,
        caller_participant: dict | None = None,
        callee_participant: dict | None = None,
    ) -> None:
        """Сохранить комнату вместе со snapshot metadata участников."""

        meta = json.dumps(
            {
                "caller": caller_channel,
                "callee": callee_channel,
                "caller_participant": caller_participant or {},
                "callee_participant": callee_participant or {},
                "created_at": time.time(),
            }
        )

        self.redis.hset(
            ROOMS_KEY,
            room_id,
            meta,
        )
        self.redis.expire(
            ROOMS_KEY,
            ROOM_TTL,
        )

    def delete_room(self, room_id: str) -> None:
        """Удалить активную комнату."""

        if room_id:
            self.redis.hdel(
                ROOMS_KEY,
                room_id,
            )

    def get_room(self, room_id: str) -> dict | None:
        """Вернуть метаданные комнаты или None."""

        raw = self.redis.hget(
            ROOMS_KEY,
            room_id,
        )

        if raw:
            return json.loads(raw)

        return None

    def list_rooms(self) -> list[dict]:
        """Вернуть активные комнаты от новых к старым."""

        all_rooms = self.redis.hgetall(
            ROOMS_KEY
        )
        rooms = []

        for room_id, meta_raw in all_rooms.items():
            meta = json.loads(meta_raw)
            meta["room_id"] = (
                room_id.decode()
                if isinstance(room_id, bytes)
                else room_id
            )
            rooms.append(meta)

        rooms.sort(
            key=lambda room: room["created_at"],
            reverse=True,
        )

        return rooms
