from django.urls import re_path
from chat.consumers.signaling import SignalingConsumer
from chat.consumers.moderator import ModeratorConsumer

websocket_urlpatterns = [
    re_path(r"ws/chat/$", SignalingConsumer.as_asgi()),
    re_path(r"ws/chat/moderate/(?P<room_id>[^/]+)/$", ModeratorConsumer.as_asgi()),
]
