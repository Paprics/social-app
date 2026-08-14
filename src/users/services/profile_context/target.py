# src/users/services/profile_context/target.py

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

User = get_user_model()


def get_profile_target(pk):
    """Return profile owner with relations required by profile pages."""

    return get_object_or_404(
        User.objects.select_related(
            "profile",
            "settings",
            "premium_features",
        ),
        pk=pk,
    )
