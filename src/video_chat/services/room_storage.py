# src/video_chat/services/room_storage.py

"""Хранение активных комнат видеочата в Redis."""

import json
import time

from video_chat.services.redis_client import get_redis_client

ROOM_KEY_PREFIX = "chat:room:"
ROOM_INDEX_KEY = "chat:room:index"
ROOM_TTL = 7200


class RoomStorage:
    """Управляет metadata активных комнат с индивидуальным TTL."""

    def __init__(self):
        self.redis = get_redis_client()

    @staticmethod
    def _key(room_id: str) -> str:
        """Вернуть Redis key комнаты."""

        return f"{ROOM_KEY_PREFIX}{room_id}"

    def create_room(
        self,
        room_id: str,
        caller_channel: str,
        callee_channel: str,
        *,
        caller_participant: dict | None = None,
        callee_participant: dict | None = None,
    ) -> None:
        """Сохранить комнату и добавить её в индекс активных комнат."""

        created_at = time.time()
        meta = {
            "caller": caller_channel,
            "callee": callee_channel,
            "caller_participant": caller_participant or {},
            "callee_participant": callee_participant or {},
            "created_at": created_at,
        }

        self.redis.set(
            self._key(room_id),
            json.dumps(meta),
            ex=ROOM_TTL,
        )
        self.redis.zadd(
            ROOM_INDEX_KEY,
            {
                room_id: created_at,
            },
        )

    def delete_room(self, room_id: str) -> None:
        """Удалить комнату и её запись из индекса."""

        if not room_id:
            return

        self.redis.delete(
            self._key(room_id)
        )
        self.redis.zrem(
            ROOM_INDEX_KEY,
            room_id,
        )

    def get_room(self, room_id: str) -> dict | None:
        """Вернуть metadata комнаты или None."""

        raw = self.redis.get(
            self._key(room_id)
        )

        if raw is None:
            return None

        return json.loads(raw)

    def list_rooms(self) -> list[dict]:
        """Вернуть активные комнаты от новых к старым."""

        room_ids = self.redis.zrevrange(
            ROOM_INDEX_KEY,
            0,
            -1,
        )
        rooms = []
        stale_room_ids = []

        for raw_room_id in room_ids:
            room_id = (
                raw_room_id.decode()
                if isinstance(raw_room_id, bytes)
                else str(raw_room_id)
            )

            room = self.get_room(
                room_id
            )

            if room is None:
                stale_room_ids.append(
                    room_id
                )
                continue

            room["room_id"] = room_id
            rooms.append(room)

        if stale_room_ids:
            self.redis.zrem(
                ROOM_INDEX_KEY,
                *stale_room_ids,
            )

        return rooms
