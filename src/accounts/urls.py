# accounts/urls.py
from django.urls import path
from django.views.generic import TemplateView

from accounts.views import (
    ChangePasswordView,
    CheckUsernameView,
    EmailVerificationView,
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    UserLogoutView,
)

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("check-username/", CheckUsernameView.as_view(), name="check_username"),
    path(
        "verify-email/<uidb64>/<token>/",
        EmailVerificationView.as_view(),
        name="verify_email",
    ),
    path(
        "check-email/",
        TemplateView.as_view(template_name="accounts/check_email.html"),
        name="check_email",
    ),
    path(
        "email-verified/",
        TemplateView.as_view(template_name="accounts/email_verified.html"),
        name="email_verified",
    ),
    path("reset-password/", PasswordResetRequestView.as_view(), name="password_reset"),
    path(
        "reset-password/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset-password/sent/",
        TemplateView.as_view(template_name="accounts/password_reset_sent.html"),
        name="password_reset_sent",
    ),
    path(
        "reset-password/complete/",
        TemplateView.as_view(template_name="accounts/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path(
        "password-changed/",
        TemplateView.as_view(template_name="accounts/password_changed.html"),
        name="password_changed",
    ),
]
