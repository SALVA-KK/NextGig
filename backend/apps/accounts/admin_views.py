from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.opportunities.views import OpportunityPagination

from .models import AdminActionLog, CustomUser, ProviderProfile
from .permissions import IsAdminRole
from .serializers import (
    AdminAuditLogSerializer,
    AdminPendingProviderSerializer,
    AdminUserListSerializer,
)


class AdminPendingProvidersListView(generics.ListAPIView):
    """
    API endpoint for admin to list pending provider profile verification requests.
    """

    permission_classes = [IsAdminRole]
    serializer_class = AdminPendingProviderSerializer
    pagination_class = OpportunityPagination

    def get_queryset(self):
        return ProviderProfile.objects.filter(is_verified=False).select_related("user").order_by("-created_at")


from apps.notifications.models import Notification
from apps.notifications.services import create_notification


class AdminVerifyProviderView(APIView):
    """
    API endpoint for admin to verify or un-verify a provider profile.
    Includes rate limiting, provider notifications, and audit logging.
    """

    permission_classes = [IsAdminRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admin_write"

    def patch(self, request, pk, *args, **kwargs):
        profile = get_object_or_404(ProviderProfile, pk=pk)
        new_is_verified = request.data.get("is_verified", True)
        old_is_verified = profile.is_verified

        if old_is_verified != new_is_verified:
            profile.is_verified = new_is_verified
            profile.save()

            # Keep user.is_verified in sync
            profile.user.is_verified = new_is_verified
            profile.user.save()

            # Send in-app notification on actual state change
            if new_is_verified:
                create_notification(
                    recipient=profile.user,
                    actor=request.user,
                    notification_type=Notification.NotificationType.PROVIDER_VERIFIED,
                    title="You're Verified!",
                    message="Congratulations - your organization has been verified by our team. Your Verified badge is now visible to students.",
                    event_key=f"provider_verified:{profile.id}",
                )
            else:
                create_notification(
                    recipient=profile.user,
                    actor=request.user,
                    notification_type=Notification.NotificationType.PROVIDER_UNVERIFIED,
                    title="Verification Status Updated",
                    message="Your organization's verification status has been updated by our team.",
                    event_key=f"provider_unverified:{profile.id}",
                )

            # Audit log
            action_type = (
                AdminActionLog.ActionType.PROVIDER_VERIFIED
                if new_is_verified
                else AdminActionLog.ActionType.PROVIDER_UNVERIFIED
            )
            AdminActionLog.objects.create(
                admin=request.user,
                action_type=action_type,
                target_description=f"Provider #{profile.id}: {profile.organization_name} ({profile.user.email})",
            )

        return Response(
            {
                "message": f"Provider profile {'verified' if new_is_verified else 'unverified'} successfully.",
                "id": profile.id,
                "is_verified": profile.is_verified,
            },
            status=status.HTTP_200_OK,
        )


class AdminUserListView(generics.ListAPIView):
    """
    API endpoint for admin to list all CustomUser accounts with filtering and search.
    """

    permission_classes = [IsAdminRole]
    serializer_class = AdminUserListSerializer
    pagination_class = OpportunityPagination

    def get_queryset(self):
        queryset = CustomUser.objects.all().order_by("-date_joined")
        role = self.request.query_params.get("role")
        search = self.request.query_params.get("search")

        if role:
            queryset = queryset.filter(role=role)
        if search:
            search_term = search.strip()
            queryset = queryset.filter(
                Q(email__icontains=search_term) | Q(full_name__icontains=search_term)
            )

        return queryset


class AdminToggleUserActiveView(APIView):
    """
    API endpoint for admin to activate or deactivate a user account.
    Prevents admins from deactivating their own account or other admin accounts (unless superuser).
    Includes rate limiting and audit logging.
    """

    permission_classes = [IsAdminRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admin_write"

    def patch(self, request, pk, *args, **kwargs):
        target_user = get_object_or_404(CustomUser, pk=pk)

        if target_user.id == request.user.id:
            return Response(
                {"detail": "You cannot deactivate your own admin account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target_user.role == CustomUser.Role.ADMIN and not request.user.is_superuser:
            return Response(
                {"detail": "Cannot deactivate another admin account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target_user.is_active = not target_user.is_active
        target_user.save()

        # Audit log
        action_type = (
            AdminActionLog.ActionType.USER_ACTIVATED
            if target_user.is_active
            else AdminActionLog.ActionType.USER_DEACTIVATED
        )
        AdminActionLog.objects.create(
            admin=request.user,
            action_type=action_type,
            target_description=f"User #{target_user.id}: {target_user.email} (Role: {target_user.role})",
        )

        return Response(
            {
                "message": f"User account {'activated' if target_user.is_active else 'deactivated'} successfully.",
                "id": target_user.id,
                "is_active": target_user.is_active,
            },
            status=status.HTTP_200_OK,
        )


class AdminAuditLogListView(generics.ListAPIView):
    """
    API endpoint for admin to retrieve paginated audit log of administrative actions.
    """

    permission_classes = [IsAdminRole]
    serializer_class = AdminAuditLogSerializer
    pagination_class = OpportunityPagination

    def get_queryset(self):
        return AdminActionLog.objects.select_related("admin").all().order_by("-timestamp")
