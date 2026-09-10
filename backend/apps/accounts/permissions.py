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


IsAdminUser = IsAdminRole


class IsStudentRole(permissions.BasePermission):
    """
    Custom permission to only allow users with the STUDENT role to access student-specific endpoints.
    Denies providers, admins, and unauthenticated users.
    """

    message = "Only student accounts can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == CustomUser.Role.STUDENT
        )

