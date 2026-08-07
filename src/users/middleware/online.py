# src/users/middleware/online.py

from users.services.last_seen import LastSeenService
from users.services.online import OnlineService


class OnlineMiddleware:
    """
    Обновляет online-статус и last_seen
    авторизованного пользователя.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        if request.user.is_authenticated:
            user_id = request.user.id

            OnlineService.touch(user_id)
            LastSeenService.touch(user_id)

        return self.get_response(request)
