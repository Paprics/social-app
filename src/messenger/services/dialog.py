# src/messenger/services/dialog.py

"""
Business logic for dialogs.
"""

from django.contrib.auth import get_user_model
from django.db import transaction

from messenger.models import Dialog, Participant
from messenger.selectors.dialog import get_private_dialog
from messenger.selectors.participant import is_user_participant
from messenger.services.realtime import MessengerRealtimeService

User = get_user_model()


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
        Возвращает единственный приватный диалог пары пользователей.

        Блокирует обе строки User в стабильном порядке, чтобы два
        конкурентных запроса для одной пары не создали два Dialog.
        """

        user_ids = sorted(
            (
                user1.pk,
                user2.pk,
            )
        )

        list(
            User.objects
            .select_for_update()
            .filter(
                pk__in=user_ids,
            )
            .order_by("pk")
            .values_list(
                "pk",
                flat=True,
            )
        )

        dialog = get_private_dialog(
            user1,
            user2,
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

        dialog_id = dialog.id
        user_ids = tuple(
            dialog.participants.filter(
                is_active=True,
            ).values_list(
                "user_id",
                flat=True,
            )
        )

        dialog.delete()

        transaction.on_commit(
            lambda: MessengerRealtimeService.notify_dialog_deleted(
                dialog_id=dialog_id,
                user_ids=user_ids,
            ),
        )
