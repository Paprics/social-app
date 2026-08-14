# src/analytics/selectors/messenger.py
"""Messaging statistics — metadata only, no message content."""

from django.db.models import Count

from analytics.dto.dashboard import Period, StatCard
from messenger.models.dialog import Dialog, DialogType
from messenger.models.message import Message


def get_messaging_stats(period: Period) -> list[StatCard]:
    """Return messaging and private-dialog statistics for the selected period."""

    # Messages are physically deleted from the database.
    # Therefore every existing Message row is considered visible/current.
    total_messages = Message.objects.count()

    new_messages = Message.objects.filter(
        created_at__range=(period.start, period.end),
    ).count()

    prev_messages = Message.objects.filter(
        created_at__range=(period.prev_start, period.prev_end),
    ).count()

    private_dialogs = Dialog.objects.filter(
        dialog_type=DialogType.PRIVATE,
    )

    total_dialogs = private_dialogs.count()

    new_dialogs = private_dialogs.filter(
        created_at__range=(period.start, period.end),
    ).count()

    prev_dialogs = private_dialogs.filter(
        created_at__range=(period.prev_start, period.prev_end),
    ).count()

    unique_senders = (
        Message.objects.filter(
            created_at__range=(period.start, period.end),
        )
        .values("sender_id")
        .distinct()
        .count()
    )

    # A private dialog is treated as having a reply when messages
    # were sent by at least two different users.
    dialogs_with_reply = (
        private_dialogs.annotate(
            sender_count=Count(
                "messages__sender_id",
                distinct=True,
            )
        )
        .filter(sender_count__gt=1)
        .count()
    )

    reply_rate = round(dialogs_with_reply / total_dialogs * 100, 1) if total_dialogs else 0.0

    messages_before_period = max(
        total_messages - new_messages,
        0,
    )

    dialogs_before_period = max(
        total_dialogs - new_dialogs,
        0,
    )

    return [
        StatCard(
            label="Total messages",
            value=total_messages,
            prev_value=messages_before_period,
        ),
        StatCard(
            label="New messages",
            value=new_messages,
            prev_value=prev_messages,
        ),
        StatCard(
            label="Total dialogs",
            value=total_dialogs,
            prev_value=dialogs_before_period,
        ),
        StatCard(
            label="New dialogs",
            value=new_dialogs,
            prev_value=prev_dialogs,
        ),
        StatCard(
            label="Unique senders",
            value=unique_senders,
            prev_value=0,
        ),
        StatCard(
            label="Dialogs with reply",
            value=dialogs_with_reply,
            prev_value=0,
            unit=f"{reply_rate}%",
        ),
    ]
