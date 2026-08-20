import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "_config.settings")

django_asgi_app = get_asgi_application()

import messenger.routing
import video_chat.routing

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(video_chat.routing.websocket_urlpatterns + messenger.routing.websocket_urlpatterns)
        ),
    }
)
