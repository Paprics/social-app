import logging

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_related_objects(sender, instance, created, **kwargs):
    """
    Создаёт связанные объекты для нового пользователя.
    """

    if not created:
        return

    from users.models.preferences import UserSettings

    try:
        user_settings, settings_created = UserSettings.objects.get_or_create(
            user=instance,
        )

        if settings_created:
            logger.info(
                "signals: UserSettings created for user pk=%s",
                instance.pk,
            )
        else:
            logger.warning(
                "signals: UserSettings already exists for user pk=%s",
                instance.pk,
            )

    except Exception:
        logger.exception(
            "signals: failed to create related objects for user pk=%s",
            instance.pk,
        )
