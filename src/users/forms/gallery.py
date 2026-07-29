# src/users/forms/gallery.py
from django import forms
from django.utils.translation import gettext_lazy as _
from users.validators.image import validate_uploaded_image


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
