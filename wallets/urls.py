from django.urls import path
from .views import (
    WalletDetailView,
    WalletTransactionListView,
    WalletFundingView,
)

urlpatterns = [
    path('', WalletDetailView.as_view(), name='wallet-detail'),
    path(
        'transactions/',
        WalletTransactionListView.as_view(),
        name='wallet-transactions'
    ),
    path(
        'fund/',
        WalletFundingView.as_view(),
        name='wallet-fund'
    ),
]