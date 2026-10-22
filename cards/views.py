from rest_framework import generics

from .models import GiftCard
from .serializers import GiftCardSerializer
from .permissions import IsGiver


class GiftCardListCreateView(generics.ListCreateAPIView):
    """
    Allows authenticated givers to create gift cards
    and view only their own gift cards.
    """

    serializer_class = GiftCardSerializer
    permission_classes = [IsGiver]

    def get_queryset(self):
        return GiftCard.objects.filter(
            giver=self.request.user
        ).order_by("-created_at")


class GiftCardDetailView(generics.RetrieveAPIView):
    """
    Allows a giver to view only their own gift card.
    """

    serializer_class = GiftCardSerializer
    permission_classes = [IsGiver]

    def get_queryset(self):
        return GiftCard.objects.filter(
            giver=self.request.user
        )