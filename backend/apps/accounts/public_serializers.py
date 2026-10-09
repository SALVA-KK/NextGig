from django.contrib.auth import get_user_model
from rest_framework import serializers

from .privacy import get_gated_phone_number, get_gated_whatsapp_number

User = get_user_model()


class PublicStudentListSerializer(serializers.ModelSerializer):
    """
    Public serializer for listing student profiles in search results.
    Excludes email, contact_person, address, show_* flags, internal profile IDs, and admin fields.
    """

    user_id = serializers.IntegerField(source="id", read_only=True)
    full_name = serializers.CharField(read_only=True)
    display_name = serializers.CharField(source="full_name", read_only=True)
    profile_picture = serializers.SerializerMethodField()
    profession = serializers.CharField(
        source="student_profile.profession", default="", read_only=True
    )
    qualification_name = serializers.CharField(
        source="student_profile.qualification_name", default="", read_only=True
    )
    institution = serializers.CharField(
        source="student_profile.institution", default="", read_only=True
    )
    skills = serializers.ListField(
        source="student_profile.skills", default=list, read_only=True
    )
    city = serializers.CharField(
        source="student_profile.city", default="", read_only=True
    )
    availability = serializers.CharField(
        source="student_profile.availability", default="", read_only=True
    )
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "user_id",
            "full_name",
            "display_name",
            "profile_picture",
            "profession",
            "qualification_name",
            "institution",
            "skills",
            "city",
            "availability",
            "role",
        ]
        read_only_fields = fields

    def get_profile_picture(self, user):
        profile = getattr(user, "student_profile", None)
        if not profile or not profile.profile_picture:
            return None
        url = profile.profile_picture.url
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class PublicStudentDetailSerializer(PublicStudentListSerializer):
    """
    Public detail serializer for student profiles.
    Adds bio, languages, portfolio_url, social_links, and gated contact details.
    """

    bio = serializers.CharField(
        source="student_profile.bio", default="", read_only=True
    )
    languages = serializers.ListField(
        source="student_profile.languages", default=list, read_only=True
    )
    portfolio_url = serializers.CharField(
        source="student_profile.portfolio_url", default="", read_only=True
    )
    social_links = serializers.JSONField(
        source="student_profile.social_links", default=dict, read_only=True
    )
    phone_number = serializers.SerializerMethodField()
    whatsapp_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_id",
            "full_name",
            "display_name",
            "profile_picture",
            "profession",
            "qualification_name",
            "institution",
            "skills",
            "city",
            "availability",
            "bio",
            "languages",
            "portfolio_url",
            "social_links",
            "phone_number",
            "whatsapp_number",
            "role",
        ]
        read_only_fields = fields

    def get_phone_number(self, user):
        profile = getattr(user, "student_profile", None)
        return get_gated_phone_number(user, profile)

    def get_whatsapp_number(self, user):
        profile = getattr(user, "student_profile", None)
        return get_gated_whatsapp_number(profile)


class PublicProviderListSerializer(serializers.ModelSerializer):
    """
    Public serializer for listing provider profiles in search results.
    Excludes email, contact_person, address, show_* flags, internal profile IDs, and admin fields.
    """

    user_id = serializers.IntegerField(source="id", read_only=True)
    organization_name = serializers.CharField(
        source="provider_profile.organization_name", default="", read_only=True
    )
    display_name = serializers.CharField(
        source="provider_profile.organization_name", default="", read_only=True
    )
    organization_type = serializers.CharField(
        source="provider_profile.organization_type", default="", read_only=True
    )
    profile_picture = serializers.SerializerMethodField()
    city = serializers.CharField(
        source="provider_profile.city", default="", read_only=True
    )
    is_verified = serializers.BooleanField(
        source="provider_profile.is_verified", default=False, read_only=True
    )
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "user_id",
            "organization_name",
            "display_name",
            "organization_type",
            "profile_picture",
            "city",
            "is_verified",
            "role",
        ]
        read_only_fields = fields

    def get_profile_picture(self, user):
        profile = getattr(user, "provider_profile", None)
        if not profile or not profile.profile_picture:
            return None
        url = profile.profile_picture.url
        request = self.context.get("request")
        if request is not None:
            return request.build_absolute_uri(url)
        return url


class PublicProviderDetailSerializer(PublicProviderListSerializer):
    """
    Public detail serializer for provider profiles.
    Adds description, website, social_links, and gated contact details.
    Does NOT leak address or contact_person.
    """

    description = serializers.CharField(
        source="provider_profile.description", default="", read_only=True
    )
    website = serializers.CharField(
        source="provider_profile.website", default="", read_only=True
    )
    social_links = serializers.JSONField(
        source="provider_profile.social_links", default=dict, read_only=True
    )
    phone_number = serializers.SerializerMethodField()
    whatsapp_number = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "user_id",
            "organization_name",
            "display_name",
            "organization_type",
            "profile_picture",
            "city",
            "is_verified",
            "description",
            "website",
            "social_links",
            "phone_number",
            "whatsapp_number",
            "role",
        ]
        read_only_fields = fields

    def get_phone_number(self, user):
        profile = getattr(user, "provider_profile", None)
        return get_gated_phone_number(user, profile)

    def get_whatsapp_number(self, user):
        profile = getattr(user, "provider_profile", None)
        return get_gated_whatsapp_number(profile)
