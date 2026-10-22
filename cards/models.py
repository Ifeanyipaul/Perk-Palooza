import secrets
from django.db.models import Q
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

from businesses.models import Business, BusinessCategory


class GiftCard(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending Payment"
        ACTIVE = "ACTIVE", "Active"
        REDEEMED = "REDEEMED", "Redeemed"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    giver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="gift_cards_created",
    )

    recipient_name = models.CharField(max_length=150)

    recipient_email = models.EmailField()

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    business = models.ForeignKey(
        Business,
        on_delete=models.PROTECT,
        related_name="gift_cards",
        null=True,
        blank=True,
    )

    category = models.ForeignKey(
        BusinessCategory,
        on_delete=models.PROTECT,
        related_name="gift_cards",
        null=True,
        blank=True,
    )

    card_code = models.CharField(
        max_length=64,
        unique=True,
        editable=False,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    expires_at = models.DateTimeField()

    is_redeemed = models.BooleanField(default=False)

    redeemed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.card_code:
            self.card_code = secrets.token_urlsafe(32)

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if bool(self.business) == bool(self.category):
            raise ValidationError(
                "A gift card must be restricted to either "
                "one business or one category, not both."
            )

        if self.amount is not None and self.amount <= 0:
            raise ValidationError(
                "Gift card amount must be greater than zero."
            )

    def __str__(self):
        return f"Gift Card - {self.recipient_name} - {self.amount}"



    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="giftcard_amount_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(business__isnull=False, category__isnull=True)
                    | Q(business__isnull=True, category__isnull=False)
                ),
                name="giftcard_exactly_one_restriction",
            ),
        ]