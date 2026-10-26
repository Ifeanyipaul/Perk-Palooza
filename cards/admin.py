from django.contrib import admin

from .models import (
    Card,
    CardBatch,
    CardDelivery,
    CardDesign,
    Dispute,
    PhysicalShipment,
    Redemption,
    ValidationReport,
)


@admin.register(CardDesign)
class CardDesignAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']


@admin.register(CardBatch)
class CardBatchAdmin(admin.ModelAdmin):
    list_display = ['giver', 'kind', 'card_type', 'quantity', 'value_per_card', 'created_at']
    list_filter = ['kind', 'card_type']
    search_fields = ['giver__email']


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ['serial_number', 'giver', 'card_type', 'face_value', 'status', 'business', 'category', 'expires_at']
    list_filter = ['status', 'card_type']
    search_fields = ['serial_number', 'giver__email', 'recipient_name']
    readonly_fields = ['code', 'serial_number', 'created_at']


@admin.register(Redemption)
class RedemptionAdmin(admin.ModelAdmin):
    list_display = ['card', 'business', 'redeemed_by', 'amount_spent', 'business_charge', 'business_net_amount', 'redeemed_at']
    search_fields = ['card__serial_number', 'business__name']


@admin.register(CardDelivery)
class CardDeliveryAdmin(admin.ModelAdmin):
    list_display = ['card', 'channel', 'destination', 'status', 'sent_at']
    list_filter = ['channel', 'status']


@admin.register(PhysicalShipment)
class PhysicalShipmentAdmin(admin.ModelAdmin):
    list_display = ['deliver_to', 'batch', 'card', 'status', 'tracking_number', 'shipped_at']
    list_filter = ['deliver_to', 'status']


@admin.register(ValidationReport)
class ValidationReportAdmin(admin.ModelAdmin):
    list_display = ['business', 'code_entered', 'status', 'created_at']
    list_filter = ['status']


@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['card', 'raised_by', 'status', 'created_at']
    list_filter = ['status']