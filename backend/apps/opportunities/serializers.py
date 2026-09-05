from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .models import Application, Opportunity, SavedOpportunity

User = get_user_model()


class PosterPublicSerializer(serializers.ModelSerializer):
    """
    Public nested representation of the user who posted the opportunity.
    """

    class Meta:
        model = User
        fields = ("id", "full_name", "email")
        read_only_fields = fields


class OpportunityListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing opportunities (omits long description text).
    """

    poster = PosterPublicSerializer(read_only=True)

    class Meta:
        model = Opportunity
        fields = (
            "id",
            "title",
            "category",
            "work_mode",
            "city",
            "pay_type",
            "pay_amount",
            "deadline",
            "status",
            "poster",
            "created_at",
        )
        read_only_fields = fields


class OpportunityDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer including all fields for retrieving full opportunity info.
    """

    poster = PosterPublicSerializer(read_only=True)

    class Meta:
        model = Opportunity
        fields = (
            "id",
            "poster",
            "title",
            "description",
            "category",
            "required_skills",
            "pay_type",
            "pay_amount",
            "duration",
            "working_hours",
            "work_mode",
            "location_text",
            "city",
            "latitude",
            "longitude",
            "vacancies",
            "deadline",
            "contact_info",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OpportunityCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating opportunities.
    Validates deadline non-past status, positive vacancies, and sets poster automatically.
    """

    class Meta:
        model = Opportunity
        fields = (
            "id",
            "title",
            "description",
            "category",
            "required_skills",
            "pay_type",
            "pay_amount",
            "duration",
            "working_hours",
            "work_mode",
            "location_text",
            "city",
            "latitude",
            "longitude",
            "vacancies",
            "deadline",
            "contact_info",
            "status",
        )
        read_only_fields = ("id",)

    def validate_deadline(self, value):
        """
        Validate that the deadline is not in the past.
        """
        if value and value < timezone.now().date():
            raise serializers.ValidationError("Deadline cannot be in the past.")
        return value

    def validate_vacancies(self, value):
        """
        Validate that vacancies count is greater than zero.
        """
        if value is not None and value <= 0:
            raise serializers.ValidationError("Vacancies must be greater than zero.")
        return value

    def validate_pay_amount(self, value):
        """
        Validate that pay_amount is non-negative.
        """
        if value is not None and value < 0:
            raise serializers.ValidationError("Pay amount cannot be negative.")
        return value


class SavedOpportunitySerializer(serializers.ModelSerializer):
    """
    Serializer for saved/bookmarked opportunities.
    Nests the OpportunityListSerializer representation and exposes saved_at timestamp.
    `user` is never client-writable.
    """

    opportunity = OpportunityListSerializer(read_only=True)
    saved_at = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = SavedOpportunity
        fields = ("id", "opportunity", "saved_at")
        read_only_fields = ("id", "opportunity", "saved_at")


class ApplicationSerializer(serializers.ModelSerializer):
    """
    Full representation of an application for the applicant's own 'my applications' view.
    """

    opportunity = OpportunityListSerializer(read_only=True)
    applicant = PosterPublicSerializer(read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "opportunity",
            "applicant",
            "status",
            "cover_note",
            "applied_at",
            "updated_at",
        )
        read_only_fields = fields


class ApplicantListSerializer(serializers.ModelSerializer):
    """
    Serializer for opportunity posters viewing applicants to their opportunity.
    Nests applicant user details alongside cover_note, status, and applied_at.
    """

    applicant = PosterPublicSerializer(read_only=True)

    class Meta:
        model = Application
        fields = (
            "id",
            "applicant",
            "status",
            "cover_note",
            "applied_at",
        )
        read_only_fields = fields


class ApplicationCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an application.
    Only cover_note is client-writable.
    Validates opportunity status, applicant role, and unique application constraint.
    """

    class Meta:
        model = Application
        fields = ("id", "cover_note")

    def validate(self, attrs):
        request = self.context.get("request")
        opportunity = self.context.get("opportunity")

        if not request or not request.user:
            raise serializers.ValidationError("Authentication required.")

        user = request.user
        if getattr(user, "role", None) != "student":
            raise serializers.ValidationError("Only students can apply to opportunities.")

        if not opportunity or opportunity.status != Opportunity.Status.OPEN:
            raise serializers.ValidationError("Cannot apply to closed or draft opportunities.")

        if opportunity.poster == user:
            raise serializers.ValidationError("You cannot apply to your own posted opportunity.")

        if Application.objects.filter(applicant=user, opportunity=opportunity).exists():
            raise serializers.ValidationError("You have already applied to this opportunity.")

        return attrs


class ApplicationStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for poster status updates (under_review, accepted, rejected).
    """

    class Meta:
        model = Application
        fields = ("status",)

    def validate_status(self, value):
        allowed_poster_statuses = [
            Application.Status.UNDER_REVIEW,
            Application.Status.ACCEPTED,
            Application.Status.REJECTED,
        ]
        if value not in allowed_poster_statuses:
            raise serializers.ValidationError(
                f"Invalid status transition. Allowed values: {', '.join(allowed_poster_statuses)}"
            )
        return value

