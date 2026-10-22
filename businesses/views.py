
from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from accounts.models import User
from .models import Business, BusinessCategory
from .serializers import (
    BusinessSerializer,
    BusinessCategorySerializer,
)
from .permissions import IsPlatformAdmin
from rest_framework.permissions import IsAuthenticated


class BusinessCategoryListView(generics.ListAPIView):
    """
    Returns all active business categories.
    """

    queryset = BusinessCategory.objects.filter(is_active=True)
    serializer_class = BusinessCategorySerializer
    permission_classes = [permissions.AllowAny]


class BusinessListCreateView(generics.ListCreateAPIView):
    """
    Lists approved businesses and handles business creation.
    """

    serializer_class = BusinessSerializer

    def get_queryset(self):
        return Business.objects.filter(
            status=Business.Status.ACTIVE,
            is_approved=True,
            is_verified=True,
        )

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsPlatformAdmin()]

        return [permissions.AllowAny()]


class BusinessDetailView(generics.RetrieveAPIView):
    """
    Retrieves details of an approved business.
    """

    serializer_class = BusinessSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        return Business.objects.filter(
            status=Business.Status.ACTIVE,
            is_approved=True,
            is_verified=True,
        )


class BusinessApprovalView(APIView):
    """
    Allows administrators to approve or suspend businesses.
    """

    permission_classes = [IsPlatformAdmin]

    def patch(self, request, pk):

        try:
            business = Business.objects.get(pk=pk)

        except Business.DoesNotExist:
            return Response(
                {"error": "Business not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        action = request.data.get("action")

        if action == "approve":
            business.is_approved = True
            business.is_verified = True
            business.status = Business.Status.ACTIVE

        elif action == "suspend":
            business.status = Business.Status.SUSPENDED

        elif action == "deactivate":
            business.status = Business.Status.INACTIVE

        else:
            return Response(
                {"error": "Invalid action."},
                status=status.HTTP_400_BAD_REQUEST
            )

        business.save()

        return Response(
            {
                "message": f"Business {action} successful.",
                "business": BusinessSerializer(business).data,
            },
            status=status.HTTP_200_OK
        )


class BusinessOwnerAssignmentView(APIView):
    """
    Allows platform administrators to assign
    a BUSINESS user to a business profile.
    """
    permission_classes = [IsPlatformAdmin]

    def patch(self, request, pk):
        business = get_object_or_404(Business, pk=pk)

        owner_id = request.data.get("owner_id")

        if not owner_id:
            return Response(
                {"error": "owner_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            owner = User.objects.get(
                pk=owner_id,
                role=User.Role.BUSINESS,
                is_active=True
            )
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {
                    "error": (
                        "Invalid owner. Select an active user "
                        "with the BUSINESS role."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        business.owner = owner
        business.save(update_fields=["owner", "updated_at"])

        return Response(
            {
                "message": "Business owner assigned successfully.",
                "business": BusinessSerializer(business).data,
            },
            status=status.HTTP_200_OK
        )


class BusinessOwnerAssignmentView(APIView):
    """
    Allows platform administrators to assign
    a BUSINESS user to a business profile.
    """

    permission_classes = [IsPlatformAdmin]

    def patch(self, request, pk):

        business = get_object_or_404(Business, pk=pk)

        owner_id = request.data.get("owner_id")

        if not owner_id:
            return Response(
                {"error": "owner_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            owner = User.objects.get(
                pk=owner_id,
                role=User.Role.BUSINESS,
                is_active=True
            )

        except User.DoesNotExist:
            return Response(
                {
                    "error": (
                        "Invalid owner. Select an active "
                        "user with the BUSINESS role."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        business.owner = owner
        business.save(update_fields=["owner", "updated_at"])

        return Response(
            {
                "message": "Business owner assigned successfully.",
                "business": BusinessSerializer(business).data,
            },
            status=status.HTTP_200_OK
        )


class MyBusinessesView(APIView):
    """
    Allows a BUSINESS user to view only
    businesses assigned to their account.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != User.Role.BUSINESS:
            return Response(
                {"error": "Only business accounts can access this endpoint."},
                status=status.HTTP_403_FORBIDDEN
            )

        businesses = Business.objects.filter(
            owner=request.user
        ).order_by("-created_at")

        serializer = BusinessSerializer(businesses, many=True)

        return Response(
            {
                "count": businesses.count(),
                "businesses": serializer.data
            },
            status=status.HTTP_200_OK
        )