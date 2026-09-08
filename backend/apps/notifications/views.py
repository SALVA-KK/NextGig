from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.opportunities.views import OpportunityPagination
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListAPIView(generics.ListAPIView):
    """
    API endpoint to list notifications for the authenticated user.
    Strictly isolated to recipient=request.user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = OpportunityPagination

    def get_queryset(self):
        queryset = Notification.objects.filter(
            recipient=self.request.user
        ).select_related("actor", "opportunity", "application")

        is_read_param = self.request.query_params.get("is_read")
        if is_read_param is not None:
            is_read_bool = is_read_param.strip().lower() == "true"
            queryset = queryset.filter(is_read=is_read_bool)

        return queryset

    @extend_schema(
        summary="List user notifications",
        description="Returns a paginated list of notifications for the authenticated user.",
        parameters=[
            OpenApiParameter("is_read", OpenApiTypes.BOOL, description="Filter by read status (true or false)"),
        ],
        responses={200: NotificationSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UnreadNotificationCountView(APIView):
    """
    API endpoint returning the unread notification count for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get unread notification count",
        description="Returns the total count of unread notifications for the authenticated user.",
        responses={200: inline_serializer(name="UnreadCountResponse", fields={"count": serializers.IntegerField()})},
    )
    def get(self, request, *args, **kwargs):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()
        return Response({"count": count}, status=status.HTTP_200_OK)


class MarkNotificationReadView(APIView):
    """
    API endpoint to mark a single notification belonging to the authenticated user as read.
    Idempotent: preserves original read_at if already read.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark notification as read",
        description="Marks a single notification belonging to the authenticated user as read.",
        responses={200: NotificationSerializer},
    )
    def patch(self, request, pk, *args, **kwargs):
        notification = generics.get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user,
        )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at"])

        serializer = NotificationSerializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarkAllNotificationsReadView(APIView):
    """
    API endpoint to bulk mark all unread notifications for the authenticated user as read.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Mark all notifications as read",
        description="Bulk updates all unread notifications for the authenticated user to read.",
        responses={200: inline_serializer(name="MarkAllReadResponse", fields={"message": serializers.CharField()})},
    )
    def post(self, request, *args, **kwargs):
        now = timezone.now()
        Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=now)
        return Response(
            {"message": "All notifications marked as read."},
            status=status.HTTP_200_OK,
        )


class NotificationDeleteView(APIView):
    """
    API endpoint to delete/dismiss a single notification belonging to the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete notification",
        description="Deletes a notification belonging to the authenticated user.",
        responses={200: inline_serializer(name="DeleteNotificationResponse", fields={"message": serializers.CharField()})},
    )
    def delete(self, request, pk, *args, **kwargs):
        notification = generics.get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user,
        )
        notification.delete()
        return Response(
            {"message": "Notification deleted successfully."},
            status=status.HTTP_200_OK,
        )
