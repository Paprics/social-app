# src/notifications/context_processor.py

"""Global notification counters for authenticated users."""

from notifications.models import Notification
from notifications.selectors import get_unread_notifications_count
from users.selectors.friendship import get_incoming_requests_count


def notifications_context(request):
    """Expose notification counters to global templates."""

    if not request.user.is_authenticated:
        return {}

    friend_requests = get_incoming_requests_count(
        request.user,
    )

    likes = get_unread_notifications_count(
        user=request.user,
        kind=Notification.Kind.PHOTO_LIKE,
    )

    comments = get_unread_notifications_count(
        user=request.user,
        kind=Notification.Kind.PHOTO_COMMENT,
    )

    activity = get_unread_notifications_count(
        user=request.user,
    )

    # TODO: connect when their notification types are implemented.
    unread_messages = 0
    gifts = 0

    notifications_count = friend_requests + unread_messages + activity + gifts

    return {
        "notifications": {
            "has_notifications": notifications_count > 0,
            "count": notifications_count,
            "friend_requests": friend_requests,
            "messages": unread_messages,
            "likes": likes,
            "comments": comments,
            "gifts": gifts,
            "activity": activity,
        }
    }
