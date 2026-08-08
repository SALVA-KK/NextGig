import logging

from django.contrib.auth.models import update_last_login
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser, PhoneOTP
from .serializers import (
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RequestOTPSerializer,
    ResetPasswordSerializer,
    StudentRegistrationSerializer,
    VerifyOTPSerializer,
)
from .utils import (
    create_phone_otp,
    send_password_reset_email,
    send_phone_otp,
    send_verification_email,
    verify_phone_otp,
)

logger = logging.getLogger(__name__)


class StudentRegistrationView(generics.CreateAPIView):
    """
    API endpoint that allows unauthenticated users to register a new Student account.
    Triggers email verification sending gracefully upon successful registration.
    """

    serializer_class = StudentRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        """
        Processes student registration and sends verification email.
        If email sending fails, the account creation persists cleanly.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

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

    @extend_schema(
        request=LoginSerializer,
        responses={200: None},
        summary="Login user",
        description="Authenticate a verified user using email and password and return JWT access and refresh tokens.",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates login payload, retrieves authenticated user, updates last_login, and returns JWT tokens.
        """
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
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

        phone_number = serializer.validated_data["phone_number"]
        purpose = serializer.validated_data["purpose"]

        otp = create_phone_otp(phone_number, purpose)
        send_phone_otp(phone_number, otp, purpose)

        return Response(
            {
                "message": "If the phone number is eligible, an OTP has been sent."
            },
            status=status.HTTP_200_OK,
        )


class VerifyOTPView(APIView):
    """
    API endpoint to verify a submitted phone OTP code.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: None},
        summary="Verify phone OTP",
        description="Verifies a previously issued phone OTP.",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates payload structure and evaluates OTP validity against the database record.
        """
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]
        purpose = serializer.validated_data["purpose"]

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


class PhoneLoginRequestOTPView(APIView):
    """
    API endpoint that sends a login OTP code to a registered phone number.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=RequestOTPSerializer,
        responses={200: None},
        summary="Request phone login OTP",
        description="Sends a login OTP to a registered phone number.",
    )
    def post(self, request, *args, **kwargs):
        """
        Validates target phone number, verifies account existence and verification status, and dispatches login OTP.
        """
        payload = {
            "phone_number": request.data.get("phone_number"),
            "purpose": PhoneOTP.OTPPurpose.LOGIN,
        }
        serializer = RequestOTPSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        purpose = PhoneOTP.OTPPurpose.LOGIN

        if CustomUser.objects.filter(phone_number=phone_number, is_verified=True).exists():
            otp = create_phone_otp(phone_number, purpose)
            send_phone_otp(phone_number, otp, purpose)

        return Response(
            {
                "message": "If the phone number is registered, an OTP has been sent."
            },
            status=status.HTTP_200_OK,
        )


class PhoneLoginVerifyOTPView(APIView):
    """
    API endpoint that authenticates a verified user using phone OTP.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        request=VerifyOTPSerializer,
        responses={200: None},
        summary="Phone login",
        description="Authenticates a verified user using phone OTP.",
    )
    def post(self, request, *args, **kwargs):
        """
        Verifies phone login OTP, retrieves verified user, updates last_login, and returns JWT tokens.
        """
        payload = {
            "phone_number": request.data.get("phone_number"),
            "otp": request.data.get("otp"),
            "purpose": PhoneOTP.OTPPurpose.LOGIN,
        }
        serializer = VerifyOTPSerializer(data=payload)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data["phone_number"]
        otp = serializer.validated_data["otp"]

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

        try:
            user = CustomUser.objects.get(phone_number=phone_number, is_verified=True)
        except CustomUser.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired OTP."},
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
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
            status=status.HTTP_200_OK,
        )

