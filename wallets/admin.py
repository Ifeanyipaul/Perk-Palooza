from django.contrib import admin

from .models import (
    CashbackEntry,
    DiscountTier,
    Payment,
    PricingSetting,
    Wallet,
    WalletEntry,
    WithdrawalRequest,
)


class ReadOnlyLedgerAdmin(admin.ModelAdmin):
    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PricingSetting)
class PricingSettingAdmin(admin.ModelAdmin):
    list_display = ['digital_card_fee', 'physical_card_fee', 'cashback_rate_bp', 'business_charge_bp', 'updated_at']

    def has_add_permission(self, request):
        return not PricingSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(DiscountTier)
class DiscountTierAdmin(admin.ModelAdmin):
    list_display = ['min_quantity', 'max_quantity', 'discount_bp']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'available', 'committed', 'locked', 'cashback_balance']
    search_fields = ['user__email']


@admin.register(WalletEntry)
class WalletEntryAdmin(ReadOnlyLedgerAdmin):
    list_display = ['wallet', 'entry_type', 'amount', 'available_change', 'committed_change', 'locked_change', 'created_at']
    list_filter = ['entry_type']


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['paystack_reference', 'giver', 'card_quantity', 'total_charged', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['paystack_reference', 'giver__email']


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'bank_name', 'account_number', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['user__email', 'account_number']


@admin.register(CashbackEntry)
class CashbackEntryAdmin(ReadOnlyLedgerAdmin):
    list_display = ['wallet', 'entry_type', 'amount', 'created_at']
    list_filter = ['entry_type']