from django.contrib.auth import get_user_model

from messenger.models import Dialog
from messenger.selectors.message import get_latest_messages

User = get_user_model()


class DialogPageService:
    """
    Формирует данные для страницы диалога.
    """

    @staticmethod
    def build(
        dialog: Dialog,
        request,
    ) -> dict:
        """
        Собирает контекст страницы диалога.
        """

        request_user: User = request.user

        other_user = None

        if dialog.is_private:

            for participant in dialog.participants.all():

                if participant.user_id != request_user.id:
                    other_user = participant.user
                    break

        show_online_status = False
        is_online = False
        last_seen = None

        if other_user:

            show_online_status = (
                other_user.settings.show_online_status
            )

            if show_online_status:
                is_online = other_user.profile.is_online
                last_seen = other_user.profile.last_seen

        return {
            "other_user": other_user,
            "messages": get_latest_messages(dialog.id),

            "show_online_status": show_online_status,
            "is_online": is_online,
            "last_seen": last_seen,
        }