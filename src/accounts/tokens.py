# accounts/tokens.py
import logging

from django.contrib.auth.tokens import PasswordResetTokenGenerator

logger = logging.getLogger(__name__)


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Токен для подтверждения email.
    Использует is_active и last_login как часть хэша —
    токен автоматически инвалидируется после активации аккаунта.
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}{user.email}"


class PasswordResetTokenGenerator(PasswordResetTokenGenerator):
    """
    Токен для восстановления пароля.
    Инвалидируется после смены пароля (last_login меняется при входе).
    """

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.password}"


# Синглтоны — используются в emails.py и views.py
email_verification_token = EmailVerificationTokenGenerator()
password_reset_token = PasswordResetTokenGenerator()


def generate_email_verification_token(user):
    """Возвращает токен подтверждения email для пользователя."""
    token = email_verification_token.make_token(user)
    logger.debug("generate_email_verification_token: user=%s token=%s", user.pk, token)
    return token


def verify_email_token(user, token):
    """
    Проверяет токен подтверждения email.
    Возвращает True если токен валиден.
    """
    result = email_verification_token.check_token(user, token)
    logger.debug("verify_email_token: user=%s valid=%s", user.pk, result)
    return result


def generate_password_reset_token(user):
    """Возвращает токен для сброса пароля."""
    token = password_reset_token.make_token(user)
    logger.debug("generate_password_reset_token: user=%s", user.pk)
    return token


def verify_password_reset_token(user, token):
    """Проверяет токен сброса пароля. Возвращает True если валиден."""
    result = password_reset_token.check_token(user, token)
    logger.debug("verify_password_reset_token: user=%s valid=%s", user.pk, result)
    return result
