import os
import dj_database_url
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Безопасность ────────────────────────────────────────────────────────────
# На проде SECRET_KEY берётся из переменной окружения.
# На локалке используется insecure ключ — это нормально для разработки.
SECRET_KEY = os.environ.get(
    "SECRET_KEY", "django-insecure-6jx&gw$s)0gyqqm0@dxmw%@cllm7cf4fi9x2b2&zz&cf$szbgj"
)

# На проде DEBUG=False берётся из env.
# Если переменная не задана — True (локалка)
DEBUG = os.environ.get("DEBUG", "True") == "True"

# На проде передаём через env: ALLOWED_HOSTS=example.com,www.example.com
# На локалке разрешаем всё
_allowed = os.environ.get("ALLOWED_HOSTS", "")
ALLOWED_HOSTS = _allowed.split(",") if _allowed else ["*"]

# ── Приложения ──────────────────────────────────────────────────────────────
# ВАЖНО: daphne должен быть ПЕРВЫМ — он перехватывает runserver
# и запускает ASGI вместо WSGI
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
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
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
            ],
        },
    },
]

WSGI_APPLICATION = "_config.wsgi.application"
ASGI_APPLICATION = "_config.asgi.application"

# ── База данных ─────────────────────────────────────────────────────────────
# Если задана переменная DATABASE_URL — используем её (прод, PostgreSQL).
# Формат: postgres://user:password@host:5432/dbname
# Если нет — SQLite (локалка).
_database_url = os.environ.get("DATABASE_URL")
if _database_url:
    DATABASES = {
        "default": dj_database_url.parse(
            _database_url,
            conn_max_age=600,  # Держим соединения 10 минут (пул)
            conn_health_checks=True,  # Проверяем соединение перед использованием
        )
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ── Пароли ──────────────────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ── Интернационализация ──────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ── Статика ─────────────────────────────────────────────────────────────────
STATIC_URL = "static/"

# Папки откуда Django собирает статику в dev
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Куда collectstatic копирует всю статику для nginx на проде
STATIC_ROOT = BASE_DIR / "staticfiles"

# ── Django Channels + Redis ──────────────────────────────────────────────────
# channel layer — шина сообщений между WebSocket workers через Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [os.environ.get("REDIS_URL", "redis://localhost:6379/0")],
        },
    },
}

# ── Логирование ──────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "ERROR",
    },
}

# ── Авторизация ──────────────────────────────────────────────────────────────
# Неавторизованных редиректим на страницу логина админки
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/chat/moderate/"

# ── Продовые настройки безопасности ─────────────────────────────────────────
# Включаются автоматически когда DEBUG=False
if not DEBUG:
    # Принудительно перенаправлять HTTP → HTTPS
    SECURE_SSL_REDIRECT = True
    # Браузер запоминает что сайт только HTTPS (1 год)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # Cookie сессии только по HTTPS
    SESSION_COOKIE_SECURE = True
    # CSRF cookie только по HTTPS
    CSRF_COOKIE_SECURE = True
    # Доверяем заголовку от nginx что соединение было HTTPS
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    # Список доменов которым доверяем для CSRF (нужен для POST запросов)
    CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS if host != "*"]
