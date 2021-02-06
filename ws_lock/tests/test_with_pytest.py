import pytest


@pytest.mark.django_db(transaction=True)
class TestLocks:

    @pytest.mark.asyncio
    async def test_denied_access(self, wrong_socket_user):
        assert wrong_socket_user.connected is False

    @pytest.mark.asyncio
    async def test_shared_bar_baz(self, allowed_socket_user_baz, allowed_socket_user_bar):
        assert allowed_socket_user_baz.connected is True
        assert allowed_socket_user_bar.connected is True
        # item 3 is FOO
        await allowed_socket_user_bar.communicator.send_json_to({'items': [3]})
        received_bar = await allowed_socket_user_bar.communicator.receive_json_from()
        received_baz = await allowed_socket_user_baz.communicator.receive_json_from()
        assert received_bar == received_baz == [{
            'user': allowed_socket_user_bar.user.id,
            'item': 3,
            'locked': True
        }]
        # leave lock
        await allowed_socket_user_bar.communicator.send_json_to({'items': []})
        received_bar = await allowed_socket_user_bar.communicator.receive_json_from()
        received_baz = await allowed_socket_user_baz.communicator.receive_json_from()
        assert received_bar == received_baz == [{
            'user': allowed_socket_user_bar.user.id,
            'item': 3,
            'locked': False
        }]

    @pytest.mark.asyncio
    async def test_unshared_bar_baz(self, allowed_socket_user_baz, allowed_socket_user_bar):
        assert allowed_socket_user_baz.connected is True
        assert allowed_socket_user_bar.connected is True
        # item 7 is BAZ
        await allowed_socket_user_baz.communicator.send_json_to({'items': [7]})
        assert await allowed_socket_user_bar.communicator.receive_nothing()
        received_baz = await allowed_socket_user_baz.communicator.receive_json_from()
        assert received_baz == [{
            'user': allowed_socket_user_baz.user.id,
            'item': 7,
            'locked': True
        }]
        # leave lock
        await allowed_socket_user_baz.communicator.send_json_to({'items': []})
        assert await allowed_socket_user_bar.communicator.receive_nothing()
        received_baz = await allowed_socket_user_baz.communicator.receive_json_from()
        assert received_baz == [{
            'user': allowed_socket_user_baz.user.id,
            'item': 7,
            'locked': False
        }]

    @pytest.mark.asyncio
    async def test_multiple_bar_baz(self, allowed_socket_user_baz, allowed_socket_user_bar):
        assert allowed_socket_user_baz.connected is True
        assert allowed_socket_user_bar.connected is True
        # item 7 is BAZ, item 3 is FOO
        await allowed_socket_user_baz.communicator.send_json_to({'items': [3, 7]})
        received_bar = await allowed_socket_user_bar.communicator.receive_json_from()
        received_baz = await allowed_socket_user_baz.communicator.receive_json_from()
        assert received_bar == [{
            'user': allowed_socket_user_baz.user.id,
            'item': 3,
            'locked': True
        }]
        assert received_baz == [{
            'user': allowed_socket_user_baz.user.id,
            'item': 3,
            'locked': True
        }, {
            'user': allowed_socket_user_baz.user.id,
            'item': 7,
            'locked': True
        }]
        # leave lock
        await allowed_socket_user_baz.communicator.send_json_to({'items': []})
        received_bar = await allowed_socket_user_bar.communicator.receive_json_from()
        received_baz = await allowed_socket_user_baz.communicator.receive_json_from()
        assert received_bar == [{
            'user': allowed_socket_user_baz.user.id,
            'item': 3,
            'locked': False
        }]
        assert received_baz == [{
            'user': allowed_socket_user_bar.user.id,
            'item': 3,
            'locked': False
        }, {
            'user': allowed_socket_user_bar.user.id,
            'item': 7,
            'locked': False
        }]

    @pytest.mark.asyncio
    async def test_shared_no_conflict_bar_baz(self, allowed_socket_user_baz, allowed_socket_user_bar):
        assert allowed_socket_user_baz.connected is True
        assert allowed_socket_user_bar.connected is True
        # item 3 is FOO
        await allowed_socket_user_bar.communicator.send_json_to({'items': [3]})
        received_bar = await allowed_socket_user_bar.communicator.receive_json_from()
        received_baz = await allowed_socket_user_baz.communicator.receive_json_from()
        assert received_bar == received_baz == [{
            'user': allowed_socket_user_bar.user.id,
            'item': 3,
            'locked': True
        }]
        # item 3 already locked
        await allowed_socket_user_baz.communicator.send_json_to({'items': [3]})
        assert await allowed_socket_user_bar.communicator.receive_nothing()
        assert await allowed_socket_user_baz.communicator.receive_nothing()
