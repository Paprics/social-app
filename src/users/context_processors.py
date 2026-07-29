from users.models import Profile, UserSettings


def user_settings(request):
    if not request.user.is_authenticated:
        return {}

    settings = UserSettings.objects.get(user=request.user)

    return {
        "user_settings": settings,
    }
