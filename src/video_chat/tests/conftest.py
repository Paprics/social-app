# src/video_chat/tests/conftest.py

import pytest

import video_chat.services.redis_client as redis_client_module
from video_chat.services.redis_client import get_redis_client


class FakeRedis:
    def __init__(self):
        self.lists = {}
        self.hashes = {}
        self.strings = {}
        self.sorted_sets = {}
        self.expirations = {}
        self.eval_calls = []

    @staticmethod
    def _bytes(value):
        if isinstance(value, bytes):
            return value

        return str(value).encode()

    def set(self, key, value, ex=None):
        self.strings[key] = self._bytes(
            value
        )

        if ex is not None:
            self.expirations[key] = ex

    def get(self, key):
        return self.strings.get(
            key
        )

    def zadd(self, key, mapping):
        values = self.sorted_sets.setdefault(
            key,
            {},
        )

        for member, score in mapping.items():
            values[self._bytes(member)] = float(
                score
            )

    def zrem(self, key, *members):
        values = self.sorted_sets.get(
            key,
            {},
        )

        for member in members:
            values.pop(
                self._bytes(member),
                None,
            )

    def zrevrange(self, key, start, end):
        values = self.sorted_sets.get(
            key,
            {},
        )

        ordered = [
            member
            for member, _score in sorted(
                values.items(),
                key=lambda item: item[1],
                reverse=True,
            )
        ]

        if end == -1:
            return ordered[start:]

        return ordered[
            start : end + 1
        ]

    def lrem(self, key, count, value):
        values = self.lists.setdefault(
            key,
            [],
        )
        target = self._bytes(
            value
        )

        if count == 0:
            self.lists[key] = [
                item
                for item in values
                if item != target
            ]
            return

        raise NotImplementedError

    def lpop(self, key):
        values = self.lists.setdefault(
            key,
            [],
        )

        if not values:
            return None

        return values.pop(
            0
        )

    def rpush(self, key, value):
        self.lists.setdefault(
            key,
            [],
        ).append(
            self._bytes(value)
        )

    def lrange(self, key, start, end):
        values = self.lists.get(
            key,
            [],
        )

        if end == -1:
            return values[start:]

        return values[
            start : end + 1
        ]

    def hset(self, key, field, value):
        self.hashes.setdefault(
            key,
            {},
        )[
            self._bytes(field)
        ] = self._bytes(value)

    def hget(self, key, field):
        return self.hashes.get(
            key,
            {},
        ).get(
            self._bytes(field)
        )

    def hgetall(self, key):
        return dict(
            self.hashes.get(
                key,
                {},
            )
        )

    def hdel(self, key, field):
        self.hashes.get(
            key,
            {},
        ).pop(
            self._bytes(field),
            None,
        )

    def expire(self, key, seconds):
        self.expirations[key] = seconds

    def delete(self, key):
        self.lists.pop(
            key,
            None,
        )
        self.hashes.pop(
            key,
            None,
        )
        self.strings.pop(
            key,
            None,
        )
        self.sorted_sets.pop(
            key,
            None,
        )
        self.expirations.pop(
            key,
            None,
        )

    def eval(
        self,
        script,
        numkeys,
        key,
        channel_name,
    ):
        """Имитировать атомарный Lua matchmaking для unit-тестов."""

        self.eval_calls.append(
            {
                "script": script,
                "numkeys": numkeys,
                "key": key,
                "channel_name": channel_name,
            }
        )

        assert numkeys == 1

        self.lrem(
            key,
            0,
            channel_name,
        )

        partner = self.lpop(
            key
        )

        if partner:
            return partner

        self.rpush(
            key,
            channel_name,
        )

        return None


@pytest.fixture
def fake_redis(monkeypatch):
    redis = FakeRedis()

    get_redis_client.cache_clear()

    monkeypatch.setattr(
        redis_client_module.redis_lib,
        "from_url",
        lambda *args, **kwargs: redis,
    )

    yield redis

    get_redis_client.cache_clear()
