import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wallet',
    )
    available = models.BigIntegerField(default=0)
    committed = models.BigIntegerField(default=0)
    locked = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(available__gte=0),
                name='wallet_available_not_negative',
            ),
            models.CheckConstraint(
                condition=Q(committed__gte=0),
                name='wallet_committed_not_negative',
            ),
            models.CheckConstraint(
                condition=Q(locked__gte=0),
                name='wallet_locked_not_negative',
            ),
        ]

    def __str__(self):
        return f'Wallet of {self.user}'

    @property
    def total(self):
        return self.available + self.committed + self.locked


class WalletEntry(models.Model):
    class EntryType(models.TextChoices):
        FUNDED = 'funded', 'Funded'
        COMMITTED = 'committed', 'Committed'
        REDEEMED = 'redeemed', 'Redeemed'
        RELEASED = 'released', 'Released'
        REFUNDED = 'refunded', 'Refunded'
        LOCKED = 'locked', 'Locked'
        REISSUED = 'reissued', 'Reissued'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='entries',
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    amount = models.BigIntegerField()
    available_change = models.BigIntegerField(default=0)
    committed_change = models.BigIntegerField(default=0)
    locked_change = models.BigIntegerField(default=0)
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='wallet_entries',
    )
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'wallet entries'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['wallet', 'created_at'])]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='wallet_entry_amount_positive',
            ),
        ]

    def __str__(self):
        return f'{self.wallet} {self.entry_type} {self.amount}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Ledger entries cannot be edited. Add a correcting entry instead.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Ledger entries cannot be deleted.')


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    giver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments',
    )
    paystack_reference = models.CharField(max_length=100, unique=True)
    card_value = models.BigIntegerField(default=0)
    printing_fee_per_card = models.BigIntegerField(default=0)
    printing_fee = models.BigIntegerField(default=0)
    delivery_fee = models.BigIntegerField(default=0)
    platform_fee = models.BigIntegerField(default=0)
    paystack_fee = models.BigIntegerField(default=0)
    total_charged = models.BigIntegerField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['giver', 'status'])]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    total_charged=F('card_value')
                    + F('printing_fee')
                    + F('delivery_fee')
                    + F('platform_fee')
                    + F('paystack_fee')
                ),
                name='payment_total_matches_parts',
            ),
        ]

    def __str__(self):
        return f'{self.paystack_reference} ({self.status})'