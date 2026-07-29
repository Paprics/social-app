from pathlib import Path

from django.utils.translation import gettext_lazy as _

from .env import env

BASE_DIR = Path(__file__).resolve().parents[2]  # src/

SECRET_KEY = env("SECRET_KEY")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core.apps.CoreConfig",
    "chat.apps.ChatConfig",
    "cms.apps.CmsConfig",
    "tinymce",
    "geo.apps.GeoConfig",
    "rosetta",
    "users.apps.UsersConfig",
    "accounts.apps.AccountsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "_config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "users.context_processors.user_settings",
            ],
        },
    },
]

WSGI_APPLICATION = "_config.wsgi.application"
ASGI_APPLICATION = "_config.asgi.application"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [env("REDIS_URL", default="redis://localhost:6379/0")],
        },
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",  # в DEBUG=True окружении
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

LOGIN_URL = "/"
# LOGIN_REDIRECT_URL = "/chat/moderate/"

TIME_ZONE = "UTC"

LANGUAGE_EN = "en"
LANGUAGE_RU = "ru"
LANGUAGE_UK = "uk"


LANGUAGE_CODE = LANGUAGE_EN

LANGUAGES = [
    (LANGUAGE_EN, _("English")),
    (LANGUAGE_RU, _("Russian")),
    (LANGUAGE_UK, _("Ukrainian")),
]

USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

# ====== EMEIL ============
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT")

EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")

EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS")

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

# Gallery
# Image processing
GALLERY_MAX_PHOTOS = 10
GALLERY_IMAGE_MAX_SIZE = 1200
GALLERY_IMAGE_FORMAT = "WEBP"
GALLERY_IMAGE_QUALITY = 82
GALLERY_IMAGE_STRIP_METADATA = True
MAX_PHOTO_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

GEO_ALLOWED_COUNTRIES = ["UA", "PL", "CZ", "DE", "RU"]
