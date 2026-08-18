# src/video_chat/services/room_storage.py

"""
room_storage.py — Хранение активных комнат в Redis.

Зачем это нужно:
    Когда два пользователя матчатся, создаётся комната (room_id).
    Модератор должен видеть список активных комнат чтобы войти в любую.
    Redis хранит этот список — быстро, без базы данных.

Структура данных в Redis:
    chat:rooms — это Hash (словарь):
        ключ:   room_id (строка, UUID)
        значение: JSON с метаданными {caller, callee, created_at}

    Пример:
        chat:rooms = {
            "abc-123": '{"caller": "specific.xxx!aaa", "callee": "specific.xxx!bbb", "created_at": 1700000000}',
            "def-456": '{"caller": "specific.xxx!ccc", "callee": "specific.xxx!ddd", "created_at": 1700000060}',
        }
"""

import json
import os
import time

import redis as redis_lib

# Ключ в Redis где хранится словарь всех активных комнат
ROOMS_KEY = "chat:rooms"

# Время жизни всего словаря комнат — 2 часа.
# Нужно на случай сбоя сервера: если комната не удалилась явно,
# Redis сам очистит её через 2 часа.
ROOM_TTL = 7200


class RoomStorage:
    """Сервис для работы со списком активных комнат в Redis.

    Используется в двух местах:
        1. SignalingConsumer — создаёт и удаляет комнаты при матче/разрыве
        2. ModeratorListView — читает список комнат для отображения модератору
        3. ModeratorConsumer — проверяет существование комнаты при подключении
    """

    def __init__(self):
        # Подключаемся к Redis. URL берётся из переменной окружения,
        # которая прописана в docker-compose.yml как REDIS_URL=redis://redis:6379/0
        self.redis = redis_lib.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        )

    def create_room(self, room_id: str, caller_channel: str, callee_channel: str):
        """Сохранить новую комнату в Redis.

        Вызывается из SignalingConsumer._create_room() сразу после матча.

        Args:
            room_id: UUID комнаты, например "abc-123-def-456"
            caller_channel: channel_name первого пользователя (тот кто нашёл партнёра)
            callee_channel: channel_name второго пользователя (тот кто ждал в очереди)
        """
        # Собираем метаданные комнаты
        meta = json.dumps(
            {
                "caller": caller_channel,
                "callee": callee_channel,
                "created_at": time.time(),  # Unix timestamp — нужен для подсчёта возраста комнаты
            }
        )

        # HSET — добавить поле в hash. Если room_id уже есть — перезапишет.
        self.redis.hset(ROOMS_KEY, room_id, meta)

        # Обновляем TTL на весь hash при каждом изменении.
        # Если комнаты не создавались 2 часа — Redis сам удалит ключ.
        self.redis.expire(ROOMS_KEY, ROOM_TTL)

    def delete_room(self, room_id: str):
        """Удалить комнату из Redis.

        Вызывается когда:
            - Один из участников закрыл вкладку (disconnect)
            - Один из участников нажал "Следующий" (handle_next)
        """
        if room_id:
            # HDEL — удалить конкретное поле из hash
            self.redis.hdel(ROOMS_KEY, room_id)

    def get_room(self, room_id: str) -> dict | None:
        """Получить метаданные одной комнаты по её ID.

        Используется в ModeratorConsumer.connect() чтобы проверить
        существует ли комната перед тем как пустить модератора.

        Returns:
            dict с ключами caller, callee, created_at — если комната есть
            None — если комната не найдена (уже закончилась)
        """
        raw = self.redis.hget(ROOMS_KEY, room_id)
        if raw:
            return json.loads(raw)
        return None

    def list_rooms(self) -> list[dict]:
        """Получить список всех активных комнат, отсортированный по времени создания.

        Используется в ModeratorListView для отображения списка комнат.

        Returns:
            Список dict, каждый содержит: room_id, caller, callee, created_at
            Отсортировано: самые новые комнаты первыми.
        """
        # HGETALL — вернуть все поля и значения из hash
        all_rooms = self.redis.hgetall(ROOMS_KEY)

        result = []
        for room_id, meta_raw in all_rooms.items():
            meta = json.loads(meta_raw)
            # Redis возвращает ключи как bytes, декодируем в строку
            meta["room_id"] = (
                room_id.decode() if isinstance(room_id, bytes) else room_id
            )
            result.append(meta)

        # Сортируем: новые комнаты наверху
        result.sort(key=lambda r: r["created_at"], reverse=True)
        return result
