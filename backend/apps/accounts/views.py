import logging

from django.contrib.auth.models import update_last_login
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import LoginSerializer, StudentRegistrationSerializer
from .utils import send_verification_email

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
