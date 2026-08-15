# src/notifications/services.py

"""Business operations for notifications."""

from django.utils import timezone

from notifications.models import Notification


class NotificationService:
    """Manage notification state."""

    @staticmethod
    def notify_photo_like(*, actor, photo):
        """Create or reactivate a photo-like notification."""

        recipient_id = photo.album.user_id

        if actor.pk == recipient_id:
            return None

        notification, _ = Notification.objects.update_or_create(
            recipient_id=recipient_id,
            actor=actor,
            kind=Notification.Kind.PHOTO_LIKE,
            photo=photo,
            defaults={
                "is_read": False,
                "last_triggered_at": timezone.now(),
            },
        )

        return notification

    @staticmethod
    def mark_read(*, recipient, notification_id) -> bool:
        """Mark one recipient notification as read."""

        updated = Notification.objects.filter(
            pk=notification_id,
            recipient=recipient,
            is_read=False,
        ).update(
            is_read=True,
        )

        return bool(updated)

    @staticmethod
    def mark_all_read(*, recipient) -> int:
        """Mark all unread notifications for recipient as read."""

        return Notification.objects.filter(
            recipient=recipient,
            is_read=False,
        ).update(
            is_read=True,
        )

    @staticmethod
    def notify_photo_comment(*, actor, comment):
        """Create notification for a new photo comment or reply."""

        if comment.photo_id is None:
            return None

        if comment.parent_id is not None:
            recipient_id = comment.parent.author_id
        else:
            recipient_id = comment.photo.album.user_id

        if actor.pk == recipient_id:
            return None

        return Notification.objects.create(
            recipient_id=recipient_id,
            actor=actor,
            kind=Notification.Kind.PHOTO_COMMENT,
            photo=comment.photo,
            comment=comment,
            is_read=False,
            last_triggered_at=timezone.now(),
        )

    @staticmethod
    def remove_photo_like(*, actor, photo) -> bool:
        """Remove the notification associated with a removed photo like."""

        deleted, _ = Notification.objects.filter(
            recipient_id=photo.album.user_id,
            actor=actor,
            kind=Notification.Kind.PHOTO_LIKE,
            photo=photo,
        ).delete()

        return bool(deleted)
