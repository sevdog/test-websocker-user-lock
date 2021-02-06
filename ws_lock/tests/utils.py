from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from ..consumers import ItemLockConsumer

User = get_user_model()
application = ItemLockConsumer.as_asgi()

def websocket_connect_to_asgi(application, user, url='/test', **kwargs):
    communicator = WebsocketCommunicator(application, url, **kwargs)
    communicator.scope['user'] = user
    return communicator
