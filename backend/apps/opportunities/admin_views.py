from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.accounts.models import AdminActionLog
from apps.accounts.permissions import IsAdminRole
from apps.opportunities.models import Opportunity
from apps.opportunities.serializers import OpportunityListSerializer
from apps.opportunities.views import OpportunityPagination


class AdminOpportunityListView(generics.ListAPIView):
    """
    API endpoint for admin to list all opportunities across all statuses (open, closed, draft)
    with optional status and title search filters.
    """

    permission_classes = [IsAdminRole]
    serializer_class = OpportunityListSerializer
    pagination_class = OpportunityPagination

    def get_queryset(self):
        queryset = Opportunity.objects.all().select_related("poster").order_by("-created_at")
        status_param = self.request.query_params.get("status")
        search = self.request.query_params.get("search")

        if status_param and status_param != "all":
            queryset = queryset.filter(status=status_param)
        if search:
            queryset = queryset.filter(title__icontains=search.strip())

        return queryset


class AdminForceCloseOpportunityView(APIView):
    """
    API endpoint for admin to force close any opportunity listing.
    Includes rate limiting and audit logging.
    """

    permission_classes = [IsAdminRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admin_write"

    def patch(self, request, pk, *args, **kwargs):
        opportunity = get_object_or_404(Opportunity, pk=pk)
        opportunity.status = "closed"
        opportunity.save()

        # Audit log
        AdminActionLog.objects.create(
            admin=request.user,
            action_type=AdminActionLog.ActionType.OPPORTUNITY_FORCE_CLOSED,
            target_description=f"Opportunity #{opportunity.id}: {opportunity.title}",
        )

        return Response(
            {
                "message": "Opportunity force-closed by admin.",
                "id": opportunity.id,
                "status": opportunity.status,
            },
            status=status.HTTP_200_OK,
        )


class AdminDeleteOpportunityView(APIView):
    """
    API endpoint for admin to moderation-delete any opportunity listing.
    Includes rate limiting and audit logging.
    """

    permission_classes = [IsAdminRole]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admin_write"

    def delete(self, request, pk, *args, **kwargs):
        opportunity = get_object_or_404(Opportunity, pk=pk)
        target_desc = f"Opportunity #{opportunity.id}: {opportunity.title}"

        # Delete record
        opportunity.delete()

        # Audit log
        AdminActionLog.objects.create(
            admin=request.user,
            action_type=AdminActionLog.ActionType.OPPORTUNITY_DELETED,
            target_description=target_desc,
        )

        return Response(
            {"message": "Opportunity deleted by admin."},
            status=status.HTTP_200_OK,
        )
