import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

# All money fields are stored in kobo (1 naira = 100 kobo) as whole numbers.
# All percentages are stored in basis points (1% = 100, 10% = 1000, 100% = 10000).


class PricingSetting(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    digital_card_fee = models.BigIntegerField(
        default=5000, help_text='Card creation fee per digital card, in kobo'
    )
    physical_card_fee = models.BigIntegerField(
        null=True, blank=True,
        help_text='Card creation fee per physical card, in kobo. Empty until decided',
    )
    cashback_rate_bp = models.PositiveIntegerField(
        default=100, help_text='Cashback on eligible fees, in basis points (100 = 1%)'
    )
    business_charge_bp = models.PositiveIntegerField(
        default=200, help_text='Business transaction charge, in basis points (200 = 2%)'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'pricing settings'
        verbose_name_plural = 'pricing settings'
        constraints = [
            models.CheckConstraint(condition=Q(id=1), name='only_one_pricing_row'),
            models.CheckConstraint(
                condition=Q(cashback_rate_bp__lte=10000) & Q(business_charge_bp__lte=10000),
                name='pricing_rates_max_100_percent',
            ),
        ]

    def __str__(self):
        return 'Pricing settings'

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj


class DiscountTier(models.Model):
    min_quantity = models.PositiveIntegerField(unique=True)
    max_quantity = models.PositiveIntegerField(
        null=True, blank=True, help_text='Leave empty for "and above"'
    )
    discount_bp = models.PositiveIntegerField(
        help_text='Discount in basis points (1000 = 10%)'
    )

    class Meta:
        ordering = ['min_quantity']
        constraints = [
            models.CheckConstraint(
                condition=Q(min_quantity__gte=1),
                name='tier_min_at_least_one',
            ),
            models.CheckConstraint(
                condition=Q(max_quantity__isnull=True)
                | Q(max_quantity__gte=F('min_quantity')),
                name='tier_max_not_below_min',
            ),
            models.CheckConstraint(
                condition=Q(discount_bp__lte=10000),
                name='tier_discount_max_100_percent',
            ),
        ]

    def __str__(self):
        upper = self.max_quantity if self.max_quantity else 'and above'
        return f'{self.min_quantity} to {upper} cards: {self.discount_bp / 100}%'


class Wallet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='wallet',
    )
    available = models.BigIntegerField(default=0, help_text='Amount in kobo')
    committed = models.BigIntegerField(default=0, help_text='Amount in kobo')
    locked = models.BigIntegerField(default=0, help_text='Amount in kobo')
    cashback_balance = models.BigIntegerField(
        default=0, help_text='Cashback waiting to be withdrawn, in kobo'
    )
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
            models.CheckConstraint(
                condition=Q(cashback_balance__gte=0),
                name='wallet_cashback_not_negative',
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
    amount = models.BigIntegerField(help_text='Amount in kobo, always positive')
    available_change = models.BigIntegerField(default=0, help_text='Kobo, plus or minus')
    committed_change = models.BigIntegerField(default=0, help_text='Kobo, plus or minus')
    locked_change = models.BigIntegerField(default=0, help_text='Kobo, plus or minus')
    card = models.ForeignKey(
        'cards.Card',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='wallet_entries',
    )
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
    card_value = models.BigIntegerField(default=0, help_text='Amount in kobo')
    card_creation_fee_per_card = models.BigIntegerField(
        default=0, help_text='Rate used for this payment, in kobo'
    )
    card_creation_fee = models.BigIntegerField(
        default=0, help_text='Total creation fee before discount, in kobo'
    )
    discount_bp = models.PositiveIntegerField(
        default=0, help_text='Bulk discount applied, in basis points'
    )
    discount_amount = models.BigIntegerField(
        default=0, help_text='Amount taken off the creation fee, in kobo'
    )
    printing_fee_per_card = models.BigIntegerField(default=0, help_text='Amount in kobo')
    printing_fee = models.BigIntegerField(default=0, help_text='Amount in kobo')
    delivery_fee = models.BigIntegerField(default=0, help_text='Amount in kobo')
    platform_fee = models.BigIntegerField(default=0, help_text='Amount in kobo')
    paystack_fee = models.BigIntegerField(default=0, help_text='Amount in kobo')
    total_charged = models.BigIntegerField(help_text='Amount in kobo')
    cashback_earned = models.BigIntegerField(
        default=0, help_text='Cashback earned on this payment, in kobo'
    )
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
                    + F('card_creation_fee')
                    - F('discount_amount')
                    + F('printing_fee')
                    + F('delivery_fee')
                    + F('platform_fee')
                    + F('paystack_fee')
                ),
                name='payment_total_matches_parts',
            ),
            models.CheckConstraint(
                condition=Q(discount_amount__gte=0)
                & Q(discount_amount__lte=F('card_creation_fee')),
                name='payment_discount_within_fee',
            ),
            models.CheckConstraint(
                condition=Q(cashback_earned__gte=0),
                name='payment_cashback_not_negative',
            ),
        ]

    def __str__(self):
        return f'{self.paystack_reference} ({self.status})'


class WithdrawalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='withdrawal_requests',
    )
    amount = models.BigIntegerField(help_text='Amount in kobo')
    bank_name = models.CharField(max_length=100)
    bank_code = models.CharField(max_length=10, help_text='Paystack bank code')
    account_number = models.CharField(max_length=10)
    account_name = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    paystack_transfer_reference = models.CharField(
        max_length=100, unique=True, null=True, blank=True
    )
    failure_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'status'])]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='withdrawal_amount_positive',
            ),
        ]

    def __str__(self):
        return f'{self.user} withdraws {self.amount} ({self.status})'


class CashbackEntry(models.Model):
    class EntryType(models.TextChoices):
        EARNED = 'earned', 'Earned'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        RETURNED = 'returned', 'Returned after failed withdrawal'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name='cashback_entries',
    )
    entry_type = models.CharField(max_length=20, choices=EntryType.choices)
    amount = models.BigIntegerField(help_text='Kobo. Plus for money in, minus for money out')
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cashback_entries',
    )
    withdrawal = models.ForeignKey(
        WithdrawalRequest,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cashback_entries',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'cashback entries'
        ordering = ['-created_at']
        indexes = [models.Index(fields=['wallet', 'created_at'])]

    def __str__(self):
        return f'{self.wallet} cashback {self.entry_type} {self.amount}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Ledger entries cannot be edited. Add a correcting entry instead.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Ledger entries cannot be deleted.')