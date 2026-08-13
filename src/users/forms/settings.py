# accounts/forms/settings.py
from django.contrib.auth import get_user_model
from django.contrib.auth.validators import UnicodeUsernameValidator
from datetime import date

from users.models import Profile, UserPremiumFeatures, UserSettings
from geo.models import Country, Region, City
from django import forms
from django.conf import settings as django_settings
from django.utils.translation import gettext_lazy as _

GENDER_CHOICES = Profile.Gender.choices
VISIBILITY_CHOICES = UserSettings.AccessLevel.choices
User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# Account form  (username / email / birth_date)
# ──────────────────────────────────────────────────────────────────────────────
class AccountSettingsForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator()],
    )

    birth_date = forms.DateField()

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.exclude(pk=self.user.pk).filter(username__iexact=username).exists():
            raise forms.ValidationError(_("This username is already taken."))

        return username

    def clean_birth_date(self):
        birth_date = self.cleaned_data["birth_date"]

        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

        if age < 18:
            raise forms.ValidationError(_("You must be at least 18 years old to use this service."))

        return birth_date

    def save(self):
        self.user.username = self.cleaned_data["username"]
        self.user.save(update_fields=["username"])

        self.user.profile.birth_date = self.cleaned_data["birth_date"]
        self.user.profile.save(update_fields=["birth_date"])

        return self.user


# ──────────────────────────────────────────────────────────────────────────────
# Profile form  (avatar / bio / gender / looking_for / geo)
# ──────────────────────────────────────────────────────────────────────────────
class ProfileSettingsForm(forms.Form):
    bio = forms.CharField(
        required=False,
        max_length=500,
    )

    status = forms.CharField(
        required=False,
        max_length=150,
    )

    gender = forms.ChoiceField(
        choices=GENDER_CHOICES,
    )

    looking_for = forms.MultipleChoiceField(
        required=False,
        choices=Profile.Gender.choices,
    )

    open_to_gifts = forms.BooleanField(
        required=False,
    )

    financial_meetings_only = forms.BooleanField(
        required=False,
    )

    country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        required=True,
    )

    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        required=True,
    )

    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=True,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_bio(self):
        bio = self.cleaned_data.get("bio")
        return bio.strip() if bio else ""

    def clean_status(self):
        status = self.cleaned_data.get("status")
        return status.strip() if status else ""

    def save(self):
        profile = self.user.profile
        data = self.cleaned_data

        profile.bio = data["bio"]
        profile.status = data["status"]
        profile.gender = data["gender"]

        profile.looking_for = data.get("looking_for", [])

        profile.open_to_gifts = data.get("open_to_gifts", False)
        profile.financial_meetings_only = data.get("financial_meetings_only", False)

        profile.country_id = data["country"]
        profile.region_id = data["region"]
        profile.city_id = data["city"]

        profile.save(
            update_fields=[
                "bio",
                "status",
                "gender",
                "looking_for",
                "open_to_gifts",
                "financial_meetings_only",
                "country",
                "region",
                "city",
            ]
        )


# ──────────────────────────────────────────────────────────────────────────────
# Privacy form
# ──────────────────────────────────────────────────────────────────────────────
class PrivacySettingsForm(forms.ModelForm):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = UserSettings
        fields = (
            "profile_visibility",
            "friends_visibility",
            "photo_albums_visibility",
            "show_online_status",
            "wall_enabled",
            "comments_enabled",
            "blur_media",
        )


# ──────────────────────────────────────────────────────────────────────────────
# Communication form
# ──────────────────────────────────────────────────────────────────────────────
class CommunicationSettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = (
            "message_permission",
            "comment_permission",
            "wall_post_permission",
        )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)


# ──────────────────────────────────────────────────────────────────────────────
# Notifications form
# ──────────────────────────────────────────────────────────────────────────────


class NotificationsSettingsForm(forms.Form):
    notify_messages = forms.BooleanField(required=False, label=_("New messages"))
    notify_friend_requests = forms.BooleanField(required=False, label=_("Friend requests"))
    notify_email = forms.BooleanField(required=False, label=_("Email notifications"))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self):
        data = self.cleaned_data
        s = self.user.settings
        for field in data:
            setattr(s, field, data[field])
        s.save(update_fields=list(data.keys()))


# ──────────────────────────────────────────────────────────────────────────────
# Localization form
# ──────────────────────────────────────────────────────────────────────────────


class LocalizationSettingsForm(forms.Form):
    language = forms.ChoiceField(
        choices=[(code, name) for code, name in django_settings.LANGUAGES],
        label=_("Interface language"),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self):
        self.user.settings.language = self.cleaned_data["language"]
        self.user.settings.save(update_fields=["language"])


# ──────────────────────────────────────────────────────────────────────────────
# Premium features form
# ──────────────────────────────────────────────────────────────────────────────

PREMIUM_BOOL_FIELDS = [
    "incognito_mode",
    "anonymous_profile_views",
    "hide_online_status_from_everyone",
    "random_chat_gender_filter",
    "random_chat_country_filter",
    "random_chat_language_filter",
    "random_chat_age_filter",
    "priority_matching",
    "advanced_search",
    "unlimited_search_radius",
    "hd_video",
    "unsend_messages",
    "scheduled_messages",
    "extended_message_editing",
    "custom_profile_theme",
    "animated_profile_badge",
    "profile_accent_color",
    "profile_statistics",
    "profile_visitors",
]


class PremiumFeaturesForm(forms.Form):
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        for field_name in PREMIUM_BOOL_FIELDS:
            self.fields[field_name] = forms.BooleanField(required=False)

    def save(self):
        data = self.cleaned_data
        pf, _ = UserPremiumFeatures.objects.get_or_create(user=self.user)
        for field in PREMIUM_BOOL_FIELDS:
            setattr(pf, field, data.get(field, False))
        pf.save(update_fields=PREMIUM_BOOL_FIELDS)
