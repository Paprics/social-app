# accounts/tasks.py
# Celery tasks для асинхронной отправки писем.
# Раскомментировать после подключения Celery + Redis broker.
import logging

logger = logging.getLogger(__name__)

# from celery import shared_task
# from accounts.emails import send_email_verification, send_password_reset_email
# from django.contrib.auth import get_user_model
# User = get_user_model()


# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def send_verification_email_task(self, user_id):
#     """Асинхронная отправка письма подтверждения email."""
#     try:
#         user = User.objects.get(pk=user_id)
#         send_email_verification(user)
#         logger.info("send_verification_email_task: done for user=%s", user_id)
#     except User.DoesNotExist:
#         logger.error("send_verification_email_task: user=%s not found", user_id)
#     except Exception as exc:
#         logger.warning("send_verification_email_task: retry for user=%s error=%s", user_id, exc)
#         raise self.retry(exc=exc)


# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def send_password_reset_email_task(self, user_id):
#     """Асинхронная отправка письма сброса пароля."""
#     try:
#         user = User.objects.get(pk=user_id)
#         send_password_reset_email(user)
#         logger.info("send_password_reset_email_task: done for user=%s", user_id)
#     except User.DoesNotExist:
#         logger.error("send_password_reset_email_task: user=%s not found", user_id)
#     except Exception as exc:
#         logger.warning("send_password_reset_email_task: retry for user=%s error=%s", user_id, exc)
#         raise self.retry(exc=exc)


def send_verification_email_task(user_id):
    """Синхронная заглушка — удалить когда подключишь Celery."""
    from django.contrib.auth import get_user_model

    from accounts.emails import send_email_verification

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        send_email_verification(user)
    except Exception as exc:
        logger.error("send_verification_email_task (sync): error=%s", exc)


def send_password_reset_email_task(user_id):
    """Синхронная заглушка — удалить когда подключишь Celery."""
    from django.contrib.auth import get_user_model

    from accounts.emails import send_password_reset_email

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
        send_password_reset_email(user)
    except Exception as exc:
        logger.error("send_password_reset_email_task (sync): error=%s", exc)
