import secrets
import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

CODE_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_card_code():
    return ''.join(secrets.choice(CODE_ALPHABET) for _ in range(12))


def generate_serial_number():
    return 'PK' + ''.join(secrets.choice('0123456789') for _ in range(10))


class CardType(models.TextChoices):
    DIGITAL = 'digital', 'Digital'
    PHYSICAL = 'physical', 'Physical'


class CardBatch(models.Model):
    class Kind(models.TextChoices):
        PREPAID = 'prepaid', 'Prepaid'
        EMPTY = 'empty', 'Empty'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    giver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='card_batches',
    )
    payment = models.ForeignKey(
        'wallets.Payment',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='card_batches',
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    card_type = models.CharField(max_length=20, choices=CardType.choices)
    quantity = models.PositiveIntegerField()
    value_per_card = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'card batches'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name='batch_quantity_positive',
            ),
            models.CheckConstraint(
                condition=Q(value_per_card__gte=0),
                name='batch_value_not_negative',
            ),
        ]

    def __str__(self):
        return f'{self.quantity} {self.card_type} cards ({self.kind})'


class Card(models.Model):
    class Status(models.TextChoices):
        INACTIVE = 'inactive', 'Inactive'
        ACTIVE = 'active', 'Active'
        REDEEMED = 'redeemed', 'Redeemed'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
        LOST = 'lost', 'Lost'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    giver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cards',
    )
    batch = models.ForeignKey(
        CardBatch,
        on_delete=models.PROTECT,
        related_name='cards',
    )
    serial_number = models.CharField(
        max_length=20, unique=True, default=generate_serial_number
    )
    code = models.CharField(max_length=20, unique=True, default=generate_card_code)
    card_type = models.CharField(max_length=20, choices=CardType.choices)
    face_value = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INACTIVE
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cards',
    )
    category = models.ForeignKey(
        'businesses.Category',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cards',
    )
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_contact = models.CharField(max_length=200, blank=True)
    replaces = models.OneToOneField(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='replaced_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['giver', 'status']),
            models.Index(fields=['batch']),
            models.Index(fields=['status', 'expires_at']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~(Q(business__isnull=False) & Q(category__isnull=False)),
                name='card_not_both_business_and_category',
            ),
            models.CheckConstraint(
                condition=Q(status__in=['inactive', 'cancelled', 'lost'])
                | Q(business__isnull=False)
                | Q(category__isnull=False),
                name='card_in_use_has_business_or_category',
            ),
            models.CheckConstraint(
                condition=Q(face_value__gte=0),
                name='card_face_value_not_negative',
            ),
        ]

    def __str__(self):
        return f'{self.serial_number} ({self.status})'


class Redemption(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    card = models.OneToOneField(
        Card,
        on_delete=models.PROTECT,
        related_name='redemption',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        related_name='redemptions',
    )
    amount_spent = models.BigIntegerField()
    leftover = models.BigIntegerField(default=0)
    cashback_amount = models.BigIntegerField(default=0)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-redeemed_at']
        indexes = [models.Index(fields=['business', 'redeemed_at'])]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_spent__gt=0),
                name='redemption_amount_positive',
            ),
            models.CheckConstraint(
                condition=Q(leftover__gte=0),
                name='redemption_leftover_not_negative',
            ),
            models.CheckConstraint(
                condition=Q(cashback_amount__gte=0),
                name='redemption_cashback_not_negative',
            ),
        ]

    def __str__(self):
        return f'{self.card} at {self.business}'


class CardDelivery(models.Model):
    class Channel(models.TextChoices):
        WHATSAPP = 'whatsapp', 'WhatsApp'
        EMAIL = 'email', 'Email'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    card = models.ForeignKey(
        Card,
        on_delete=models.PROTECT,
        related_name='deliveries',
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    destination = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'card deliveries'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.card} by {self.channel} ({self.status})'


class PhysicalShipment(models.Model):
    class DeliverTo(models.TextChoices):
        GIVER = 'giver', 'Giver'
        RECIPIENT = 'recipient', 'Recipient'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SHIPPED = 'shipped', 'Shipped'
        DELIVERED = 'delivered', 'Delivered'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deliver_to = models.CharField(max_length=20, choices=DeliverTo.choices)
    batch = models.ForeignKey(
        CardBatch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='shipments',
    )
    card = models.ForeignKey(
        Card,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='shipments',
    )
    address = models.TextField()
    tracking_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=(Q(batch__isnull=False) & Q(card__isnull=True))
                | (Q(batch__isnull=True) & Q(card__isnull=False)),
                name='shipment_is_batch_or_card',
            ),
        ]

    def __str__(self):
        return f'Shipment to {self.deliver_to} ({self.status})'


class ValidationReport(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        RESOLVED = 'resolved', 'Resolved'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.PROTECT,
        related_name='validation_reports',
    )
    code_entered = models.CharField(max_length=50)
    card = models.ForeignKey(
        Card,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='validation_reports',
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Report by {self.business} ({self.status})'


class Dispute(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        RESOLVED = 'resolved', 'Resolved'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    card = models.ForeignKey(
        Card,
        on_delete=models.PROTECT,
        related_name='disputes',
    )
    raised_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='disputes',
    )
    reason = models.TextField()
    resolution = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Dispute on {self.card} ({self.status})'