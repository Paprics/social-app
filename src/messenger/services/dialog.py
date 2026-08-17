# src/messenger/services/dialog.py

"""
Business logic for dialogs.
"""

from django.db import transaction
from django.utils import timezone

from messenger.models import Dialog, Participant
from messenger.selectors.participant import is_user_participant
from messenger.services.read import ReadService


class DialogService:
    """
    Сервис работы с диалогами.

    Отвечает только за бизнес-логику.
    Все сложные запросы находятся в selectors.
    """

    @staticmethod
    @transaction.atomic
    def create_dialog(users):
        """
        Создает новый диалог и добавляет участников.

        Args:
            users: список объектов User.
        """

        dialog = Dialog.objects.create()

        Participant.objects.bulk_create(
            [
                Participant(
                    dialog=dialog,
                    user=user,
                )
                for user in users
            ]
        )

        return dialog

    @staticmethod
    @transaction.atomic
    def get_or_create_private_dialog(user1, user2):
        """
        Возвращает существующий личный диалог.

        Если диалог отсутствует —
        создает новый.
        """

        dialog = (
            Dialog.objects.filter(
                dialog_type="private",
                participants__user=user1,
            )
            .filter(
                participants__user=user2,
            )
            .first()
        )

        if dialog:
            return dialog

        return DialogService.create_dialog(
            [
                user1,
                user2,
            ]
        )

    @staticmethod
    def add_participant(dialog, user):
        """
        Добавляет пользователя в диалог.

        Если пользователь ранее вышел из диалога,
        повторно активирует его участие.
        """

        participant, _ = Participant.objects.get_or_create(
            dialog=dialog,
            user=user,
            defaults={
                "is_active": True,
            },
        )

        if not participant.is_active:
            participant.is_active = True
            participant.save(
                update_fields=[
                    "is_active",
                ]
            )

        return participant

    @staticmethod
    def remove_participant(dialog, user):
        """
        Исключает пользователя из диалога.

        Используется soft delete —
        запись Participant сохраняется.
        """

        Participant.objects.filter(
            dialog=dialog,
            user=user,
        ).update(
            is_active=False,
        )

    @staticmethod
    def user_has_access(dialog_id, user_id):
        """Проверяет доступ пользователя к диалогу."""

        return is_user_participant(
            dialog_id=dialog_id,
            user_id=user_id,
        )

    @staticmethod
    def mark_as_read(
        dialog,
        user,
    ):
        """
        Compatibility adapter.

        Read cursor изменяет только ReadService.
        После миграции всех callers этот метод можно удалить.
        """

        participant = (
            Participant.objects
            .filter(
                dialog=dialog,
                user=user,
                is_active=True,
            )
            .first()
        )

        if participant is None:
            return None

        last_message_id = (
            dialog.messages
            .order_by("-id")
            .values_list(
                "id",
                flat=True,
            )
            .first()
        )

        if last_message_id is None:
            return participant

        ReadService.mark_read_up_to(
            dialog_id=dialog.id,
            user_id=user.id,
            message_id=last_message_id,
        )

        participant.refresh_from_db(
            fields=[
                "last_read_message",
            ],
        )

        return participant

    @staticmethod
    def get_other_user(dialog, current_user):
        """
        Возвращает второго участника приватного диалога.

        Использует уже загруженных участников,
        если они были получены через prefetch_related().
        """

        for participant in dialog.participants.all():

            if participant.user_id != current_user.id:
                return participant.user

        return None

    @staticmethod
    @transaction.atomic
    def delete_dialog(
            *,
            dialog: Dialog,
            user,
    ) -> None:
        """
        Полностью удаляет диалог.

        Удалять может только участник диалога.
        """

        if not DialogService.user_has_access(
                dialog.id,
                user.id,
        ):
            raise PermissionError(
                "Access denied.",
            )

        dialog.delete()