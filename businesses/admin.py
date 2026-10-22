
from django.contrib import admin
from .models import Business, BusinessCategory


@admin.register(BusinessCategory)
class BusinessCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "status",
        "is_verified",
        "is_approved",
        "created_at",
    )

    search_fields = ("name", "email", "phone")
    list_filter = ("status", "is_verified", "is_approved", "category")
