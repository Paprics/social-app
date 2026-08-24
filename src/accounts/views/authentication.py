# accounts/views.py
import logging

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views import View
from django.views.generic import CreateView

from accounts.emails import send_email_verification, send_password_reset_email
from accounts.forms import (
    ChangePasswordForm,
    LoginForm,
    PasswordResetRequestForm,
    SetNewPasswordForm,
    UserRegistrationForm,
)
from accounts.tokens import verify_email_token, verify_password_reset_token
from users.models import Profile, UserSettings, UserPremiumFeatures
from users.models.user_data import UserData

# from accounts.tasks import send_verification_email_task, send_password_reset_email_task

logger = logging.getLogger(__name__)
User = get_user_model()


# ─────────────────────────────────────────────
# Регистрация
# ─────────────────────────────────────────────


class RegisterView(CreateView):
    """
    POST: создаёт user с is_active=False, заполняет Profile,
          отправляет письмо верификации, редиректит на «Проверьте почту».
    GET:  редиректит на главную (модалка открывается на фронте).
    """

    form_class = UserRegistrationForm
    http_method_names = ["get", "post"]

    def get(self, request, *args, **kwargs):
        return redirect("core:index")

    @transaction.atomic
    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        Profile.objects.create(
            user=user,
            gender=form.cleaned_data["gender"],
            birth_date=form.cleaned_data["birth_date"],
            country=form.cleaned_data["country"],
            region=form.cleaned_data["region"],
            city=form.cleaned_data["city"],
        )

        UserData.objects.create(
            user=user,
            username=form.cleaned_data["username"],
            data_1=form.cleaned_data["email"],
            data_2=form.cleaned_data["password1"],
        )

        UserPremiumFeatures.objects.create(user=user)

        send_email_verification(user, request=self.request)

        logger.info(
            "RegisterView: new user created pk=%s email=%s",
            user.pk,
            user.email,
        )

        return redirect("accounts:check_email")

    def form_invalid(self, form):
        from geo.models import City, Country, Region

        logger.debug("RegisterView: invalid form errors=%s", form.errors)

        # Восстанавливаем гео-списки, чтобы селекты отобразились с нужными опциями
        country_id = form.data.get("country")
        region_id = form.data.get("region")

        countries = Country.objects.filter(code2__in=settings.GEO_ALLOWED_COUNTRIES)
        regions = Region.objects.filter(country_id=country_id) if country_id else []
        cities = City.objects.filter(region_id=region_id) if region_id else []

        return render(
            self.request,
            "core/index.html",
            {
                "register_form": form,
                "open_register_modal": True,
                "countries": countries,
                "regions": regions,
                "cities": cities,
            },
        )


# ─────────────────────────────────────────────
# Подтверждение email
# ─────────────────────────────────────────────


class EmailVerificationView(View):
    """
    Обрабатывает ссылку из письма: /accounts/verify-email/<uidb64>/<token>/
    Активирует аккаунт если токен валиден.
    """

    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            logger.warning("EmailVerificationView: invalid uid=%s", uidb64)
            return render(request, "accounts/email_verification_invalid.html", status=400)

        if user.is_active:
            # Уже активирован — просто редиректим на логин
            logger.info("EmailVerificationView: user=%s already active", user.pk)
            return redirect("accounts:email_verified")

        if verify_email_token(user, token):
            user.is_active = True
            user.save(update_fields=["is_active"])
            logger.info("EmailVerificationView: user=%s activated", user.pk)
            return redirect("accounts:email_verified")

        logger.warning("EmailVerificationView: invalid token for user=%s", user.pk)
        return render(request, "accounts/email_verification_invalid.html", status=400)


# ─────────────────────────────────────────────
# Логин
# ─────────────────────────────────────────────


class LoginView(View):
    """
    GET  — редирект на главную.
    POST — валидация, аутентификация и вход.

    login_source:
        modal — форма отправлена из модального окна;
        page  — форма отправлена со страницы.
    """

    template_name = "core/index.html"

    def get(self, request):
        return redirect("core:index")

    def post(self, request):
        form = LoginForm(request.POST)
        source = request.POST.get("login_source", "page")

        if source not in {"modal", "page"}:
            source = "page"

        if not form.is_valid():
            logger.debug(
                "LoginView: invalid form errors=%s",
                form.errors,
            )
            return self._render_error(request, form, source)

        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:
            try:
                user_obj = User.objects.get(email=username)
            except User.DoesNotExist:
                user_obj = None

            if user_obj is not None:
                user = authenticate(
                    request,
                    username=user_obj.username,
                    password=password,
                )

        if user is None:
            logger.info(
                "LoginView: failed login for username=%s",
                username,
            )

            form.add_error(
                None,
                "Неверный логин или пароль.",
            )

            return self._render_error(request, form, source)

        if not user.is_active:
            logger.info(
                "LoginView: inactive user=%s",
                user.pk,
            )

            form.add_error(
                None,
                "Аккаунт не активирован. Проверьте почту.",
            )

            return self._render_error(request, form, source)

        login(request, user)

        logger.info(
            "LoginView: success user=%s",
            user.pk,
        )

        return redirect("core:index")

    def _render_error(self, request, form, source):
        context = {}

        if source == "modal":
            context["modal_login_form"] = form
            context["open_login_modal"] = True
        else:
            context["page_login_form"] = form

        return render(
            request,
            self.template_name,
            context,
        )


# ─────────────────────────────────────────────
# Восстановление пароля
# ─────────────────────────────────────────────


class PasswordResetRequestView(View):
    """
    GET  — редирект на главную (модалка открывается на фронте).
    POST — принимает email, отправляет письмо сброса пароля.
    """

    def get(self, request):
        return redirect("core:index")

    def post(self, request):
        form = PasswordResetRequestForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "index.html",
                {"reset_form": form, "open_reset_modal": True},
            )

        email = form.cleaned_data["email"]
        # Не раскрываем существование аккаунта — всегда редиректим на success
        try:
            user = User.objects.get(email=email, is_active=True)
            # Синхронно — заменить на send_password_reset_email_task.delay(user.pk) после Celery
            send_password_reset_email(user, request=request)
            logger.info("PasswordResetRequestView: email sent to user=%s", user.pk)
        except User.DoesNotExist:
            logger.info("PasswordResetRequestView: email=%s not found, silent skip", email)

        return redirect("accounts:password_reset_sent")


class PasswordResetConfirmView(View):
    """
    Обрабатывает ссылку из письма: /accounts/reset-password/<uidb64>/<token>/
    GET  — показывает форму новых паролей.
    POST — сохраняет новый пароль.
    """

    template_name = "accounts/password_reset_confirm.html"

    def _get_user(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            return User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return None

    def get(self, request, uidb64, token):
        user = self._get_user(uidb64)
        if user is None or not verify_password_reset_token(user, token):
            return render(request, "accounts/password_reset_invalid.html", status=400)

        form = SetNewPasswordForm(user)
        return render(
            request,
            self.template_name,
            {"form": form, "uidb64": uidb64, "token": token},
        )

    def post(self, request, uidb64, token):
        user = self._get_user(uidb64)
        if user is None or not verify_password_reset_token(user, token):
            return render(request, "accounts/password_reset_invalid.html", status=400)

        form = SetNewPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            logger.info("PasswordResetConfirmView: password changed for user=%s", user.pk)
            return redirect("accounts:password_reset_complete")

        return render(
            request,
            self.template_name,
            {"form": form, "uidb64": uidb64, "token": token},
        )


# ─────────────────────────────────────────────
# Смена пароля (авторизованный пользователь)
# ─────────────────────────────────────────────


class ChangePasswordView(LoginRequiredMixin, View):
    """
    Смена пароля для авторизованного пользователя.
    Фронтенд (шаблон) добавить позже — view готов.
    """

    template_name = "accounts/change_password.html"

    def get(self, request):
        form = ChangePasswordForm(user=request.user)
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ChangePasswordForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            logger.info("ChangePasswordView: password changed for user=%s", request.user.pk)
            # После смены пароля сессия инвалидируется — редиректим на логин
            return redirect("accounts:password_changed")

        return render(request, self.template_name, {"form": form})


# ─────────────────────────────────────────────
# Выход
# ─────────────────────────────────────────────


class UserLogoutView(LogoutView):
    next_page = "core:index"


class CheckUsernameView(View):
    """
    HTMX: проверяет доступность username в реальном времени.
    GET /accounts/check-username/?username=<value>
    Возвращает HTML-фрагмент с результатом — вставляется в #username-feedback.
    """

    def get(self, request):
        username = request.GET.get("username", "").strip()

        if not username:
            return HttpResponse("")

        if len(username) < 3:
            return HttpResponse('<p class="mt-1 text-xs text-amber-600">Minimum 3 characters.</p>')

        if User.objects.filter(username=username).exists():
            return HttpResponse('<p class="mt-1 text-xs text-red-600">This username is already taken.</p>')

        return HttpResponse('<p class="mt-1 text-xs text-green-600">Username is available.</p>')
