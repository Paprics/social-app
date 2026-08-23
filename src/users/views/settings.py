# accounts/views/settings_views.py
import json
from datetime import date
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views import View

from geo.models import City, Country, Region
from users.forms import (
    ProfileSettingsForm,
    PrivacySettingsForm,
    CommunicationSettingsForm,
)
from users.models import Profile, UserSettings

User = get_user_model()


class SensitiveContentToggleView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        settings = request.user.settings

        settings.blur_media = "blur_media" in request.POST
        settings.save(update_fields=["blur_media"])

        return HttpResponse(status=204)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _htmx_response(ok: bool, message: str) -> HttpResponse:
    payload = json.dumps({"settingsToast": {"ok": ok, "message": message}})
    resp = HttpResponse(status=200)
    resp["HX-Trigger"] = payload
    return resp


def _handle_form(request, form_class, success_msg=None, **form_kwargs):
    """
    Обрабатывает POST-запрос с Django-формой.

    Создаёт экземпляр формы, используя request.POST и request.FILES,
    передаёт текущего аутентифицированного пользователя и дополнительные
    именованные аргументы, выполняет валидацию данных, сохраняет форму
    при успешной проверке и возвращает стандартизированный HTMX-ответ.

    Args:
        request: Текущий HTTP-запрос.
        form_class: Класс Django Form или ModelForm для создания экземпляра формы.
        success_msg: Необязательное сообщение, возвращаемое при успешном сохранении.
        **form_kwargs: Дополнительные именованные аргументы, передаваемые
            в конструктор формы (например, instance, initial).

    Returns:
        HttpResponse: HTMX-ответ, содержащий результат успешной обработки
            или сообщение об ошибке.
    """
    form = form_class(request.POST, request.FILES, user=request.user, **form_kwargs)
    if form.is_valid():
        form.save()
        return _htmx_response(ok=True, message=success_msg or _("Changes saved."))
    errors = [
        f"{field}: {', '.join(errs)}" if field != "__all__" else ", ".join(errs) for field, errs in form.errors.items()
    ]
    return _htmx_response(ok=False, message=errors[0] if errors else _("Invalid data."))


# ─── Main page ────────────────────────────────────────────────────────────────


class SettingsPageView(LoginRequiredMixin, View):

    def get(self, request):

        user = User.objects.select_related(
            "profile",
            "settings",
            "premium_features",
        ).get(pk=request.user.pk)

        country_id = user.profile.country_id
        region_id = user.profile.region_id
        city_id = user.profile.city_id

        countries = Country.objects.filter(code2__in=settings.GEO_ALLOWED_COUNTRIES).order_by("name_en")

        regions = Region.objects.filter(country_id=country_id).order_by("name_en") if country_id else []

        cities = City.objects.filter(region_id=region_id).order_by("-population", "name_en") if region_id else []

        current_year = date.today().year

        birth_days = range(1, 32)

        birth_months = (
            (1, _("January")),
            (2, _("February")),
            (3, _("March")),
            (4, _("April")),
            (5, _("May")),
            (6, _("June")),
            (7, _("July")),
            (8, _("August")),
            (9, _("September")),
            (10, _("October")),
            (11, _("November")),
            (12, _("December")),
        )

        birth_years = range(
            current_year - 18,
            1899,
            -1,
        )

        return render(
            request,
            "users/settings.html",
            {
                "user": user,
                "countries": countries,
                "regions": regions,
                "city_id": city_id,
                "cities": cities,
                "languages": settings.LANGUAGES,
                "gender_choices": Profile.Gender.choices,
                "access_level_choices": UserSettings.AccessLevel.choices,
                "birth_days": birth_days,
                "birth_months": birth_months,
                "birth_years": birth_years,
            },
        )


# ─── Section endpoints (HTMX POST) ───────────────────────────────────────────


class SettingsAccountView(LoginRequiredMixin, View):

    def post(self, request):
        from users.forms.settings import AccountSettingsForm

        form = AccountSettingsForm(request.POST, user=request.user)

        if form.is_valid():
            form.save()

            return JsonResponse({"message": _("Account updated.")})

        return JsonResponse({"errors": form.errors}, status=400)


class SettingsProfileView(LoginRequiredMixin, View):

    def post(self, request):
        form = ProfileSettingsForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():
            form.save()
            return JsonResponse(
                {
                    "success": True,
                    "message": _("Profile updated."),
                }
            )

        return JsonResponse(
            {
                "success": False,
                "errors": form.errors,
            },
            status=400,
        )


class SettingsPrivacyView(LoginRequiredMixin, View):
    def post(self, request):
        return _handle_form(
            request,
            PrivacySettingsForm,
            instance=request.user.settings,
            success_msg=_("Privacy settings saved."),
        )


class SettingsCommunicationView(LoginRequiredMixin, View):
    def post(self, request):
        return _handle_form(
            request,
            CommunicationSettingsForm,
            instance=request.user.settings,
            success_msg=_("Communication settings saved."),
        )


class SettingsPremiumFeaturesView(LoginRequiredMixin, View):
    def post(self, request):
        from accounts.forms.settings_forms import PremiumFeaturesForm

        return _handle_form(request, PremiumFeaturesForm, success_msg=_("Premium settings saved."))
