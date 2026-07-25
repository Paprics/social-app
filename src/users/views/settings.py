# accounts/views/settings_views.py
import json

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from django.views import View

from geo.models import City, Country, Region
from users.models import Profile

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _htmx_response(ok: bool, message: str) -> HttpResponse:
    payload = json.dumps({"settingsToast": {"ok": ok, "message": message}})
    resp = HttpResponse(status=200)
    resp["HX-Trigger"] = payload
    return resp


def _handle_form(request, form_class, success_msg=None, **form_kwargs):
    form = form_class(request.POST, request.FILES, user=request.user, **form_kwargs)
    if form.is_valid():
        form.save()
        return _htmx_response(ok=True, message=success_msg or _("Changes saved."))
    errors = [
        f"{field}: {', '.join(errs)}" if field != "__all__" else ", ".join(errs)
        for field, errs in form.errors.items()
    ]
    return _htmx_response(ok=False, message=errors[0] if errors else _("Invalid data."))


# ─── Main page ────────────────────────────────────────────────────────────────


class SettingsPageView(LoginRequiredMixin, View):
    def get(self, request):
        profile = request.user.profile
        s = request.user.settings

        country_id = profile.country_id
        region_id = profile.region_id

        countries = Country.objects.filter(
            code2__in=settings.GEO_ALLOWED_COUNTRIES
        ).order_by("name_en")

        regions = (
            Region.objects.filter(country_id=country_id).order_by("name_en")
            if country_id
            else []
        )
        cities = (
            City.objects.filter(region_id=region_id).order_by("-population", "name_en")
            if region_id
            else []
        )

        communication_fields = [
            (
                "private_message_permission",
                _("Private messages"),
                _("Who can send you direct messages."),
                s.private_message_permission,
            ),
            (
                "comment_permission",
                _("Comments"),
                _("Who can comment on your content."),
                s.comment_permission,
            ),
            (
                "wall_post_permission",
                _("Wall posts"),
                _("Who can post on your wall."),
                s.wall_post_permission,
            ),
        ]

        return render(
            request,
            "users/settings.html",
            {
                "countries": countries,
                "regions": regions,
                "cities": cities,
                "profile_gender_choices": Profile.Gender.choices,
                "communication_fields": communication_fields,
            },
        )


# ─── Section endpoints (HTMX POST) ───────────────────────────────────────────


class SettingsAccountView(LoginRequiredMixin, View):
    def post(self, request):
        from accounts.forms.settings_forms import AccountSettingsForm

        return _handle_form(
            request, AccountSettingsForm, success_msg=_("Account updated.")
        )


class SettingsProfileView(LoginRequiredMixin, View):
    def post(self, request):
        from accounts.forms.settings_forms import ProfileSettingsForm

        return _handle_form(
            request, ProfileSettingsForm, success_msg=_("Profile updated.")
        )


class SettingsPrivacyView(LoginRequiredMixin, View):
    def post(self, request):
        from accounts.forms.settings_forms import PrivacySettingsForm

        return _handle_form(
            request, PrivacySettingsForm, success_msg=_("Privacy settings saved.")
        )


class SettingsCommunicationView(LoginRequiredMixin, View):
    def post(self, request):
        from accounts.forms.settings_forms import CommunicationSettingsForm

        return _handle_form(
            request,
            CommunicationSettingsForm,
            success_msg=_("Communication settings saved."),
        )


class SettingsNotificationsView(LoginRequiredMixin, View):
    def post(self, request):
        from accounts.forms.settings_forms import NotificationsSettingsForm

        return _handle_form(
            request,
            NotificationsSettingsForm,
            success_msg=_("Notification preferences saved."),
        )


class SettingsLocalizationView(LoginRequiredMixin, View):
    def post(self, request):
        from accounts.forms.settings_forms import LocalizationSettingsForm

        return _handle_form(
            request, LocalizationSettingsForm, success_msg=_("Language updated.")
        )


class SettingsPremiumFeaturesView(LoginRequiredMixin, View):
    def post(self, request):
        from accounts.forms.settings_forms import PremiumFeaturesForm

        return _handle_form(
            request, PremiumFeaturesForm, success_msg=_("Premium settings saved.")
        )
