import secrets
import uuid

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

# All money fields are stored in kobo (1 naira = 100 kobo) as whole numbers.


def generate_rep_username(business_name):
    letters = ''.join(c for c in business_name.upper() if c.isalpha())[:3] or 'BIZ'
    digits = ''.join(secrets.choice('0123456789') for _ in range(4))
    tail = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ') for _ in range(2))
    return f'{letters}-{digits}-{tail}'


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
    description = models.TextField(
        help_text='What the business does, and the products, services or facilities it offers'
    )
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    notification_phone = models.CharField(
        max_length=20, blank=True,
        help_text='Receives business-level redemption alerts',
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    redemption_password_hash = models.CharField(max_length=128, blank=True)
    float_balance = models.BigIntegerField(default=0, help_text='Amount in kobo')
    low_float_threshold = models.BigIntegerField(default=0, help_text='Amount in kobo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'businesses'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['state', 'city']),
        ]

    def __str__(self):
        return self.name

    def set_redemption_password(self, raw_password):
        self.redemption_password_hash = make_password(raw_password)

    def check_redemption_password(self, raw_password):
        return check_password(raw_password, self.redemption_password_hash)

    @property
    def is_float_low(self):
        return self.float_balance <= self.low_float_threshold


class BusinessHours(models.Model):
    class Day(models.IntegerChoices):
        MONDAY = 0, 'Monday'
        TUESDAY = 1, 'Tuesday'
        WEDNESDAY = 2, 'Wednesday'
        THURSDAY = 3, 'Thursday'
        FRIDAY = 4, 'Friday'
        SATURDAY = 5, 'Saturday'
        SUNDAY = 6, 'Sunday'

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='hours',
    )
    day_of_week = models.IntegerField(choices=Day.choices)
    opens_at = models.TimeField(null=True, blank=True)
    closes_at = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'business hours'
        ordering = ['business', 'day_of_week']
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'day_of_week'],
                name='one_hours_row_per_day',
            ),
            models.CheckConstraint(
                condition=Q(is_closed=True)
                | (Q(opens_at__isnull=False) & Q(closes_at__isnull=False)),
                name='open_days_have_times',
            ),
        ]

    def __str__(self):
        if self.is_closed:
            return f'{self.business} {self.get_day_of_week_display()}: closed'
        return f'{self.business} {self.get_day_of_week_display()}: {self.opens_at} to {self.closes_at}'


class BusinessOffering(models.Model):
    class Kind(models.TextChoices):
        PRODUCT = 'product', 'Product'
        SERVICE = 'service', 'Service'
        FACILITY = 'facility', 'Facility'

    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='offerings',
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ['business', 'kind', 'name']
        indexes = [models.Index(fields=['name'])]
        constraints = [
            models.UniqueConstraint(
                fields=['business', 'kind', 'name'],
                name='no_duplicate_offering',
            ),
        ]

    def __str__(self):
        return f'{self.business}: {self.name}'


class BusinessRepresentative(models.Model):
    class Role(models.TextChoices):
        REDEMPTION = 'redemption', 'Card scanning and redemption'
        DEPOSIT_NOTIFICATIONS = 'deposit_notifications', 'Deposit notifications'
        OWNER = 'owner', 'Business owner / primary contact'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name='representatives',
    )
    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=30, choices=Role.choices)
    username = models.CharField(
        max_length=30, unique=True, null=True, blank=True, editable=False,
        help_text='System-generated for redemption representatives. Never editable.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['business', 'full_name']

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()}, {self.business})'

    def save(self, *args, **kwargs):
        if self.role == self.Role.REDEMPTION and not self.username:
            self.username = generate_rep_username(self.business.name)
        super().save(*args, **kwargs)


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
    amount = models.BigIntegerField(help_text='Amount in kobo. Plus for money in, minus for money out')
    balance_after = models.BigIntegerField(help_text='Amount in kobo')
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