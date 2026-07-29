# accounts/forms/settings.py
from users.models import Profile, UserPremiumFeatures, UserSettings
from django import forms
from django.conf import settings as django_settings
from django.utils.translation import gettext_lazy as _

# ──────────────────────────────────────────────────────────────────────────────
# Account form  (username / email / birth_date)
# ──────────────────────────────────────────────────────────────────────────────


class AccountSettingsForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label=_("Username"),
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )

    birth_date = forms.DateField(
        label=_("Date of birth"),
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_username(self):
        username = self.cleaned_data["username"]
        qs = type(self.user).objects.exclude(pk=self.user.pk).filter(username=username)
        if qs.exists():
            raise forms.ValidationError(_("This username is already taken."))
        return username

    def clean_birth_date(self):
        from datetime import date

        bd = self.cleaned_data["birth_date"]
        today = date.today()
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        if age < 18:
            raise forms.ValidationError(_("You must be at least 18 years old to use this service."))
        return bd

    def save(self):
        data = self.cleaned_data
        user = self.user
        user.username = data["username"]
        user.save(update_fields=["username", "email"])

        profile = user.profile
        profile.birth_date = data["birth_date"]
        profile.save(update_fields=["birth_date"])


# ──────────────────────────────────────────────────────────────────────────────
# Profile form  (avatar / bio / gender / looking_for / geo)
# ──────────────────────────────────────────────────────────────────────────────

GENDER_CHOICES = Profile.Gender.choices


class ProfileSettingsForm(forms.Form):
    avatar = forms.ImageField(required=False, label=_("Profile photo"))
    bio = forms.CharField(
        required=False,
        max_length=500,
        label=_("Bio"),
        widget=forms.Textarea(attrs={"rows": 3, "maxlength": 500}),
    )
    gender = forms.ChoiceField(
        required=False,
        choices=[("", _("Not specified"))] + GENDER_CHOICES,
        label=_("Gender"),
    )
    looking_for = forms.MultipleChoiceField(
        required=False,
        choices=GENDER_CHOICES,
        label=_("Looking for"),
        widget=forms.CheckboxSelectMultiple(),
    )
    country = forms.IntegerField(required=False, label=_("Country"))
    region = forms.IntegerField(required=False, label=_("Region"))
    city = forms.IntegerField(required=False, label=_("City"))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self):
        data = self.cleaned_data
        profile = self.user.profile

        if data.get("avatar"):
            profile.avatar = data["avatar"]
        profile.bio = data.get("bio", "")
        profile.gender = data.get("gender", "")
        profile.looking_for = data.get("looking_for", [])
        profile.country_id = data.get("country") or None
        profile.region_id = data.get("region") or None
        profile.city_id = data.get("city") or None
        profile.save(
            update_fields=[
                "avatar",
                "bio",
                "gender",
                "looking_for",
                "country",
                "region",
                "city",
            ]
        )


# ──────────────────────────────────────────────────────────────────────────────
# Privacy form
# ──────────────────────────────────────────────────────────────────────────────

VISIBILITY_CHOICES = UserSettings.ProfileVisibility.choices


class PrivacySettingsForm(forms.Form):
    profile_visibility = forms.ChoiceField(choices=VISIBILITY_CHOICES, label=_("Profile visibility"))
    friends_visibility = forms.ChoiceField(choices=VISIBILITY_CHOICES, label=_("Friends list"))
    photo_albums_visibility = forms.ChoiceField(choices=VISIBILITY_CHOICES, label=_("Photo albums"))
    show_online_status = forms.BooleanField(required=False, label=_("Show online status"))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def save(self):
        data = self.cleaned_data
        s = self.user.settings
        for field in [
            "profile_visibility",
            "friends_visibility",
            "photo_albums_visibility",
            "show_online_status",
        ]:
            setattr(s, field, data[field])
        s.save(update_fields=list(data.keys()))


# ──────────────────────────────────────────────────────────────────────────────
# Communication form
# ──────────────────────────────────────────────────────────────────────────────

PERMISSION_CHOICES = UserSettings.PermissionLevel.choices


class CommunicationSettingsForm(forms.Form):
    private_message_permission = forms.ChoiceField(choices=PERMISSION_CHOICES, label=_("Private messages"))
    comment_permission = forms.ChoiceField(choices=PERMISSION_CHOICES, label=_("Comments"))
    wall_post_permission = forms.ChoiceField(choices=PERMISSION_CHOICES, label=_("Wall posts"))

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
