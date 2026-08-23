from django.contrib.auth import get_user_model

from users.models import Profile, UserSettings
from django.conf import settings

User = get_user_model()


def user_settings(request):
    if not request.user.is_authenticated:
        return {}

    settings = UserSettings.objects.get(user=request.user)

    return {
        "user_settings": settings,
    }
