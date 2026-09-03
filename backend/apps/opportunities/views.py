import logging

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle

from .models import Opportunity
from .permissions import IsOwnerOrReadOnly, IsVerifiedUser
from .serializers import (
    OpportunityCreateUpdateSerializer,
    OpportunityDetailSerializer,
    OpportunityListSerializer,
)

logger = logging.getLogger(__name__)


class OpportunityPagination(PageNumberPagination):
    """
    Standard pagination for opportunities list (20 items per page by default).
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class OpportunityListCreateView(generics.ListCreateAPIView):
    """
    API endpoint to list opportunities (public) or create a new opportunity (verified users).
    """

    pagination_class = OpportunityPagination

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsVerifiedUser()]
        return [AllowAny()]

    def get_throttles(self):
        if self.request.method == "POST":
            self.throttle_scope = "opportunity_create"
            return [ScopedRateThrottle()]
        return []

    def get_serializer_class(self):
        if self.request.method == "POST":
            return OpportunityCreateUpdateSerializer
        return OpportunityListSerializer

    def get_queryset(self):
        """
        Filters opportunities by category, work_mode, city, and status.
        Defaults to status='open' unless 'status' query param is explicitly passed.
        """
        queryset = Opportunity.objects.select_related("poster").all()
        params = self.request.query_params

        # Filter by status (default to 'open' if not provided or not 'all')
        status_param = params.get("status", "open").strip().lower()
        if status_param != "all":
            queryset = queryset.filter(status=status_param)

        # Filter by category
        category = params.get("category")
        if category:
            queryset = queryset.filter(category__iexact=category.strip())

        # Filter by work_mode
        work_mode = params.get("work_mode")
        if work_mode:
            queryset = queryset.filter(work_mode__iexact=work_mode.strip())

        # Filter by city
        city = params.get("city")
        if city:
            queryset = queryset.filter(city__icontains=city.strip())

        return queryset

    def perform_create(self, serializer):
        """
        Automatically sets the poster to the current authenticated user.
        """
        serializer.save(poster=self.request.user)

    @extend_schema(
        summary="List opportunities",
        description="Public endpoint to list opportunities with query parameter filtering (category, work_mode, city, status). Defaults to open opportunities.",
        parameters=[
            OpenApiParameter("category", OpenApiTypes.STR, description="Filter by category (e.g. part_time, internship)"),
            OpenApiParameter("work_mode", OpenApiTypes.STR, description="Filter by work mode (remote, onsite, hybrid)"),
            OpenApiParameter("city", OpenApiTypes.STR, description="Filter by city name"),
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter by status (open, closed, draft, or 'all'. Defaults to 'open')"),
        ],
        responses={200: OpportunityListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create new opportunity",
        description="Allows an authenticated, verified user to create a new opportunity listing.",
        request=OpportunityCreateUpdateSerializer,
        responses={201: OpportunityDetailSerializer},
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class OpportunityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint to retrieve (public), update, or delete (owner/admin only) a specific opportunity.
    """

    queryset = Opportunity.objects.select_related("poster").all()
    permission_classes = [IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return OpportunityCreateUpdateSerializer
        return OpportunityDetailSerializer

    @extend_schema(
        summary="Retrieve opportunity details",
        description="Public endpoint to view full details of a specific opportunity.",
        responses={200: OpportunityDetailSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update opportunity",
        description="Full update of an opportunity (owner or admin only).",
        request=OpportunityCreateUpdateSerializer,
        responses={200: OpportunityDetailSerializer},
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(
        summary="Partial update opportunity",
        description="Partial update of an opportunity (owner or admin only).",
        request=OpportunityCreateUpdateSerializer,
        responses={200: OpportunityDetailSerializer},
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Delete opportunity",
        description="Deletes an opportunity (owner or admin only).",
        responses={204: None},
    )
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
