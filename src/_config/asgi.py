import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

import video_chat.routing
import messenger.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_config.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(video_chat.routing.websocket_urlpatterns + messenger.routing.websocket_urlpatterns)
        ),
    }
)
