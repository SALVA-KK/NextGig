from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework import serializers

from .models import Application, Opportunity, SavedOpportunity, RecommendedOpportunity

User = get_user_model()


from rest_framework.exceptions import PermissionDenied


class PosterPublicSerializer(serializers.ModelSerializer):
    """
    Public nested representation of the user who posted the opportunity.
    Enforces server-side contact privacy for poster phone/WhatsApp.
    """

    phone_number = serializers.SerializerMethodField()
    whatsapp_number = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()
    organization_name = serializers.SerializerMethodField()
    is_verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "email",
            "phone_number",
            "whatsapp_number",
            "profile_picture",
            "social_links",
            "organization_name",
            "is_verified",
        )
        read_only_fields = fields

    def get_profile(self, user):
        if getattr(user, "role", None) == "provider":
            try:
                return user.provider_profile
            except ObjectDoesNotExist:
                return None
        elif getattr(user, "role", None) == "student":
            try:
                return user.student_profile
            except ObjectDoesNotExist:
                return None
        try:
            return user.provider_profile
        except ObjectDoesNotExist:
            try:
                return user.student_profile
            except ObjectDoesNotExist:
                return None

    def get_phone_number(self, user):
        profile = self.get_profile(user)
        if profile and getattr(profile, "show_phone", False):
            if hasattr(profile, "phone_number") and profile.phone_number:
                return profile.phone_number
            return getattr(user, "phone_number", None)
        return None

    def get_whatsapp_number(self, user):
        profile = self.get_profile(user)
        if profile and getattr(profile, "show_whatsapp", False):
            return getattr(profile, "whatsapp_number", None)
        return None

    def get_profile_picture(self, user):
        profile = self.get_profile(user)
        if not profile:
            return None
        pic = getattr(profile, "profile_picture", None)
        if pic and hasattr(pic, "url") and pic.url:
            return pic.url
        logo = getattr(profile, "logo", None)
        if logo and hasattr(logo, "url") and logo.url:
            return logo.url
        return None

    def get_social_links(self, user):
        profile = self.get_profile(user)
        if profile:
            return getattr(profile, "social_links", {}) or {}
        return {}

    def get_organization_name(self, user):
        profile = self.get_profile(user)
        if profile and hasattr(profile, "organization_name"):
            return profile.organization_name
        return None

    def get_is_verified(self, user):
        profile = self.get_profile(user)
        if profile and hasattr(profile, "is_verified"):
            return bool(profile.is_verified)
        return False


class ApplicantPublicSerializer(serializers.ModelSerializer):
    """
    Public nested representation of an applicant for opportunity posters.
    Enforces server-side contact privacy (phone/WhatsApp).
    Nests student profile information (skills, bio, social_links, etc.).
    """

    phone_number = serializers.SerializerMethodField()
    whatsapp_number = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    profession = serializers.SerializerMethodField()
    qualification_type = serializers.SerializerMethodField()
    qualification_name = serializers.SerializerMethodField()
    institution = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()
    city = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()
    languages = serializers.SerializerMethodField()
    social_links = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "full_name",
            "email",
            "phone_number",
            "whatsapp_number",
            "profile_picture",
            "profession",
            "qualification_type",
            "qualification_name",
            "institution",
            "skills",
            "bio",
            "city",
            "availability",
            "languages",
            "social_links",
        )
        read_only_fields = fields

    def get_profile(self, user):
        try:
            return user.student_profile
        except ObjectDoesNotExist:
            return None

    def get_phone_number(self, user):
        profile = self.get_profile(user)
        if profile and getattr(profile, "show_phone", False):
            if hasattr(profile, "phone_number") and profile.phone_number:
                return profile.phone_number
            return getattr(user, "phone_number", None)
        return None

    def get_whatsapp_number(self, user):
        profile = self.get_profile(user)
        if profile and getattr(profile, "show_whatsapp", False):
            return getattr(profile, "whatsapp_number", None)
        return None

    def get_profile_picture(self, user):
        profile = self.get_profile(user)
        if profile and profile.profile_picture:
            return profile.profile_picture.url
        return None

    def get_profession(self, user):
        profile = self.get_profile(user)
        return profile.profession if profile else ""

    def get_qualification_type(self, user):
        profile = self.get_profile(user)
        return profile.qualification_type if profile else ""

    def get_qualification_name(self, user):
        profile = self.get_profile(user)
        return profile.qualification_name if profile else ""

    def get_institution(self, user):
        profile = self.get_profile(user)
        return profile.institution if profile else ""

    def get_skills(self, user):
        profile = self.get_profile(user)
        return profile.skills if profile else []

    def get_bio(self, user):
        profile = self.get_profile(user)
        return profile.bio if profile else ""

    def get_city(self, user):
        profile = self.get_profile(user)
        return profile.city if profile else ""

    def get_availability(self, user):
        profile = self.get_profile(user)
        return profile.availability if profile else ""

    def get_languages(self, user):
        profile = self.get_profile(user)
        return profile.languages if profile else []

    def get_social_links(self, user):
        profile = self.get_profile(user)
        return profile.social_links if (profile and profile.social_links) else {}



class OpportunityListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing opportunities (omits long description text).
    """

    poster = PosterPublicSerializer(read_only=True)
    applicants_count = serializers.IntegerField(source="applications.count", read_only=True)

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
            "close_reason",
            "closed_by",
            "poster",
            "created_at",
            "applicants_count",
        )
        read_only_fields = fields


class OpportunityDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer including all fields for retrieving full opportunity info.
    """

    poster = PosterPublicSerializer(read_only=True)
    applicants_count = serializers.IntegerField(source="applications.count", read_only=True)

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
            "close_reason",
            "closed_by",
            "created_at",
            "updated_at",
            "applicants_count",
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
            "close_reason",
            "closed_by",
        )
        read_only_fields = ("id", "close_reason", "closed_by")

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance
        new_status = attrs.get("status")

        if instance and new_status and instance.status == Opportunity.Status.CLOSED and new_status == Opportunity.Status.OPEN:
            if instance.close_reason == Opportunity.CloseReason.ADMIN_MODERATED:
                request = self.context.get("request")
                user = getattr(request, "user", None) if request else None
                is_admin = user and (getattr(user, "role", None) == "admin" or getattr(user, "is_staff", False))
                if not is_admin:
                    raise PermissionDenied("This listing was closed by an admin and can only be reopened by an admin.")
        return attrs

    def validate_deadline(self, value):
        """
        Validate that the deadline is not in the past.
        """
        if value and value < timezone.localdate():
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

    def update(self, instance, validated_data):
        new_status = validated_data.get("status", instance.status)
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None

        if new_status == Opportunity.Status.CLOSED and instance.status != Opportunity.Status.CLOSED:
            if not validated_data.get("close_reason"):
                validated_data["close_reason"] = Opportunity.CloseReason.OWNER_CLOSED
                validated_data["closed_by"] = user
        elif new_status == Opportunity.Status.OPEN and instance.status == Opportunity.Status.CLOSED:
            validated_data["close_reason"] = None
            validated_data["closed_by"] = None

        return super().update(instance, validated_data)


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


class RecommendedOpportunitySerializer(serializers.ModelSerializer):
    """
    Serializer for daily recommended opportunities.
    Nests OpportunityListSerializer representation and exposes match score.
    """

    opportunity = OpportunityListSerializer(read_only=True)

    class Meta:
        model = RecommendedOpportunity
        fields = ("id", "score", "opportunity", "created_at")
        read_only_fields = fields



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
    Nests applicant user details alongside cover_note, status, applied_at, applicant resume metadata, and opportunity info.
    """

    applicant = ApplicantPublicSerializer(read_only=True)
    opportunity = OpportunityListSerializer(read_only=True)
    has_resume = serializers.SerializerMethodField()
    resume_download_url = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = (
            "id",
            "opportunity",
            "applicant",
            "status",
            "cover_note",
            "applied_at",
            "has_resume",
            "resume_download_url",
        )
        read_only_fields = fields

    def get_has_resume(self, obj):
        from apps.accounts.views import get_user_resume

        resume = get_user_resume(obj.applicant)
        return bool(resume and resume.file)

    def get_resume_download_url(self, obj):
        from apps.accounts.views import get_user_resume

        resume = get_user_resume(obj.applicant)
        if resume and resume.file:
            return f"/api/applications/{obj.id}/resume/"
        return None



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

        if opportunity.deadline and opportunity.deadline < timezone.localdate():
            raise serializers.ValidationError("This opportunity's deadline has passed.")

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

