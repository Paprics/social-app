# src/users/forms/gallery.py
from django import forms
from django.utils.translation import gettext_lazy as _

from gallery.models import UserAlbum
from gallery.validators.image import validate_uploaded_image


class PhotoUploadForm(forms.Form):
    """
    Форма используется только для валидации — рендер на фронтенде.
    Принимает множество файлов через поле photos (multiple).
    """

    photos = forms.FileField(required=True)

    def clean(self):
        cleaned_data = super().clean()
        files = self.files.getlist("photos")
        if not files:
            raise forms.ValidationError(_("No photos were uploaded."))
        errors = []
        valid_files = []
        for file in files:
            try:
                validate_uploaded_image(file)
                valid_files.append(file)
            except forms.ValidationError as exc:
                errors.append(f"{file.name}: {'; '.join(exc.messages)}")
        if errors and not valid_files:
            raise forms.ValidationError(errors)
        if errors:
            # Частичная валидация: сохраняем только прошедшие
            print(f"[forms/gallery] Некоторые файлы не прошли валидацию: {errors}")
        cleaned_data["photos"] = valid_files
        return cleaned_data


class AlbumCreateForm(forms.ModelForm):
    """Validate user-editable album creation fields."""

    class Meta:
        model = UserAlbum
        fields = (
            "title",
            "visibility",
        )

    def clean_title(self):
        """Normalize the album title and reject whitespace-only values."""
        title = self.cleaned_data["title"].strip()

        if not title:
            raise forms.ValidationError(
                _("Enter an album title."),
                code="required",
            )

        return title
