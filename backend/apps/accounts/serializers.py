from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import CustomUser


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

    class Meta:
        model = CustomUser
        fields = (
            "id",
            "email",
            "full_name",
            "phone_number",
            "password",
            "confirm_password",
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
        Ensure phone number is unique if provided.
        """
        if value:
            cleaned_phone = value.strip()
            if CustomUser.objects.filter(phone_number=cleaned_phone).exists():
                raise serializers.ValidationError(
                    "A user with this phone number already exists."
                )
            return cleaned_phone
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
        """
        # Remove confirm_password field as it is only needed for validation
        validated_data.pop("confirm_password")

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
