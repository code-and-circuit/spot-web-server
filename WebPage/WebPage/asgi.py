"""
ASGI config for WebPage project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""




import os
import signal
from uvicorn.main import Server

import django
from django.core.asgi import get_asgi_application
from SpotSite.middleware import websockets
import SpotSite.spot_logging as l

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WebPage.settings')

django.setup()

from SpotSite import websocket as ws
from SpotSite import background_process





application = get_asgi_application()
application = websockets(application)

original_handler = Server.handle_exit


class AppStatus:
    should_exit = False

    @staticmethod
    def handle_exit(*args, **kwargs):
        AppStatus.should_exit = True
        ws.close_all_sockets()
        background_process.close()
        original_handler(*args, **kwargs)


Server.handle_exit = AppStatus.handle_exit
