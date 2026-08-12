import secrets
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, PhoneOTP, Invitation
from .utils import get_phone_lookup_variants, normalize_phone_number


class StudentRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for Student registration requests.
    Enforces password validation, email/phone uniqueness, and automatically assigns the STUDENT role.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Password must meet standard Django validation rules.",
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Must match the password field.",
    )
    invite_token = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Optional invitation token to link registration with inviter.",
    )

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "full_name",
            "phone_number",
            "password",
            "confirm_password",
            "invite_token",
        )
        read_only_fields = ("id",)

    def validate_email(self, value):
        """
        Ensure email is unique (case-insensitive check) and return normalized email.
        """
        normalized_email = value.strip().lower()
        if CustomUser.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return normalized_email

    def validate_phone_number(self, value):
        """
        Ensure phone number is unique if provided and normalize to E.164.
        """
        if value:
            try:
                normalized_phone = normalize_phone_number(value)
            except ValueError as error:
                raise serializers.ValidationError(str(error))

            variants = get_phone_lookup_variants(normalized_phone)
            if CustomUser.objects.filter(phone_number__in=variants).exists():
                raise serializers.ValidationError(
                    "A user with this phone number already exists."
                )
            return normalized_phone
        return value

    def validate(self, attrs):
        """
        Cross-field validation for password matching and Django password policy enforcement.
        """
        password = attrs.get("password")
        confirm_password = attrs.get("confirm_password")

        if password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "Passwords do not match."}
            )

        # Validate password against Django's AUTH_PASSWORD_VALIDATORS settings
        user_instance = CustomUser(
            email=attrs.get("email"),
            full_name=attrs.get("full_name"),
        )
        try:
            validate_password(password, user=user_instance)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})

        return attrs

    def create(self, validated_data):
        """
        Create and return a new Student user using CustomUserManager.create_user().
        Links user to Invitation if a valid invite_token is provided.
        """
        # Remove confirm_password field as it is only needed for validation
        validated_data.pop("confirm_password")

        # Extract optional invite token
        invite_token = validated_data.pop("invite_token", None)

        # Automatically assign the STUDENT role internally
        validated_data["role"] = CustomUser.Role.STUDENT

        # Extract credentials for CustomUserManager.create_user
        email = validated_data.pop("email")
        password = validated_data.pop("password")

        # Use CustomUserManager.create_user to handle normalization and password hashing
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            **validated_data,
        )

        if invite_token:
            invitation = Invitation.objects.filter(
                token=invite_token,
                is_used=False,
            ).first()
            if invitation:
                invitation.invited_user = user
                invitation.is_used = True
                invitation.save()

        return user


class LoginSerializer(serializers.Serializer):
    """
    Serializer for user authentication requests.
    Validates credentials, account status, and email verification.
    """

    email = serializers.EmailField(
        required=True,
        help_text="Registered email address.",
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Account password.",
    )

    def validate(self, attrs):
        """
        Validates login credentials, authenticates the user, and enforces account status rules.
        """
        email = attrs.get("email", "").strip().lower()
        attrs["email"] = email
        password = attrs.get("password")

        request = self.context.get("request")
        user = authenticate(request=request, email=email, password=password)

        if not user:
            raise serializers.ValidationError("Invalid email or password.")

        if not user.is_active:
            raise serializers.ValidationError("This account has been disabled.")

        if not user.is_verified:
            raise serializers.ValidationError(
                "Please verify your email address before logging in."
            )

        attrs["user"] = user
        return attrs


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for validating refresh tokens for logout/blacklisting requests.
    """

    refresh = serializers.CharField(
        required=True,
        help_text="Refresh token to be blacklisted.",
    )

    def validate(self, attrs):
        """
        Validates that the refresh token is valid and unexpired.
        Stores the RefreshToken instance in validated_data for the view to blacklist.
        """
        refresh_token_str = attrs.get("refresh")
        try:
            attrs["token"] = RefreshToken(refresh_token_str)
        except TokenError:
            raise serializers.ValidationError(
                {"refresh": "Invalid or expired refresh token."}
            )
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for authenticated user password change requests.
    Validates that the new password and confirmation match and conform to security rules.
    """

    old_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Current account password.",
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="New password conforming to security rules.",
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Confirmation of the new password.",
    )

    def validate(self, attrs):
        """
        Cross-field validation ensuring new_password matches confirm_password
        and passes Django password strength validators.
        """
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "New password and confirmation do not match."}
            )

        # Pass request user to validate_password if context is available
        request = self.context.get("request")
        user = request.user if request and hasattr(request, "user") else None

        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"new_password": list(error.messages)})

        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """
    Serializer for password reset requests via email.
    Normalizes input email format without revealing user existence.
    """

    email = serializers.EmailField(
        required=True,
        help_text="Registered email address for password reset instructions.",
    )

    def validate_email(self, value):
        """
        Normalizes the email address by stripping whitespace and converting to lowercase.
        """
        return value.strip().lower()


class ResetPasswordSerializer(serializers.Serializer):
    """
    Serializer for completing a password reset request.
    Validates that the new password and confirmation match and conform to password security policies.
    """

    new_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="New password conforming to security rules.",
    )
    confirm_password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text="Confirmation of the new password.",
    )

    def validate(self, attrs):
        """
        Cross-field validation ensuring new_password matches confirm_password
        and passes Django password strength validators using self.context.get('user').
        """
        new_password = attrs.get("new_password")
        confirm_password = attrs.get("confirm_password")

        if new_password != confirm_password:
            raise serializers.ValidationError(
                {"confirm_password": "New password and confirmation do not match."}
            )

        user = self.context.get("user")
        try:
            validate_password(new_password, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"new_password": list(error.messages)})

        return attrs


class RequestOTPSerializer(serializers.Serializer):
    """
    Serializer for requesting a phone OTP verification code.
    Validates phone number format normalization and workflow purpose choices.
    """

    phone_number = serializers.CharField(
        max_length=20,
        required=True,
        help_text="Target phone number for OTP delivery.",
    )

    purpose = serializers.ChoiceField(
        choices=PhoneOTP.OTPPurpose.choices,
        required=True,
        help_text="Intended workflow purpose for the OTP.",
    )

    def validate_phone_number(self, value):
        """
        Normalizes phone number to standard E.164 format.
        """
        try:
            return normalize_phone_number(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error))


class VerifyOTPSerializer(serializers.Serializer):
    """
    Serializer for verifying a received 6-digit phone OTP code.
    Validates phone number format, OTP string length, and workflow purpose choice.
    """

    phone_number = serializers.CharField(
        max_length=20,
        required=True,
        help_text="Phone number receiving the OTP.",
    )

    otp = serializers.CharField(
        max_length=6,
        min_length=6,
        required=True,
        write_only=True,
        help_text="Six-digit OTP code.",
    )

    purpose = serializers.ChoiceField(
        choices=PhoneOTP.OTPPurpose.choices,
        required=True,
        help_text="Workflow purpose for the OTP.",
    )

    def validate_phone_number(self, value):
        """
        Normalizes phone number to standard E.164 format.
        """
        try:
            return normalize_phone_number(value)
        except ValueError as error:
            raise serializers.ValidationError(str(error))


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving and updating user profile information.
    Excludes sensitive authentication flags (is_verified, is_active, tokens, passwords).
    """

    class Meta:
        model = CustomUser
        fields = (
            "email",
            "full_name",
            "phone_number",
            "role",
            "date_joined",
        )
        read_only_fields = ("email", "role", "date_joined")

    def validate_phone_number(self, value):
        """
        Ensure phone number is unique across users when updated and normalize to E.164.
        """
        if value:
            try:
                normalized_phone = normalize_phone_number(value)
            except ValueError as error:
                raise serializers.ValidationError(str(error))

            user_pk = self.instance.pk if self.instance else None
            variants = get_phone_lookup_variants(normalized_phone)
            if (
                CustomUser.objects.filter(phone_number__in=variants)
                .exclude(pk=user_pk)
                .exists()
            ):
                raise serializers.ValidationError(
                    "A user with this phone number already exists."
                )
            return normalized_phone
        return value


class InvitationResponseSerializer(serializers.Serializer):
    """
    Serializer for invitation creation response payload.
    """

    message = serializers.CharField(help_text="Success status message.")
    invite_url = serializers.CharField(help_text="Full frontend URL for sharing the invitation.")
    token = serializers.CharField(help_text="Unique invitation token.")
    created_at = serializers.DateTimeField(help_text="Timestamp when invitation was generated.")


class InviterPublicSerializer(serializers.Serializer):
    """
    Public representation of the inviter user.
    Hides email, phone, and private attributes.
    """

    id = serializers.IntegerField(help_text="Inviter user ID.")
    full_name = serializers.CharField(help_text="Inviter full name for safe display.")


class PublicInvitationSerializer(serializers.Serializer):
    """
    Serializer for public invitation details query.
    """

    valid = serializers.BooleanField(help_text="Flag indicating whether invitation token is valid and active.")
    inviter = InviterPublicSerializer(required=False, help_text="Public inviter information if valid.")
    detail = serializers.CharField(required=False, help_text="Error message if token is invalid or expired.")


