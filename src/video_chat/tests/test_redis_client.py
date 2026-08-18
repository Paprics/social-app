# src/video_chat/tests/test_redis_client.py

"""Тесты общего Redis client видеочата."""

import video_chat.services.redis_client as redis_client_module
from video_chat.services.redis_client import get_redis_client


def test_get_redis_client_reuses_cached_client(
    monkeypatch,
):
    client = object()
    calls = []

    get_redis_client.cache_clear()

    def fake_from_url(*args, **kwargs):
        calls.append(
            {
                "args": args,
                "kwargs": kwargs,
            }
        )
        return client

    monkeypatch.setattr(
        redis_client_module.redis_lib,
        "from_url",
        fake_from_url,
    )

    first = get_redis_client()
    second = get_redis_client()

    assert first is client
    assert second is client
    assert len(calls) == 1

    get_redis_client.cache_clear()
