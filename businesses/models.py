import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Business(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACTIVE = 'active', 'Active'
        PAUSED = 'paused', 'Paused'
        REMOVED = 'removed', 'Removed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='business',
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='businesses',
    )
    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    redemption_password_hash = models.CharField(max_length=128, blank=True)
    float_balance = models.BigIntegerField(default=0)
    low_float_threshold = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'businesses'
        indexes = [models.Index(fields=['status'])]

    def __str__(self):
        return self.name

    def set_redemption_password(self, raw_password):
        self.redemption_password_hash = make_password(raw_password)

    def check_redemption_password(self, raw_password):
        return check_password(raw_password, self.redemption_password_hash)

    @property
    def is_float_low(self):
        return self.float_balance <= self.low_float_threshold


class FloatEntry(models.Model):
    class EntryType(models.TextChoices):
        DEPOSIT = 'deposit', 'Deposit'
        REDEMPTION_DRAW = 'redemption_draw', 'Redemption draw'
        TOP_UP = 'top_up', 'Top up'
        OVERDRAFT_COVER = 'overdraft_cover', 'Overdraft cover'
        ADJUSTMENT = 'adjustment', 'Adjustment'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name='float_entries',
    )
    entry_type = models.CharField(max_length=30, choices=EntryType.choices)
    amount = models.BigIntegerField()
    balance_after = models.BigIntegerField()
    redemption = models.ForeignKey(
        'cards.Redemption',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='float_entries',
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'float entries'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['business', 'created_at'])]

    def __str__(self):
        return f'{self.business} {self.entry_type} {self.amount}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Ledger entries cannot be edited. Add a correcting entry instead.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Ledger entries cannot be deleted.')


class TopUpRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        REJECTED = 'rejected', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name='top_up_requests',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.business} top-up ({self.status})'