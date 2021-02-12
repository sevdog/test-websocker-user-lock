import threading
from collections import defaultdict
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from .models import Item, ItemLock, GroupTypeVisibility


def can_user_connect(user):
    print('db-connection-1', threading.get_ident())
    return user and not user.is_anonymous and user.is_active and user.has_perms([
        'ws_lock.view_itemlock',
        'ws_lock.add_itemlock',
        'ws_lock.change_itemlock',
        'ws_lock.view_item'
    ])


class ItemLockConsumer(AsyncJsonWebsocketConsumer):

    async def send_locks(self, locks):
        # group locks by item_type
        grouped_locks = defaultdict(list)
        for lock in locks:
            grouped_locks[lock.item.item_type].append(lock)

        # send each lock on its own group
        for group, group_locks in grouped_locks.items():
            payload = [{'item': l.item_id, 'user': l.user_id, 'locked': l.locked} for l in group_locks]
            await self.channel_layer.group_send(f'type-{group}', {'type': 'receive.locks', 'data': payload})

    async def receive_locks(self, event):
        print('send', threading.get_ident())
        await self.send_json(event['data'])

    @database_sync_to_async
    def connection_groups(self):
        """Connection groups based on current user"""
        print('db-connection-2', threading.get_ident())
        user = self.scope.get('user')
        if user is None or user.is_anonymous or not user.is_active:
            return []

        visible_types = GroupTypeVisibility.objects.filter(group__in=user.groups.all()).values_list('item_type', flat=True).distinct()
        return [f'type-{t}' for t in visible_types]

    async def websocket_connect(self, message):
        # set connection groups at runtime
        self.groups = await self.connection_groups()
        await super().websocket_connect(message)

    async def connect(self):
        user = self.scope.get('user')
        print('connect', threading.get_ident())
        accept = await database_sync_to_async(can_user_connect)(user)
        if accept:
            await super().connect()
        else:
            await self.close()

    @database_sync_to_async
    def _update_locks(self, items):
        print('db-connection-3', threading.get_ident())
        user = self.scope['user']
        # validate items by filtering with user-group-permission
        validated_items = list(
            Item.objects.filter(
                item_type__in=GroupTypeVisibility.objects.filter(group__in=user.groups.all()).values_list('item_type'),
                id__in=items
            ).values_list('id', flat=True)
        )
        # get pending locks
        pending_locks = user.lock_items.filter(locked=True)
        # left locks are those which item_id is no more present in received data
        left_locks_ids = list(pending_locks.exclude(item_id__in=validated_items).values_list('id', flat=True))
        pending_locks.exclude(item_id__in=validated_items).update(locked=False)
        # get which locks need to be created and then create them
        already_existing = set(ItemLock.objects.filter(locked=True, item_id__in=validated_items).values_list('item_id', flat=True))
        ItemLock.objects.bulk_create([
            ItemLock(user=user, item_id=item_id)
            for item_id in validated_items if item_id not in already_existing
        ])
        # get active ad left locks
        active_locks = list(pending_locks.select_related('item', 'user'))
        left_locks = list(user.lock_items.filter(id__in=left_locks_ids).select_related('item', 'user'))
        # return every lock which needs to be sent
        return active_locks + left_locks

    async def receive_json(self, content):
        items = content.get('items')
        if not isinstance(items, list):
            return

        # process locks and then re-send them
        print('receive', threading.get_ident())
        updated_locks = await self._update_locks(items)
        await self.send_locks(updated_locks)

    @database_sync_to_async
    def _leave_locks_on_close(self):
        print('db-connection-4', threading.get_ident())
        user = self.scope['user']
        # fetch locked elements from database
        user_locks = list(user.lock_items.filter(locked=True).select_related('item', 'user'))
        # update locks
        user.lock_items.filter(locked=True).update(locked=False)
        return user_locks

    async def disconnect(self, code):
        # clean all open inspections
        left_locks = await self._leave_locks_on_close()
        # send message to others
        print('disconnect', threading.get_ident())
        await self.send_locks(left_locks)
