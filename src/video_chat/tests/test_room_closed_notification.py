# src/video_chat/tests/test_room_closed_notification.py

"""Регрессия уведомления moderator group при завершении room."""

import asyncio

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from video_chat.tests.test_signaling_consumer import (
    connect_pair,
    signaling_backend,
)


def test_end_current_room_notifies_moderator_group(
    signaling_backend,
):
    """Next отправляет room.closed в moderator group удалённой комнаты."""

    async def scenario():
        layer = get_channel_layer()

        (
            caller,
            callee,
            caller_match,
            _,
        ) = await connect_pair()

        room_id = caller_match["room_id"]
        moderator_channel = await layer.new_channel(
            "room-closed-test."
        )

        await layer.group_add(
            f"moderate_{room_id}",
            moderator_channel,
        )

        await caller.send_json_to(
            {
                "type": "next",
            }
        )

        event = await asyncio.wait_for(
            layer.receive(moderator_channel),
            timeout=1,
        )

        assert event == {
            "type": "room.closed",
        }

        await layer.group_discard(
            f"moderate_{room_id}",
            moderator_channel,
        )

        await caller.disconnect()
        await callee.disconnect()

    async_to_sync(scenario)()
