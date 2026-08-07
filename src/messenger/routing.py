# src/messenger/routing.py

from django.urls import re_path

from messenger.consumers.dialog_consumer import DialogConsumer

websocket_urlpatterns = [
    re_path(
        r"ws/messenger/(?P<public_id>[a-zA-Z0-9]+)/$",
        DialogConsumer.as_asgi(),
    ),
]
