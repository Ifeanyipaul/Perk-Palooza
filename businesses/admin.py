from django.contrib import admin

from .models import (
    Business,
    BusinessHours,
    BusinessOffering,
    BusinessRepresentative,
    Category,
    FloatEntry,
    TopUpRequest,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


class BusinessHoursInline(admin.TabularInline):
    model = BusinessHours
    extra = 0


class BusinessOfferingInline(admin.TabularInline):
    model = BusinessOffering
    extra = 0


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'city', 'state', 'status', 'float_balance']
    list_filter = ['status', 'category', 'state']
    search_fields = ['name', 'registration_number', 'description', 'city']
    readonly_fields = ['redemption_password_hash', 'created_at', 'updated_at']
    inlines = [BusinessHoursInline, BusinessOfferingInline]


@admin.register(BusinessRepresentative)
class BusinessRepresentativeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'business', 'role', 'username', 'is_active']
    list_filter = ['role', 'is_active']
    search_fields = ['full_name', 'phone', 'username']
    readonly_fields = ['username', 'created_at']


@admin.register(FloatEntry)
class FloatEntryAdmin(admin.ModelAdmin):
    list_display = ['business', 'entry_type', 'amount', 'balance_after', 'created_at']
    list_filter = ['entry_type']
    search_fields = ['business__name']

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TopUpRequest)
class TopUpRequestAdmin(admin.ModelAdmin):
    list_display = ['business', 'status', 'created_at', 'resolved_at']
    list_filter = ['status']