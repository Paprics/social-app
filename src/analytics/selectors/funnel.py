# src/analytics/selectors/funnel.py
"""Registration-to-engagement conversion funnel."""

from django.contrib.auth import get_user_model
from django.db.models import Count

from analytics.dto.dashboard import FunnelStep
from messenger.models.dialog import Dialog, DialogType
from messenger.models.message import Message
from messenger.models.participant import Participant
from users.models.profile import Profile

User = get_user_model()


def get_funnel() -> list[FunnelStep]:
    """
    Build the registration-to-engagement funnel.

    Steps are cumulative indicators of how far users progressed:
    registration -> profile -> avatar -> photo -> message -> two-way dialog.
    """

    active_users = User.objects.filter(is_active=True)

    total_users = active_users.count()
    denominator = total_users or 1

    profile_filled = (
        Profile.objects.filter(
            user__is_active=True,
            birth_date__isnull=False,
        )
        .exclude(gender="")
        .count()
    )

    with_avatar = Profile.objects.filter(
        user__is_active=True,
        avatar_photo__isnull=False,
    ).count()

    with_photo = (
        active_users.filter(
            galleries__photos__isnull=False,
        )
        .distinct()
        .count()
    )

    sent_message = (
        Message.objects.filter(
            sender__is_active=True,
        )
        .values("sender_id")
        .distinct()
        .count()
    )

    # Private dialogs where both sides have actually written messages.
    two_way_dialog_ids = (
        Dialog.objects.filter(
            dialog_type=DialogType.PRIVATE,
        )
        .annotate(
            sender_count=Count(
                "messages__sender_id",
                distinct=True,
            )
        )
        .filter(sender_count__gte=2)
        .values("id")
    )

    two_way_dialog_users = (
        Participant.objects.filter(
            dialog_id__in=two_way_dialog_ids,
            is_active=True,
            user__is_active=True,
        )
        .values("user_id")
        .distinct()
        .count()
    )

    steps = [
        ("Registered", total_users),
        ("Profile filled", profile_filled),
        ("Avatar uploaded", with_avatar),
        ("At least 1 photo", with_photo),
        ("Sent a message", sent_message),
        ("Two-way conversation", two_way_dialog_users),
    ]

    return [
        FunnelStep(
            label=label,
            count=count,
            pct=round(count / denominator * 100, 1),
        )
        for label, count in steps
    ]
