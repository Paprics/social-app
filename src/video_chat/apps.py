# src/video_chat/apps.py

"""Конфигурация Django-приложения видеочата."""

from django.apps import AppConfig


class VideoChatConfig(AppConfig):
    """Конфигурация приложения видеочата."""

    name = "video_chat"
    verbose_name = "Video Chat"
