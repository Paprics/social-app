# users/middleware/online.py
from users.services.last_seen import LastSeenService
from users.services.online import OnlineService


class OnlineMiddleware:
    """Updates the authenticated user's online status."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            OnlineService.touch(request.user.id)

        if request.user.is_authenticated:
            OnlineService.touch(request.user.id)
            LastSeenService.touch(request.user.id)

        return self.get_response(request)
