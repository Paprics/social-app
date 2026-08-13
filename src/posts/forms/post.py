from django import forms


class PostForm(forms.Form):
    """Validate post input."""

    content = forms.CharField(
        max_length=5000,
        required=False,
        strip=True,
    )

    def clean(self):
        cleaned_data = super().clean()

        content = cleaned_data.get("content", "")
        photos = self.files.getlist("photos")

        if not content and not photos:
            raise forms.ValidationError("Post must contain text or at least one image.")

        return cleaned_data
