# src/posts/forms/comment.py

from django import forms


class CommentForm(forms.Form):
    """Validate comment input."""

    content = forms.CharField(
        max_length=100,
        strip=True,
        error_messages={
            "required": "Comment cannot be empty.",
            "max_length": "Comment must be 100 characters or fewer.",
        },
    )
