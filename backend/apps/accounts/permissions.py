from rest_framework import permissions
from .models import CustomUser


class IsAdminRole(permissions.BasePermission):
    """
    Custom permission to only allow users with the ADMIN role
    (or is_staff / is_superuser) to access the endpoint.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.role == CustomUser.Role.ADMIN
                or request.user.is_staff
                or request.user.is_superuser
            )
        )
