# src/messenger/services/typing.py

"""
Business logic for typing events.
"""


class TypingService:
    """
    Сервис обработки событий набора текста.
    """

    @staticmethod
    def typing_started(user):
        """
        Пользователь начал печатать.

        Возвращает событие для WebSocket.
        """

        return {
            "type": "typing.started",
            "user_id": user.id,
        }

    @staticmethod
    def typing_stopped(user):
        """
        Пользователь перестал печатать.

        Возвращает событие для WebSocket.
        """

        return {
            "type": "typing.stopped",
            "user_id": user.id,
        }