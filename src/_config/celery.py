# src/_config/celery.py
import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_config.settings")

app = Celery("_config")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
