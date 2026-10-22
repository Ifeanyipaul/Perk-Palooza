from django.shortcuts import render
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from .models import Wallet, WalletTransaction
from .serializers import (
    WalletSerializer,
    WalletTransactionSerializer
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from .serializers import WalletFundingSerializer
from .services import create_pending_funding

class WalletDetailView(generics.RetrieveAPIView):
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Wallet.objects.filter(
            user=self.request.user,
            user__role='GIVER'
        )


class WalletTransactionListView(generics.ListAPIView):
    serializer_class = WalletTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WalletTransaction.objects.filter(
            wallet__user=self.request.user,
            wallet__user__role='GIVER'
        ).order_by('-created_at')
        
        
class WalletFundingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "GIVER":
            return Response(
                {"detail": "Only givers can fund wallets."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = WalletFundingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            funding = create_pending_funding(
                request.user,
                serializer.validated_data["amount"]
            )
        except ValidationError as error:
            return Response(
                {"detail": error.messages},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                "message": "Funding transaction created successfully.",
                "transaction": {
                    "reference": funding.reference,
                    "amount": str(funding.amount),
                    "status": funding.status,
                    "transaction_type": funding.transaction_type,
                }
            },
            status=status.HTTP_201_CREATED
        )