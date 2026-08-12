# src/_config/settings/dev.py
from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env.int("POSTGRES_PORT"),
    }
}

INSTALLED_APPS += [
    "debug_toolbar",
    "rosetta",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
] + MIDDLEWARE

# INTERNAL_IPS = [
#     "127.0.0.1",
# ]

# Debug ToolBar Docker
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: True,
}

# На dev письма пишутся в консоль, не отправляются реально
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
