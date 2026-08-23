# src/core/context_processors.py

from django.conf import settings


def site_settings(request):
    return {
        "GOOGLE_SITE_VERIFICATION": settings.GOOGLE_SITE_VERIFICATION,
    }
