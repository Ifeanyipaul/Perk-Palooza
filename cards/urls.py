from django.urls import path

from .views import (
    GiftCardListCreateView,
    GiftCardDetailView,
)

urlpatterns = [
    path(
        "",
        GiftCardListCreateView.as_view(),
        name="giftcard-list-create",
    ),

    path(
        "<int:pk>/",
        GiftCardDetailView.as_view(),
        name="giftcard-detail",
    ),
]