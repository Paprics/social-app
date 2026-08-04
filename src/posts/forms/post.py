from django import forms


class PostForm(forms.Form):
    content = forms.CharField(
        max_length=5000,
        strip=True,
    )

    def clean_content(self):
        content = self.cleaned_data["content"]

        if not content.strip():
            raise forms.ValidationError("Post cannot be empty.")

        return content
