from collections import namedtuple
from async_generator import async_generator, yield_
import pytest
from django.core.management import call_command
from .utils import application, websocket_connect_to_asgi, User


ConnectionTuple = namedtuple('ConnectionTuple', ['user', 'communicator', 'connected'])


@pytest.fixture(scope='function')
def django_db_setup_for_sockets(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('loaddata', 'initial_setup')


@pytest.fixture(scope='function')
def ws_not_allowed_user(django_db_setup_for_sockets, django_db_blocker):
    with django_db_blocker.unblock():
        user = User.objects.get_by_natural_key('david')
        return user


@pytest.fixture(scope='function')
def ws_allowed_user_to_baz(django_db_setup_for_sockets, django_db_blocker):
    with django_db_blocker.unblock():
        user = User.objects.get_by_natural_key('alice')
        return user


@pytest.fixture(scope='function')
def ws_allowed_user_to_bar(django_db_setup_for_sockets, django_db_blocker):
    with django_db_blocker.unblock():
        user = User.objects.get_by_natural_key('bob')
        return user



@pytest.fixture(scope='function')
def ws_allowed_user_to_nothing(django_db_setup_for_sockets, django_db_blocker):
    with django_db_blocker.unblock():
        user = User.objects.get_by_natural_key('charlie')
        return user


@pytest.fixture(scope='function')
@async_generator
async def wrong_socket_user(ws_not_allowed_user):
    communicator = websocket_connect_to_asgi(application, ws_not_allowed_user)
    connected, _subprotocol = await communicator.connect()
    await yield_(
        ConnectionTuple(
            ws_not_allowed_user,
            communicator,
            connected
        )
    )
    await communicator.disconnect()


@pytest.fixture(scope='function')
@async_generator
async def allowed_socket_user_bar(ws_allowed_user_to_bar):
    communicator = websocket_connect_to_asgi(application, ws_allowed_user_to_bar)
    connected, _subprotocol = await communicator.connect()
    await yield_(
        ConnectionTuple(
            ws_allowed_user_to_bar,
            communicator,
            connected
        )
    )
    await communicator.disconnect()


@pytest.fixture(scope='function')
@async_generator
async def allowed_socket_user_baz(ws_allowed_user_to_baz):
    communicator = websocket_connect_to_asgi(application, ws_allowed_user_to_baz)
    connected, _subprotocol = await communicator.connect()
    await yield_(
        ConnectionTuple(
            ws_allowed_user_to_baz,
            communicator,
            connected
        )
    )
    await communicator.disconnect()


@pytest.fixture(scope='function')
@async_generator
async def allowed_socket_user_nothinh(ws_allowed_user_to_nothing):
    communicator = websocket_connect_to_asgi(application, ws_allowed_user_to_nothing)
    connected, _subprotocol = await communicator.connect()
    await yield_(
        ConnectionTuple(
            ws_allowed_user_to_nothing,
            communicator,
            connected
        )
    )
    await communicator.disconnect()
