# accounts/forms.py
import logging
from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _

from geo.models import City, Country, Region

logger = logging.getLogger(__name__)
User = get_user_model()


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    username = forms.CharField(
        max_length=150,
        required=True,
        validators=[UnicodeUsernameValidator()],
    )

    gender = forms.ChoiceField(
        required=True,
        choices=[
            ("", ""),
            ("male", _("Male")),
            ("female", _("Female")),
            ("couple", _("Couple")),
            ("non_binary", _("Non-binary")),
        ],
    )

    birth_date = forms.DateField(required=True)

    country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        required=True,
        empty_label=None,
    )

    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        required=True,
        empty_label=None,
    )

    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=True,
        empty_label=None,
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with this email already exists."))
        return email

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        if User.objects.filter(username=username).exists():
            raise forms.ValidationError(_("A user with this username already exists."))

        return username

    def clean_birth_date(self):
        bd = self.cleaned_data.get("birth_date")
        if not bd:
            raise forms.ValidationError(_("Please enter your date of birth."))

        today = date.today()
        age = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))

        if age < 18:
            raise forms.ValidationError(_("You must be at least 18 years old to register."))

        if age > 80:
            raise forms.ValidationError(_("Please enter a valid date of birth."))

        return bd

    def clean_gender(self):
        gender = self.cleaned_data.get("gender")

        if not gender:
            raise forms.ValidationError(_("Please select your gender."))

        return gender


class LoginForm(forms.Form):
    username = forms.CharField(max_length=254)
    password = forms.CharField()

    def clean_username(self):
        value = self.cleaned_data.get("username", "").strip()
        if not value:
            raise forms.ValidationError(_("This field is required."))
        return value

    def clean_password(self):
        value = self.cleaned_data.get("password", "")
        if len(value) < 6:
            raise forms.ValidationError(_("Password must be at least 6 characters."))
        return value


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(label=_("Email"), max_length=254)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        return email


class SetNewPasswordForm(SetPasswordForm):
    pass


class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(label=_("Current password"), widget=forms.PasswordInput)
    new_password1 = forms.CharField(label=_("New password"), widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("Confirm new password"), widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        old_password = self.cleaned_data.get("old_password")
        if not self.user.check_password(old_password):
            raise forms.ValidationError(_("Current password is incorrect."))
        return old_password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("new_password1")
        p2 = cleaned.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError(_("Passwords do not match."))
        return cleaned

    def save(self):
        self.user.set_password(self.cleaned_data["new_password1"])
        self.user.save()
        return self.user
