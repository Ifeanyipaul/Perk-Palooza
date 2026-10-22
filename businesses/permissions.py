from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    """
    Allows access only to authenticated platform administrators.
    """

    message = "Only platform administrators can perform this action."

    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == "ADMIN"
        )


class IsBusinessOwner(BasePermission):
    """
    Allows access only to the owner of a business.
    """

    message = "You do not have permission to access this business."

    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated
            and request.user.role == "BUSINESS"
            and obj.owner_id == request.user.id
        )