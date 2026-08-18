# src/video_chat/routing.py

from django.urls import re_path

from video_chat.consumers.moderator import ModeratorConsumer
from video_chat.consumers.signaling import SignalingConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/$", SignalingConsumer.as_asgi()),
    re_path(r"ws/chat/moderate/(?P<room_id>[^/]+)/$", ModeratorConsumer.as_asgi()),
]
