import logging

from django.db import IntegrityError
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import Application, Opportunity, SavedOpportunity
from .permissions import IsApplicantOrPoster, IsOwnerOrReadOnly, IsVerifiedUser
from .serializers import (
    ApplicantListSerializer,
    ApplicationCreateSerializer,
    ApplicationSerializer,
    ApplicationStatusUpdateSerializer,
    OpportunityCreateUpdateSerializer,
    OpportunityDetailSerializer,
    OpportunityListSerializer,
    SavedOpportunitySerializer,
)
from .tasks import notify_applicant_of_status_change, notify_poster_of_new_application

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


class OpportunitySaveView(APIView):
    """
    API endpoint to save (POST) or unsave (DELETE) an opportunity for the authenticated user.
    Saving requires an authenticated + verified user account.
    Unsaving requires an authenticated user account.
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), IsVerifiedUser()]
        return [IsAuthenticated()]

    @extend_schema(
        summary="Save / Bookmark opportunity",
        description="Saves/bookmarks an opportunity for the authenticated user (idempotent).",
        responses={201: inline_serializer(name="OpportunitySaveSuccess", fields={"message": serializers.CharField()}), 200: inline_serializer(name="OpportunityAlreadySaved", fields={"message": serializers.CharField()})},
    )
    def post(self, request, pk, *args, **kwargs):
        opportunity = generics.get_object_or_404(Opportunity, pk=pk)
        saved_opp, created = SavedOpportunity.objects.get_or_create(
            user=request.user,
            opportunity=opportunity,
        )
        if created:
            return Response(
                {"message": "Opportunity saved successfully."},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": "Opportunity is already saved."},
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        summary="Unsave / Remove bookmark from opportunity",
        description="Removes an opportunity from the authenticated user's saved list.",
        responses={200: inline_serializer(name="OpportunityUnsaveSuccess", fields={"message": serializers.CharField()}), 404: inline_serializer(name="OpportunityNotSavedError", fields={"detail": serializers.CharField()})},
    )
    def delete(self, request, pk, *args, **kwargs):
        saved_opp = SavedOpportunity.objects.filter(
            user=request.user,
            opportunity_id=pk,
        ).first()
        if not saved_opp:
            return Response(
                {"detail": "Saved opportunity not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        saved_opp.delete()
        return Response(
            {"message": "Opportunity unsaved successfully."},
            status=status.HTTP_200_OK,
        )


class SavedOpportunityListView(generics.ListAPIView):
    """
    API endpoint to list all saved opportunities bookmarked by the authenticated user.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = SavedOpportunitySerializer
    pagination_class = OpportunityPagination

    def get_queryset(self):
        return SavedOpportunity.objects.filter(
            user=self.request.user
        ).select_related("opportunity", "opportunity__poster")

    @extend_schema(
        summary="List user's saved opportunities",
        description="Returns a paginated list of opportunities bookmarked by the authenticated user.",
        responses={200: SavedOpportunitySerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ApplicationCreateView(APIView):
    """
    API endpoint for students to apply to an open opportunity.
    Gated by IsAuthenticated + IsVerifiedUser + Student role check.
    Throttled at 20 requests/hour.
    """

    permission_classes = [IsAuthenticated, IsVerifiedUser]
    throttle_scope = "application_create"

    def get_throttles(self):
        return [ScopedRateThrottle()]

    @extend_schema(
        summary="Apply for an opportunity",
        description="Submits an application for an open opportunity. Accessible only to verified student accounts.",
        request=ApplicationCreateSerializer,
        responses={201: ApplicationSerializer, 400: inline_serializer(name="ApplicationError", fields={"detail": serializers.CharField()})},
    )
    def post(self, request, pk, *args, **kwargs):
        if getattr(request.user, "role", None) != "student":
            return Response(
                {"detail": "Only students can apply to opportunities."},
                status=status.HTTP_403_FORBIDDEN,
            )

        opportunity = generics.get_object_or_404(Opportunity, pk=pk)

        if opportunity.status != Opportunity.Status.OPEN:
            return Response(
                {"detail": "Cannot apply to closed or draft opportunities."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if opportunity.poster == request.user:
            return Response(
                {"detail": "You cannot apply to your own posted opportunity."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Application.objects.filter(applicant=request.user, opportunity=opportunity).exists():
            return Response(
                {"detail": "You have already applied to this opportunity."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ApplicationCreateSerializer(
            data=request.data,
            context={"request": request, "opportunity": opportunity},
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            application = serializer.save(
                applicant=request.user,
                opportunity=opportunity,
            )
        except IntegrityError:
            return Response(
                {"detail": "You have already applied to this opportunity."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Trigger async email notification with graceful fallback if Redis is offline
        try:
            notify_poster_of_new_application.delay(application.id)
        except Exception as e:
            logger.warning(f"Failed to enqueue poster notification task: {e}")

        output_serializer = ApplicationSerializer(application)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class MyApplicationsListView(generics.ListAPIView):
    """
    API endpoint for authenticated applicants to list their own submitted applications.
    Supports optional status query parameter filtering.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ApplicationSerializer
    pagination_class = OpportunityPagination

    def get_queryset(self):
        queryset = Application.objects.filter(applicant=self.request.user).select_related(
            "opportunity", "opportunity__poster", "applicant"
        )
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status__iexact=status_param.strip())
        return queryset

    @extend_schema(
        summary="List my applications",
        description="Returns a paginated list of applications submitted by the authenticated user.",
        parameters=[
            OpenApiParameter("status", OpenApiTypes.STR, description="Filter applications by status (applied, under_review, accepted, rejected, withdrawn)"),
        ],
        responses={200: ApplicationSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class OpportunityApplicantsListView(generics.ListAPIView):
    """
    API endpoint for opportunity posters (or admins) to view all applicants for their opportunity.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ApplicantListSerializer
    pagination_class = OpportunityPagination

    def get_queryset(self):
        pk = self.kwargs.get("pk")
        opportunity = generics.get_object_or_404(Opportunity, pk=pk)

        user = self.request.user
        is_poster = opportunity.poster == user or getattr(user, "role", None) == "admin" or getattr(user, "is_staff", False)
        if not is_poster:
            return Application.objects.none()

        return Application.objects.filter(opportunity=opportunity).select_related("applicant")

    @extend_schema(
        summary="List applicants for an opportunity",
        description="Returns a paginated list of applicants for a specific opportunity. Accessible only to the opportunity poster or admin.",
        responses={200: ApplicantListSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        opportunity = generics.get_object_or_404(Opportunity, pk=pk)

        user = request.user
        is_poster = opportunity.poster == user or getattr(user, "role", None) == "admin" or getattr(user, "is_staff", False)
        if not is_poster:
            return Response(
                {"detail": "You do not have permission to view applicants for this opportunity."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().get(request, *args, **kwargs)


class ApplicationStatusUpdateView(APIView):
    """
    API endpoint for updating an application status.
    - Poster can set under_review, accepted, rejected.
    - Applicant can withdraw pending applications.
    """

    permission_classes = [IsAuthenticated, IsApplicantOrPoster]

    @extend_schema(
        summary="Update application status",
        description="Updates an application status. Posters can update to under_review, accepted, or rejected. Applicants can withdraw pending applications.",
        request=ApplicationStatusUpdateSerializer,
        responses={200: ApplicationSerializer},
    )
    def patch(self, request, pk, *args, **kwargs):
        application = generics.get_object_or_404(
            Application.objects.select_related("opportunity", "opportunity__poster", "applicant"),
            pk=pk,
        )

        self.check_object_permissions(request, application)

        user = request.user
        is_poster = application.opportunity.poster == user or getattr(user, "role", None) == "admin" or getattr(user, "is_staff", False)
        is_applicant = application.applicant == user

        new_status = request.data.get("status")

        if is_applicant and not is_poster:
            # Applicant withdrawal flow
            if new_status != Application.Status.WITHDRAWN:
                return Response(
                    {"detail": "Applicants can only withdraw their application."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if application.status not in [Application.Status.APPLIED, Application.Status.UNDER_REVIEW]:
                return Response(
                    {"detail": "Cannot withdraw an application that has already been accepted, rejected, or withdrawn."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            application.status = Application.Status.WITHDRAWN
            application.save()
            output_serializer = ApplicationSerializer(application)
            return Response(output_serializer.data, status=status.HTTP_200_OK)

        # Poster status update flow
        serializer = ApplicationStatusUpdateSerializer(
            instance=application,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        application = serializer.save()

        # Notify applicant of poster-initiated status change
        try:
            notify_applicant_of_status_change.delay(application.id)
        except Exception as e:
            logger.warning(f"Failed to enqueue applicant notification task: {e}")

        output_serializer = ApplicationSerializer(application)
        return Response(output_serializer.data, status=status.HTTP_200_OK)

