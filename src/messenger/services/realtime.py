"""Realtime notifications for messenger UI state."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


class MessengerRealtimeService:
    """Publishes cross-client messenger events through Channels groups."""

    @staticmethod
    def notify_dialog_deleted(
        *,
        dialog_id: int,
        user_ids: tuple[int, ...],
    ) -> None:
        """Notify open dialog sockets and each participant inbox socket."""

        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            f"dialog_{dialog_id}",
            {
                "type": "dialog_deleted",
            },
        )

        for user_id in user_ids:
            async_to_sync(channel_layer.group_send)(
                f"messenger_user_{user_id}",
                {
                    "type": "inbox_changed",
                    "reason": "dialog.deleted",
                },
            )
