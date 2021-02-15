import threading
from asgiref.sync import sync_to_async
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from ..models import Item
from .utils import application, websocket_connect_to_asgi, User


class TestLocks(TestCase):
    fixtures = ['initial_setup']

    @classmethod
    def setUpTestData(cls):
        print('test-setup', threading.get_ident())
        cls.USERS = {
            username: User.objects.get_by_natural_key(username)
            for username in ['alice', 'bob', 'charlie', 'david']
        }

    async def test_fetch(self):
        @sync_to_async
        def fetch():
            return list(Item.objects.all())

        items = await fetch()
        assert len(items) == 8

    async def test_denied_access(self):
        print('test', threading.get_ident())
        communicator = websocket_connect_to_asgi(application, self.USERS['david'])
        connected, _subprotocol = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_shared_bar_baz(self):
        communicator_baz = websocket_connect_to_asgi(application, self.USERS['alice'])
        connected, _subprotocol = await communicator_baz.connect()
        self.assertTrue(connected)
        communicator_bar = websocket_connect_to_asgi(application, self.USERS['bob'])
        connected, _subprotocol = await communicator_bar.connect()
        self.assertTrue(connected)
        # item 3 is FOO
        await communicator_bar.send_json_to({'items': [3]})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == received_baz == [{
            'user': self.USERS['bob'].id,
            'item': 3,
            'locked': True
        }]
        # leave lock
        await communicator_bar.send_json_to({'items': []})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == received_baz == [{
            'user': self.USERS['bob'].id,
            'item': 3,
            'locked': False
        }]

        await communicator_baz.disconnect()
        await communicator_bar.disconnect()

    async def test_unshared_bar_baz(self):
        communicator_baz = websocket_connect_to_asgi(application, self.USERS['alice'])
        connected, _subprotocol = await communicator_baz.connect()
        self.assertTrue(connected)
        communicator_bar = websocket_connect_to_asgi(application, self.USERS['bob'])
        connected, _subprotocol = await communicator_bar.connect()
        self.assertTrue(connected)
        # item 7 is BAZ
        await communicator_baz.send_json_to({'items': [7]})
        assert await communicator_bar.receive_nothing()
        received_baz = await communicator_baz.receive_json_from()
        assert received_baz == [{
            'user': self.USERS['alice'].id,
            'item': 7,
            'locked': True
        }]
        # leave lock
        await communicator_baz.send_json_to({'items': []})
        assert await communicator_bar.receive_nothing()
        received_baz = await communicator_baz.receive_json_from()
        assert received_baz == [{
            'user': self.USERS['alice'].id,
            'item': 7,
            'locked': False
        }]

        await communicator_baz.disconnect()
        await communicator_bar.disconnect()

    async def test_multiple_bar_baz(self):
        communicator_baz = websocket_connect_to_asgi(application, self.USERS['alice'])
        connected, _subprotocol = await communicator_baz.connect()
        self.assertTrue(connected)
        communicator_bar = websocket_connect_to_asgi(application, self.USERS['bob'])
        connected, _subprotocol = await communicator_bar.connect()
        self.assertTrue(connected)
        # item 7 is BAZ, item 3 is FOO
        await communicator_baz.send_json_to({'items': [3, 7]})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == [{
            'user': self.USERS['alice'].id,
            'item': 3,
            'locked': True
        }]
        assert received_baz == [{
            'user': self.USERS['alice'].id,
            'item': 3,
            'locked': True
        }]
        assert await communicator_bar.receive_nothing()
        received_baz = await communicator_baz.receive_json_from()
        assert received_baz == [{
            'user': self.USERS['alice'].id,
            'item': 7,
            'locked': True
        }]
        # leave lock
        await communicator_baz.send_json_to({'items': []})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == [{
            'user': self.USERS['alice'].id,
            'item': 3,
            'locked': False
        }]
        assert received_baz == [{
            'user': self.USERS['bob'].id,
            'item': 3,
            'locked': False
        }]
        assert await communicator_bar.receive_nothing()
        received_baz = await communicator_baz.receive_json_from()
        assert received_baz == [{
            'user': self.USERS['bob'].id,
            'item': 7,
            'locked': False
        }]

        await communicator_baz.disconnect()
        await communicator_bar.disconnect()

    async def test_shared_no_conflict_bar_baz(self):
        communicator_baz = websocket_connect_to_asgi(application, self.USERS['alice'])
        connected, _subprotocol = await communicator_baz.connect()
        self.assertTrue(connected)
        communicator_bar = websocket_connect_to_asgi(application, self.USERS['bob'])
        connected, _subprotocol = await communicator_bar.connect()
        self.assertTrue(connected)
        # item 3 is FOO
        await communicator_bar.send_json_to({'items': [3]})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == received_baz == [{
            'user': self.USERS['bob'].id,
            'item': 3,
            'locked': True
        }]
        # item 3 already locked
        await communicator_baz.send_json_to({'items': [3]})
        assert await communicator_bar.receive_nothing()
        assert await communicator_baz.receive_nothing()

        await communicator_baz.disconnect()
        await communicator_bar.disconnect()

class TestLocksInTransaction(TransactionTestCase):
    fixtures = ['initial_setup']

    @sync_to_async
    def _get_user(self, username):
        return User.objects.get_by_natural_key(username)

    async def test_fetch(self):
        @sync_to_async
        def fetch():
            return list(Item.objects.all())

        items = await fetch()
        assert len(items) == 8

    async def test_denied_access(self):
        print('test', threading.get_ident())
        communicator = websocket_connect_to_asgi(application, await self._get_user('david'))
        connected, _subprotocol = await communicator.connect()
        self.assertFalse(connected)
        await communicator.disconnect()

    async def test_shared_bar_baz(self):
        user_baz = await self._get_user('alice')
        communicator_baz = websocket_connect_to_asgi(application, user_baz)
        connected, _subprotocol = await communicator_baz.connect()
        self.assertTrue(connected)
        user_bar = await self._get_user('bob')
        communicator_bar = websocket_connect_to_asgi(application, user_bar)
        connected, _subprotocol = await communicator_bar.connect()
        self.assertTrue(connected)
        # item 3 is FOO
        await communicator_bar.send_json_to({'items': [3]})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == received_baz == [{
            'user': user_bar.id,
            'item': 3,
            'locked': True
        }]
        # leave lock
        await communicator_bar.send_json_to({'items': []})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == received_baz == [{
            'user': user_bar.id,
            'item': 3,
            'locked': False
        }]

        await communicator_baz.disconnect()
        await communicator_bar.disconnect()

    async def test_unshared_bar_baz(self):
        user_baz = await self._get_user('alice')
        communicator_baz = websocket_connect_to_asgi(application, user_baz)
        connected, _subprotocol = await communicator_baz.connect()
        self.assertTrue(connected)
        user_bar = await self._get_user('bob')
        communicator_bar = websocket_connect_to_asgi(application, user_bar)
        connected, _subprotocol = await communicator_bar.connect()
        self.assertTrue(connected)
        # item 7 is BAZ
        await communicator_baz.send_json_to({'items': [7]})
        assert await communicator_bar.receive_nothing()
        received_baz = await communicator_baz.receive_json_from()
        assert received_baz == [{
            'user': user_baz.id,
            'item': 7,
            'locked': True
        }]
        # leave lock
        await communicator_baz.send_json_to({'items': []})
        assert await communicator_bar.receive_nothing()
        received_baz = await communicator_baz.receive_json_from()
        assert received_baz == [{
            'user': user_baz.id,
            'item': 7,
            'locked': False
        }]

        await communicator_baz.disconnect()
        await communicator_bar.disconnect()

    async def test_multiple_bar_baz(self):
        user_baz = await self._get_user('alice')
        communicator_baz = websocket_connect_to_asgi(application, user_baz)
        connected, _subprotocol = await communicator_baz.connect()
        self.assertTrue(connected)
        user_bar = await self._get_user('bob')
        communicator_bar = websocket_connect_to_asgi(application, user_bar)
        connected, _subprotocol = await communicator_bar.connect()
        self.assertTrue(connected)
        # item 7 is BAZ, item 3 is FOO
        await communicator_baz.send_json_to({'items': [3, 7]})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == [{
            'user': user_baz.id,
            'item': 3,
            'locked': True
        }]
        assert received_baz == [{
            'user': user_baz.id,
            'item': 3,
            'locked': True
        }]
        assert await communicator_bar.receive_nothing()
        received_baz = await communicator_baz.receive_json_from()
        assert received_baz == [{
            'user': user_baz.id,
            'item': 7,
            'locked': True
        }]
        # leave lock
        await communicator_baz.send_json_to({'items': []})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == [{
            'user': user_baz.id,
            'item': 3,
            'locked': False
        }]
        assert received_baz == [{
            'user': user_baz.id,
            'item': 3,
            'locked': False
        }]
        assert await communicator_bar.receive_nothing()
        received_baz = await communicator_baz.receive_json_from()
        assert received_baz == [{
            'user': user_baz.id,
            'item': 7,
            'locked': False
        }]

        await communicator_baz.disconnect()
        await communicator_bar.disconnect()

    async def test_shared_no_conflict_bar_baz(self):
        user_baz = await self._get_user('alice')
        communicator_baz = websocket_connect_to_asgi(application, user_baz)
        connected, _subprotocol = await communicator_baz.connect()
        self.assertTrue(connected)
        user_bar = await self._get_user('bob')
        communicator_bar = websocket_connect_to_asgi(application, user_bar)
        connected, _subprotocol = await communicator_bar.connect()
        self.assertTrue(connected)
        # item 3 is FOO
        await communicator_bar.send_json_to({'items': [3]})
        received_bar = await communicator_bar.receive_json_from()
        received_baz = await communicator_baz.receive_json_from()
        assert received_bar == received_baz == [{
            'user': user_bar.id,
            'item': 3,
            'locked': True
        }]
        # item 3 already locked
        await communicator_baz.send_json_to({'items': [3]})
        assert await communicator_bar.receive_nothing()
        assert await communicator_baz.receive_nothing()

        await communicator_baz.disconnect()
        await communicator_bar.disconnect()