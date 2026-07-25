import dj_database_url

from .dev import *

DEBUG = True

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL"),
        conn_max_age=60,
        conn_health_checks=True,
    )
}
