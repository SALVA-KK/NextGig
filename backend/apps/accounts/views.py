import logging
import pyotp
import secrets
import time

from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema, inline_serializer
from rest_framework import generics, serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from .models import AdminMFA, CustomUser, PhoneOTP, Invitation
from .permissions import IsAdminRole
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    InvitationResponseSerializer,
    LoginSerializer,
    LogoutSerializer,
    PublicInvitationSerializer,
    RequestOTPSerializer,
    ResetPasswordSerializer,
    StudentRegistrationSerializer,
    UserProfileSerializer,
    VerifyOTPSerializer,
)

# OpenAPI Inline Serializers for Swagger Documentation
AuthUserResponseSerializer = inline_serializer(
    name="AuthUserResponse",
    fields={
        "id": serializers.IntegerField(help_text="User ID"),
        "email": serializers.EmailField(help_text="User email address"),
        "full_name": serializers.CharField(help_text="User's full name"),
        "role": serializers.CharField(help_text="User role (student, provider, admin)"),
    },
)

TokenResponseSerializer = inline_serializer(
    name="TokenResponse",
    fields={
        "message": serializers.CharField(),
        "access": serializers.CharField(help_text="JWT access token"),
        "refresh": serializers.CharField(help_text="JWT refresh token"),
        "user": AuthUserResponseSerializer,
    },
)

LoginResponseSerializer = inline_serializer(
    name="LoginResponse",
    fields={
        "message": serializers.CharField(),
        "access": serializers.CharField(required=False, help_text="JWT access token"),
        "refresh": serializers.CharField(required=False, help_text="JWT refresh token"),
        "user": AuthUserResponseSerializer,
        "mfa_required": serializers.BooleanField(required=False, help_text="True if admin MFA verification is required"),
        "mfa_token": serializers.CharField(required=False, help_text="Pre-auth MFA session token"),
    },
)

AdminMFAVerifyRequestSerializer = inline_serializer(
    name="AdminMFAVerifyRequest",
    fields={
        "mfa_token": serializers.CharField(help_text="Pre-authentication MFA session token"),
        "otp_code": serializers.CharField(help_text="6-digit TOTP code or emergency backup code"),
    },
)

AdminMFAConfirmRequestSerializer = inline_serializer(
    name="AdminMFAConfirmRequest",
    fields={
        "otp_code": serializers.CharField(help_text="First 6-digit TOTP code from authenticator app"),
    },
)

AdminMFADisableRequestSerializer = inline_serializer(
    name="AdminMFADisableRequest",
    fields={
        "password": serializers.CharField(help_text="Current admin password"),
        "otp_code": serializers.CharField(help_text="6-digit TOTP code or emergency backup code"),
    },
)


class DecoratedTokenRefreshView(TokenRefreshView):
    """
    API endpoint to refresh JWT access token using a valid refresh token.
    Documented for OpenAPI/Swagger without requiring an access token header.
    """

    @extend_schema(
        auth=[],
        summary="Refresh JWT access token",
        description="Refresh JWT access token using a valid refresh token.",
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

from .utils import (
    create_mfa_preauth_token,
    create_phone_otp,
    generate_backup_recovery_codes,
    generate_qr_code_data_uri,
    generate_totp_secret,
    get_phone_lookup_variants,
    get_secret_fingerprint,
    get_totp_provisioning_uri,
    send_existing_account_email,
    send_password_reset_email,
    send_phone_otp,
    send_verification_email,
    verify_and_consume_backup_code,
    verify_mfa_preauth_token,
    verify_phone_otp,
    verify_totp_code,
)

from .throttling import (
    ForgotPasswordEmailRateThrottle,
    ForgotPasswordIPRateThrottle,
    RegisterBurstRateThrottle,
    RegisterSustainedRateThrottle,
)

from .firebase import verify_firebase_id_token

logger = logging.getLogger(__name__)


class StudentRegistrationView(generics.CreateAPIView):
    """
    API endpoint that allows unauthenticated users to register a new Student account.
    Triggers email verification sending gracefully upon successful registration.
    """

    serializer_class = StudentRegistrationSerializer
    permission_classes = [AllowAny]
    throttle_classes = [RegisterBurstRateThrottle, RegisterSustainedRateThrottle]

    @extend_schema(
        summary="Register new student account",
        description="Allows unauthenticated users to register a new Student account.",
    )
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        """
        Processes student registration and sends verification email.
        If email belongs to an existing account, sends an notification email to owner.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        if getattr(serializer, "is_duplicate", False):
            try:
                send_existing_account_email(user)
            except Exception as exc:
                logger.error("Failed to send existing account email to %s: %s", user.email, exc)

            return Response(
                {
                    "message": "Student account registered successfully. Please check your email to verify your account.",
                    "user": {
                        "id": user.id,
                        "email": user.email,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        email_sent = True
        try:
            send_verification_email(user)
        except Exception as exc:
            logger.error("Failed to send verification email to %s: %s", user.email, exc)
            email_sent = False

        if email_sent:
            message = "Student account registered successfully. Please check your email to verify your account."
        else:
            message = "Student account registered successfully, but verification email could not be sent. Please request a resend later."

        return Response(
            {
                "message": message,
                "user": {
                    "id": user.id,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """
    API endpoint to verify user email address using uid and token query parameters.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="uid",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Base64 encoded user ID",
                required=True,
            ),
            OpenApiParameter(
                name="token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Email verification token",
                required=True,
            ),
        ],
        responses={200: None},
        summary="Verify email",
        description="Verify user email address using uid and token query parameters.",
    )
    def get(self, request, *args, **kwargs):
        """
        Validates uid and token query params to verify email address.
        """
        uidb64 = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uidb64 or not token:
            return Response(
                {"error": "Both 'uid' and 'token' query parameters are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            if user.is_verified:
                return Response(
                    {"message": "Email is already verified."},
                    status=status.HTTP_200_OK,
                )

            user.is_verified = True
            if user.email_verified_at is None:
                user.email_verified_at = timezone.now()

            user.save(update_fields=["is_verified", "email_verified_at"])

            return Response(
                {"message": "Email verified successfully."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"error": "Invalid or expired verification link."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class LoginView(APIView):
    """
    API endpoint that allows users to authenticate with email and password,
    returning JWT access and refresh tokens upon successful verification.
    """

    permission_classes = [AllowAny]
    throttle_scope = "login"

    @extend_schema(
        request=LoginSerializer,
        responses={200: LoginResponseSerializer},
        summary="Login user",
        description="Authenticate a verified user using email and password and return JWT access and refresh tokens (or MFA challenge for admin).",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates login payload, retrieves authenticated user, updates last_login, and returns JWT tokens.
        """
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        # Check if Admin has MFA active
        admin_mfa = AdminMFA.objects.filter(user=user).first()
        if user.role == CustomUser.Role.ADMIN and admin_mfa and admin_mfa.is_enabled:
            mfa_token = create_mfa_preauth_token(user)
            return Response(
                {
                    "mfa_required": True,
                    "mfa_token": mfa_token,
                    "message": "MFA verification required.",
                },
                status=status.HTTP_200_OK,
            )

        update_last_login(None, user)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    API endpoint to log out a user by blacklisting their refresh token.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=LogoutSerializer,
        responses={200: None},
        summary="Logout user",
        description="Blacklist the provided refresh token to revoke the user session.",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates refresh token payload and adds it to the token blacklist database.
        """
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data["token"]
        token.blacklist()

        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )


class ChangePasswordView(APIView):
    """
    API endpoint that allows an authenticated user to change their password securely.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: None},
        summary="Change password",
        description="Allows an authenticated user to change their password.",
    )
    def post(self, request, *args, **kwargs):
        """
        Verifies current password, ensures non-reuse of current password, and updates password.
        """
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        user = request.user

        if not user.check_password(old_password):
            return Response(
                {"old_password": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.check_password(new_password):
            return Response(
                {
                    "new_password": "New password cannot be the same as the current password."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password changed successfully."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordView(APIView):
    """
    API endpoint that allows unauthenticated users to request a password reset email.
    """

    permission_classes = [AllowAny]
    throttle_classes = [ForgotPasswordIPRateThrottle, ForgotPasswordEmailRateThrottle]

    @extend_schema(
        request=ForgotPasswordSerializer,
        responses={200: None},
        summary="Forgot password",
        description="Request a password reset email.",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates email format and dispatches password reset instructions if account exists.
        """
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]

        try:
            user = CustomUser.objects.get(email__iexact=email)
            send_password_reset_email(user)
        except CustomUser.DoesNotExist:
            pass

        return Response(
            {
                "message": "If an account with that email exists, a password reset link has been sent."
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    API endpoint to reset a user's password using a valid uid and password reset token.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=ResetPasswordSerializer,
        parameters=[
            OpenApiParameter(
                name="uid",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Base64 encoded user ID",
                required=True,
            ),
            OpenApiParameter(
                name="token",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Password reset token",
                required=True,
            ),
        ],
        responses={200: None},
        summary="Reset password",
        description="Reset a user's password using a valid uid and password reset token.",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates reset parameters (uid, token), executes password validation, and sets new password.
        """
        uidb64 = request.query_params.get("uid")
        token = request.query_params.get("token")

        if not uidb64 or not token:
            return Response(
                {"detail": "Invalid password reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response(
                {"detail": "Invalid password reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Password reset link is invalid or has expired."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ResetPasswordSerializer(
            data=request.data,
            context={"user": user},
        )
        serializer.is_valid(raise_exception=True)

        new_password = serializer.validated_data["new_password"]
        user.set_password(new_password)
        user.save()

        return Response(
            {"message": "Password reset successful."},
            status=status.HTTP_200_OK,
        )


class RequestOTPView(APIView):
    """
    API endpoint that allows unauthenticated users to request a phone OTP code.
    """

    permission_classes = [AllowAny]
    throttle_scope = "login"

    @extend_schema(
        request=RequestOTPSerializer,
        responses={200: None},
        summary="Request phone OTP",
        description="Generates and dispatches a 6-digit phone OTP code for authentication/verification workflows.",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates payload, creates database OTP hash record, and dispatches SMS delivery.
        """
        serializer = RequestOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                "message": "SMS dispatch is managed on the client via Firebase Phone Authentication.",
                "notice": "For Firebase Phone Auth, call client SDK signInWithPhoneNumber and send id_token to /verify-otp/."
            },
            status=status.HTTP_200_OK,
        )


class VerifyOTPView(APIView):
    """
    API endpoint to verify a submitted phone OTP code or Firebase ID token.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: None},
        summary="Verify phone OTP / Firebase ID token",
        description="Verifies a client-side Firebase ID token or fallback MSG91 6-digit phone OTP code.",
    )
    def post(self, request, *args, **kwargs):
        """
        Verifies Firebase ID token (or legacy OTP) and returns verification confirmation.
        """
        id_token = request.data.get("id_token")
        phone_number = request.data.get("phone_number")
        otp = request.data.get("otp")
        purpose = request.data.get("purpose", PhoneOTP.OTPPurpose.LOGIN)

        if id_token:
            verified_phone = verify_firebase_id_token(id_token)
            if not verified_phone:
                return Response(
                    {"detail": "Invalid or expired Firebase ID token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"message": "OTP verified successfully.", "phone_number": verified_phone},
                status=status.HTTP_200_OK,
            )

        if phone_number and otp:
            is_valid = verify_phone_otp(
                phone_number=phone_number,
                otp=otp,
                purpose=purpose,
            )
            if not is_valid:
                return Response(
                    {"detail": "Invalid or expired OTP."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"message": "OTP verified successfully."},
                status=status.HTTP_200_OK,
            )

        return Response(
            {"detail": "Either 'id_token' or both 'phone_number' and 'otp' are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )


class PhoneLoginRequestOTPView(APIView):
    """
    API endpoint that sends a login OTP code to a registered phone number.
    (Deprecated in favor of Firebase Phone Auth client-side SMS dispatch).
    """

    permission_classes = [AllowAny]
    throttle_scope = "login"

    @extend_schema(
        request=RequestOTPSerializer,
        responses={200: None},
        summary="Request phone login OTP",
        description="Sends a login OTP to a registered phone number.",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates target phone number, verifies account existence, and dispatches login OTP.
        """
        payload = {
            "phone_number": request.data.get("phone_number"),
            "purpose": PhoneOTP.OTPPurpose.LOGIN,
        }
        serializer = RequestOTPSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        return Response(
            {
                "message": "SMS dispatch is managed on the client via Firebase Phone Authentication.",
                "notice": "For Firebase Phone Auth, call client SDK signInWithPhoneNumber and send id_token to /verify-otp/."
            },
            status=status.HTTP_200_OK,
        )


class PhoneLoginVerifyOTPView(APIView):
    """
    API endpoint that authenticates a verified user using Firebase Phone Auth ID token or legacy OTP.
    """

    permission_classes = [AllowAny]
    throttle_scope = "login"

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: TokenResponseSerializer},
        summary="Phone login",
        description="Authenticates a verified user using Firebase ID token (or legacy OTP) and returns JWT access and refresh tokens.",
    )
    def post(self, request, *args, **kwargs):
        """
        Verifies Firebase ID token or phone OTP, retrieves user, updates last_login, and returns JWT tokens.
        """
        id_token = request.data.get("id_token")
        phone_number = request.data.get("phone_number")
        otp = request.data.get("otp")

        verified_phone = None

        if id_token:
            verified_phone = verify_firebase_id_token(id_token)
            if not verified_phone:
                return Response(
                    {"detail": "Invalid or expired Firebase ID token."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        elif phone_number and otp:
            is_valid = verify_phone_otp(
                phone_number=phone_number,
                otp=otp,
                purpose=PhoneOTP.OTPPurpose.LOGIN,
            )
            if not is_valid:
                return Response(
                    {"detail": "Invalid or expired OTP."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            verified_phone = phone_number
        else:
            return Response(
                {"detail": "Either 'id_token' or both 'phone_number' and 'otp' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variants = get_phone_lookup_variants(verified_phone)
        user = CustomUser.objects.filter(phone_number__in=variants, is_verified=True).first()
        if not user:
            return Response(
                {"detail": "No active user account found matching this verified phone number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {"detail": "This account has been disabled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_last_login(None, user)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "Phone login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API endpoint to retrieve and update the authenticated user's profile information.
    Requires JWT authentication.
    """

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Returns the current authenticated user instance.
        """
        return self.request.user

    @extend_schema(
        summary="Get user profile",
        description="Retrieve current authenticated user's profile details.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update user profile",
        description="Update current authenticated user's profile details (full_name, phone_number).",
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(
        summary="Replace user profile",
        description="Replace current authenticated user's profile details (full_name, phone_number).",
    )
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class AdminMFAVerifyView(APIView):
    """
    API endpoint for verifying Admin MFA (TOTP code or single-use recovery code)
    during pre-auth login state before issuing final SimpleJWT tokens.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=AdminMFAVerifyRequestSerializer,
        responses={200: TokenResponseSerializer},
        summary="Verify Admin MFA TOTP / Backup Code",
        description="Verifies pre-auth MFA token with 6-digit TOTP code or emergency backup code to issue final SimpleJWT tokens.",
    )
    def post(self, request, *args, **kwargs):
        mfa_token = request.data.get("mfa_token")
        otp_code = request.data.get("otp_code")

        if not mfa_token or not otp_code:
            return Response(
                {"detail": "MFA token and verification code are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_pk = verify_mfa_preauth_token(mfa_token)
        if not user_pk:
            return Response(
                {"detail": "Invalid or expired MFA pre-authentication session token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = CustomUser.objects.get(pk=user_pk, role=CustomUser.Role.ADMIN)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Invalid MFA authentication user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin_mfa = AdminMFA.objects.filter(user=user).first()
        if not admin_mfa or not admin_mfa.is_enabled:
            return Response(
                {"detail": "MFA is not enabled for this administrator."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify TOTP code or Backup recovery code
        is_totp_valid = verify_totp_code(admin_mfa.totp_secret, otp_code)
        is_backup_valid = False
        if not is_totp_valid:
            is_backup_valid = verify_and_consume_backup_code(admin_mfa, otp_code)

        if not is_totp_valid and not is_backup_valid:
            return Response(
                {"detail": "Invalid 6-digit authenticator code or emergency recovery code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        update_last_login(None, user)
        refresh = RefreshToken.for_user(user)

        return Response(
            {
                "message": "MFA login successful.",
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role,
                },
            },
            status=status.HTTP_200_OK,
        )


class AdminMFASetupView(APIView):
    """
    API endpoint for authenticated admins to initiate TOTP MFA enrollment.
    Generates secret, QR code data URI, and emergency backup codes.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        summary="Initiate Admin MFA Setup",
        description="Generates TOTP Base32 secret, QR code image URI, and 8 single-use emergency backup recovery codes.",
    )
    def post(self, request, *args, **kwargs):
        admin_mfa, created = AdminMFA.objects.get_or_create(user=request.user)

        if admin_mfa.is_enabled:
            return Response(
                {"detail": "Admin MFA is already enabled on this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        force_reset = request.data.get("reset", False)

        if not admin_mfa.totp_secret or force_reset:
            totp_secret = generate_totp_secret()
            plain_backup_codes, hashed_backup_codes = generate_backup_recovery_codes()

            admin_mfa.totp_secret = totp_secret
            admin_mfa.backup_codes = hashed_backup_codes
            admin_mfa.save()
        else:
            totp_secret = admin_mfa.totp_secret
            plain_backup_codes = []

        logger.warning(
            "[MFA FINGERPRINT DIAGNOSTIC] Setup View - DB secret_fp=%s",
            get_secret_fingerprint(totp_secret),
        )

        provisioning_uri = get_totp_provisioning_uri(totp_secret, request.user.email)
        qr_code_data_uri = generate_qr_code_data_uri(provisioning_uri)

        return Response(
            {
                "secret": totp_secret,
                "qr_code": qr_code_data_uri,
                "backup_codes": plain_backup_codes,
            },
            status=status.HTTP_200_OK,
        )


class AdminMFAConfirmView(APIView):
    """
    API endpoint for confirming and activating Admin MFA setup with first 6-digit TOTP code.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        request=AdminMFAConfirmRequestSerializer,
        responses={200: inline_serializer(name="AdminMFAConfirmResponse", fields={"message": serializers.CharField()})},
        summary="Confirm and Enable Admin MFA",
        description="Verifies the first 6-digit TOTP code to confirm authenticator app scanning and activate MFA.",
    )
    def post(self, request, *args, **kwargs):
        admin_mfa = AdminMFA.objects.filter(user=request.user).first()
        raw_code = request.data.get("otp_code")
        data_keys = list(request.data.keys()) if hasattr(request.data, "keys") else []
        code_len = len(str(raw_code).strip()) if raw_code else 0

        logger.warning(
            "[MFA CONFIRM ENTRY DIAGNOSTIC] user_id=%s | request_data_keys=%s | received_code_len=%d | admin_mfa_exists=%s | is_enabled=%s | has_secret=%s",
            request.user.pk if hasattr(request, "user") and request.user else None,
            data_keys,
            code_len,
            bool(admin_mfa),
            admin_mfa.is_enabled if admin_mfa else False,
            bool(admin_mfa.totp_secret) if admin_mfa else False,
        )

        otp_code = request.data.get("otp_code")
        if not otp_code:
            return Response(
                {"detail": "Verification code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not admin_mfa or not admin_mfa.totp_secret:
            return Response(
                {"detail": "MFA setup has not been initiated. Please start setup first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if admin_mfa.is_enabled:
            return Response(
                {"detail": "MFA is already active on this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        totp = pyotp.TOTP(admin_mfa.totp_secret)
        current_backend_code = totp.now()
        cleaned_code = str(otp_code).strip()

        logger.warning(
            "[MFA FINGERPRINT DIAGNOSTIC] Confirm View - db_secret_fp=%s | digits=%s | interval=%s | digest=%s | user_id=%s | received_len=%d | backend_current_len=%d | is_exact_match=%s",
            get_secret_fingerprint(admin_mfa.totp_secret),
            totp.digits,
            totp.interval,
            getattr(totp.digest, "__name__", str(totp.digest)),
            request.user.pk,
            len(cleaned_code),
            len(current_backend_code),
            cleaned_code == current_backend_code,
        )

        if not verify_totp_code(admin_mfa.totp_secret, otp_code):
            return Response(
                {"detail": "Invalid verification code. Please check your authenticator app and try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin_mfa.is_enabled = True
        admin_mfa.save()

        return Response(
            {"message": "Admin Multi-Factor Authentication (MFA) has been successfully activated."},
            status=status.HTTP_200_OK,
        )


class AdminMFADisableView(APIView):
    """
    API endpoint for authenticated admins to disable MFA after password & TOTP code verification.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        request=AdminMFADisableRequestSerializer,
        responses={200: inline_serializer(name="AdminMFADisableResponse", fields={"message": serializers.CharField()})},
        summary="Disable Admin MFA",
        description="Disables MFA for an admin account after verifying current password and 6-digit TOTP code.",
    )
    def post(self, request, *args, **kwargs):
        password = request.data.get("password")
        otp_code = request.data.get("otp_code")

        if not password or not otp_code:
            return Response(
                {"detail": "Password and verification code are required to disable MFA."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.check_password(password):
            return Response(
                {"detail": "Invalid password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin_mfa = AdminMFA.objects.filter(user=request.user).first()
        if not admin_mfa or not admin_mfa.is_enabled:
            return Response(
                {"detail": "MFA is not currently active on this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        is_totp_valid = verify_totp_code(admin_mfa.totp_secret, otp_code)
        is_backup_valid = False
        if not is_totp_valid:
            is_backup_valid = verify_and_consume_backup_code(admin_mfa, otp_code)

        if not is_totp_valid and not is_backup_valid:
            return Response(
                {"detail": "Invalid verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin_mfa.is_enabled = False
        admin_mfa.save()

        return Response(
            {"message": "Admin MFA has been disabled."},
            status=status.HTTP_200_OK,
        )


class AdminMFAStatusView(APIView):
    """
    API endpoint to check current Admin MFA status.
    """

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        summary="Get Admin MFA Status",
        description="Returns whether Admin MFA is enabled on the authenticated admin account.",
    )
    def get(self, request, *args, **kwargs):
        admin_mfa = AdminMFA.objects.filter(user=request.user).first()
        is_enabled = bool(admin_mfa and admin_mfa.is_enabled)
        return Response({"is_enabled": is_enabled}, status=status.HTTP_200_OK)


class InvitationCreateView(APIView):
    """
    API endpoint that allows authenticated users to generate a unique invitation link.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Generate platform invitation link",
        description="Generates a unique invitation link for the authenticated user to share.",
        responses={201: InvitationResponseSerializer},
    )
    def post(self, request, *args, **kwargs):
        token = secrets.token_urlsafe(32)
        invitation = Invitation.objects.create(
            inviter=request.user,
            token=token,
        )

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        invite_url = f"{frontend_url}/invite/{token}"

        return Response(
            {
                "message": "Invitation link created successfully.",
                "invite_url": invite_url,
                "token": token,
                "created_at": invitation.created_at,
            },
            status=status.HTTP_201_CREATED,
        )


class InvitationDetailView(APIView):
    """
    Public API endpoint to retrieve invitation details by token.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Retrieve public invitation details",
        description="Validates invitation token and safely returns inviter display information.",
        responses={200: PublicInvitationSerializer, 404: PublicInvitationSerializer},
    )
    def get(self, request, token, *args, **kwargs):
        invitation = Invitation.objects.filter(token=token, is_used=False).first()

        if not invitation:
            return Response(
                {
                    "valid": False,
                    "detail": "Invalid or expired invitation link.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        if invitation.expires_at and timezone.now() > invitation.expires_at:
            return Response(
                {
                    "valid": False,
                    "detail": "This invitation link has expired.",
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "valid": True,
                "inviter": {
                    "id": invitation.inviter.id,
                    "full_name": invitation.inviter.full_name,
                },
            },
            status=status.HTTP_200_OK,
        )




