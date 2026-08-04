# notifications/context_processor.py
from users.services.friendship_service import FriendshipService


def notifications_context(request):
    if not request.user.is_authenticated:
        return {}

    friend_requests = FriendshipService.get_incoming_requests_count(request.user)

    unread_messages = 0
    gifts = 0
    likes = 0
    comments = 0

    notifications_count = friend_requests + unread_messages + gifts + likes + comments
    # unread_messages = MessageService.get_unread_count(request.user)

    return {
        "notifications": {
            "has_notifications": notifications_count > 0,
            "count": notifications_count,
            "friend_requests": friend_requests,
            "messages": unread_messages,
            "likes": likes,
            "comments": comments,
            "gifts": gifts,
        }
    }
