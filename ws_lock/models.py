from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class ItemTypes(models.IntegerChoices):
    BOO = 1
    FOO = 2
    BAR = 3
    BAZ = 4


class GroupTypeVisibility(models.Model):
    item_type = models.PositiveSmallIntegerField(choices=ItemTypes.choices, default=ItemTypes.BOO)
    group = models.ForeignKey(Group, related_name='visible_types', on_delete=models.CASCADE)

    class Meta:
        unique_together = (('item_type', 'group'), )


class Item(models.Model):
    item_type = models.PositiveSmallIntegerField(choices=ItemTypes.choices, default=ItemTypes.BOO)

    def __str__(self):
        return f'{ItemTypes(self.item_type).label}@{self.id}'


class ItemLock(models.Model):
    locked = models.BooleanField(default=True)
    item = models.ForeignKey(Item, related_name='locks', on_delete=models.CASCADE)
    user = models.ForeignKey(User, related_name='lock_items', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Lock on {self.item} by {self.user}'
