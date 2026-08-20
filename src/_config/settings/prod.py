# src/_config/settings/prod.py

from .base import *

DEBUG = False

ALLOWED_HOSTS = [
    "flingon.xyz",
    "www.flingon.xyz",
]

CSRF_TRUSTED_ORIGINS = [
    "https://flingon.xyz",
    "https://www.flingon.xyz",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB"),
        "USER": env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST"),
        "PORT": env.int("POSTGRES_PORT"),
        "CONN_MAX_AGE": 600,
        "OPTIONS": {
            "connect_timeout": 10,
        },
    }
}

# Production video chat requires a working TURN server.
VIDEO_CHAT_REQUIRE_TURN = True
TURN_URL = env("TURN_URL")
TURN_USER = env("TURN_USER")
TURN_PASSWORD = env("TURN_PASSWORD")

# HTTPS terminates at Caddy.
# Caddy -> internal nginx -> Daphne must preserve X-Forwarded-Proto: https.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
