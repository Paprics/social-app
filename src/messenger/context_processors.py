"""Global messenger state for authenticated users."""

from messenger.selectors.participant import get_unread_messages_count


def messenger_context(request):
    """Expose the global unread-message counter to templates."""

    if not request.user.is_authenticated:
        return {
            "messenger_unread_count": 0,
        }

    return {
        "messenger_unread_count": get_unread_messages_count(
            request.user,
        ),
    }
