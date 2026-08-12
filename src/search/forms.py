from django import forms
from django.utils.translation import gettext_lazy as _

from geo.models import City, Country, Region
from users.models.profile import Profile


class UserSearchForm(forms.Form):
    """Validates GET parameters for the user search page."""

    gender = forms.ChoiceField(
        choices=(
            ("", _("Any")),
            *Profile.Gender.choices,
        ),
        required=False,
    )
    age_from = forms.IntegerField(
        min_value=18,
        max_value=120,
        required=False,
    )
    age_to = forms.IntegerField(
        min_value=18,
        max_value=120,
        required=False,
    )
    country = forms.ModelChoiceField(
        queryset=Country.objects.all(),
        required=False,
    )
    region = forms.ModelChoiceField(
        queryset=Region.objects.all(),
        required=False,
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.all(),
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()

        age_from = cleaned_data.get("age_from")
        age_to = cleaned_data.get("age_to")

        if age_from is not None and age_to is not None and age_from > age_to:
            self.add_error(
                "age_to",
                _("Maximum age cannot be less than minimum age."),
            )

        return cleaned_data
