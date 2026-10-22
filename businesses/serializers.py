
from rest_framework import serializers
from .models import Business, BusinessCategory


class BusinessCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = BusinessCategory

        fields = [
            "id",
            "name",
            "slug",
            "description",
            "is_active",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "slug",
            "created_at",
            "updated_at",
        ]


class BusinessSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(
        source="owner.username",
        read_only=True
    )

    category_name = serializers.CharField(
        source="category.name",
        read_only=True
    )

    class Meta:
        model = Business

        fields = [
            "id",
            "owner",
            "owner_username",
            "name",
            "slug",
            "category",
            "category_name",
            "email",
            "phone",
            "address",
            "description",
            "status",
            "is_verified",
            "is_approved",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "owner",
            "owner_username",
            "slug",
            "category_name",
            "status",
            "is_verified",
            "is_approved",
            "created_at",
            "updated_at",
        ]

    def validate_category(self, value):

        if not value.is_active:
            raise serializers.ValidationError(
                "This business category is currently inactive."
            )

        return value
