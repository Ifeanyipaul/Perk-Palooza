from rest_framework import serializers
from .models import Wallet, WalletTransaction
from decimal import Decimal


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = [
            'id',
            'available_balance',
            'committed_balance',
            'total_funded',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class WalletTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = [
            'id',
            'transaction_type',
            'amount',
            'status',
            'reference',
            'description',
            'created_at',
        ]
        read_only_fields = fields
        
        

class WalletFundingSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal("0.01")
    )