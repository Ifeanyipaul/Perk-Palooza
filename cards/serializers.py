from django.utils import timezone
from rest_framework import serializers

from businesses.models import Business, BusinessCategory
from .models import GiftCard


class GiftCardSerializer(serializers.ModelSerializer):

    giver = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    card_code = serializers.CharField(read_only=True)

    status = serializers.CharField(read_only=True)

    is_redeemed = serializers.BooleanField(read_only=True)

    redeemed_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = GiftCard

        fields = [
            "id",
            "giver",
            "recipient_name",
            "recipient_email",
            "amount",
            "business",
            "category",
            "card_code",
            "status",
            "expires_at",
            "is_redeemed",
            "redeemed_at",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "giver",
            "card_code",
            "status",
            "is_redeemed",
            "redeemed_at",
            "created_at",
            "updated_at",
        ]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Gift card amount must be greater than zero."
            )

        return value

    def validate_business(self, value):
        if value is not None:
            if (
                value.status != Business.Status.ACTIVE
                or not value.is_approved
                or not value.is_verified
            ):
                raise serializers.ValidationError(
                    "You can only select an approved, active and verified business."
                )

        return value

    def validate_category(self, value):
        if value is not None and not value.is_active:
            raise serializers.ValidationError(
                "You can only select an active business category."
            )

        return value

    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                "Expiry date must be in the future."
            )

        return value

    def validate(self, attrs):
        business = attrs.get(
            "business",
            getattr(self.instance, "business", None)
        )

        category = attrs.get(
            "category",
            getattr(self.instance, "category", None)
        )

        if bool(business) == bool(category):
            raise serializers.ValidationError(
                "A gift card must be restricted to either "
                "one business or one category, not both."
            )

        return attrs

    def create(self, validated_data):
        validated_data["giver"] = self.context["request"].user

        return super().create(validated_data)