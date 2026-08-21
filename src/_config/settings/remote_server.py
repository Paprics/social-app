"""
Django settings for local development against the remote production server.

Uses an SSH tunnel to connect the local Django application to the remote database.
"""

from pathlib import Path

import environ

from .dev import *

PROJECT_DIR = Path(__file__).resolve().parents[3]

production_env = environ.Env()
production_values = environ.Env.read_env(
    PROJECT_DIR / ".env",
    overwrite=True,
)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": production_env("POSTGRES_DB"),
        "USER": production_env("POSTGRES_USER"),
        "PASSWORD": production_env("POSTGRES_PASSWORD"),
        "HOST": "127.0.0.1",
        "PORT": "5433",
    }
}

REDIS_URL = "redis://127.0.0.1:6379/0"

CELERY_BROKER_URL = "redis://127.0.0.1:6379/1"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}
