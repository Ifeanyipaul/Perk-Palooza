from rest_framework.permissions import BasePermission


class IsGiver(BasePermission):
    """
    Only authenticated GIVER accounts can access
    gift card creation and management endpoints.
    """

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "GIVER"
        )