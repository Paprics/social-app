# src/_config/settings/test.py

from .dev import *  # noqa: F403

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

DEBUG = False


# ---------------------------------------------------------------------------
# Debug Toolbar
# ---------------------------------------------------------------------------

# Debug Toolbar нужен только при ручной разработке.
# В pytest он не должен участвовать в обработке HTTP-запросов.

INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]  # noqa: F405

MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE  # noqa: F405
    if middleware != "debug_toolbar.middleware.DebugToolbarMiddleware"
]


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

# Для тестовых пользователей криптографически дорогой password hasher не нужен.
# Это заметно ускоряет create_user() и force_login()-сценарии.

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

# WebSocket tests must not depend on an external Redis process.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

