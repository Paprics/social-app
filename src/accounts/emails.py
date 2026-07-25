# accounts/emails.py
import logging

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

from accounts.tokens import (
    generate_email_verification_token,
    generate_password_reset_token,
)

logger = logging.getLogger(__name__)


def send_email_verification(user, request=None):
    """
    Отправляет письмо с ссылкой для подтверждения email.
    Вызывается из RegisterView после сохранения user (is_active=False).
    """
    token = generate_email_verification_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    domain = get_current_site(request).domain if request else settings.SITE_DOMAIN

    path = reverse(
        "accounts:verify_email",
        kwargs={
            "uidb64": uid,
            "token": token,
        },
    )

    verify_url = request.build_absolute_uri(path)

    subject = _("Confirm your email")
    message = render_to_string(
        "accounts/emails/email_verification.html",
        {
            "user": user,
            "verify_url": verify_url,
            "domain": domain,
        },
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=message,
            fail_silently=False,
        )
        logger.info(
            "send_email_verification: sent to user=%s email=%s", user.pk, user.email
        )
    except Exception as exc:
        logger.error(
            "send_email_verification: failed for user=%s error=%s", user.pk, exc
        )
        raise


def send_password_reset_email(user, request=None):
    """
    Отправляет письмо со ссылкой для сброса пароля.
    """
    token = generate_password_reset_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    domain = get_current_site(request).domain if request else settings.SITE_DOMAIN
    path = reverse(
        "accounts:password_reset_confirm",
        kwargs={
            "uidb64": uid,
            "token": token,
        },
    )

    reset_url = request.build_absolute_uri(path)

    subject = _("Reset your password")
    message = render_to_string(
        "accounts/emails/password_reset.html",
        {
            "user": user,
            "reset_url": reset_url,
            "domain": domain,
        },
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=message,
            fail_silently=False,
        )
        logger.info("send_password_reset_email: sent to user=%s", user.pk)
    except Exception as exc:
        logger.error(
            "send_password_reset_email: failed for user=%s error=%s", user.pk, exc
        )
        raise
