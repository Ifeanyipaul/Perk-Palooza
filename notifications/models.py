import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class DeviceToken(models.Model):
    class Platform(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'
        WEB = 'web', 'Web'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, choices=Platform.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.user} ({self.platform})'


class Notification(models.Model):
    class Channel(models.TextChoices):
        PUSH = 'push', 'Push'
        WHATSAPP = 'whatsapp', 'WhatsApp'
        SMS = 'sms', 'SMS'
        EMAIL = 'email', 'Email'

    class Event(models.TextChoices):
        CARD_REDEEMED = 'card_redeemed', 'Card redeemed (to giver)'
        REDEMPTION_AT_BUSINESS = 'redemption_at_business', 'Card used at business'
        CARD_SCANNED = 'card_scanned', 'Card scanned (to representative)'
        DEPOSIT = 'deposit', 'Business deposit'
        LOW_FLOAT = 'low_float', 'Low float warning'
        CARD_EXPIRED = 'card_expired', 'Card expired'
        CASHBACK_EARNED = 'cashback_earned', 'Cashback earned'
        WITHDRAWAL_UPDATE = 'withdrawal_update', 'Withdrawal update'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='notifications',
    )
    representative = models.ForeignKey(
        'businesses.BusinessRepresentative',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='notifications',
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    event = models.CharField(max_length=30, choices=Event.choices)
    destination = models.CharField(
        max_length=200, blank=True,
        help_text='Phone number or email used. Empty for push',
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    card = models.ForeignKey(
        'cards.Card',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='notifications',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    failure_reason = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(Q(user__isnull=False) & Q(representative__isnull=True))
                | (Q(user__isnull=True) & Q(representative__isnull=False)),
                name='notification_has_one_recipient',
            ),
        ]

    def __str__(self):
        return f'{self.event} by {self.channel} ({self.status})'