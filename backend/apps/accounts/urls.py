from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ChangePasswordView,
    ForgotPasswordView,
    LoginView,
    LogoutView,
    PhoneLoginRequestOTPView,
    PhoneLoginVerifyOTPView,
    RequestOTPView,
    ResetPasswordView,
    StudentRegistrationView,
    UserProfileView,
    VerifyEmailView,
    VerifyOTPView,
)

app_name = "accounts"

urlpatterns = [
    path(
        "register/",
        StudentRegistrationView.as_view(),
        name="student-register",
    ),
    path(
        "verify-email/",
        VerifyEmailView.as_view(),
        name="verify-email",
    ),
    path(
        "login/",
        LoginView.as_view(),
        name="login",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "logout/",
        LogoutView.as_view(),
        name="logout",
    ),
    path(
        "change-password/",
        ChangePasswordView.as_view(),
        name="change-password",
    ),
    path(
        "forgot-password/",
        ForgotPasswordView.as_view(),
        name="forgot-password",
    ),
    path(
        "reset-password/",
        ResetPasswordView.as_view(),
        name="reset-password",
    ),
    path(
        "request-otp/",
        RequestOTPView.as_view(),
        name="request-otp",
    ),
    path(
        "verify-otp/",
        VerifyOTPView.as_view(),
        name="verify-otp",
    ),
    path(
        "phone-login/request-otp/",
        PhoneLoginRequestOTPView.as_view(),
        name="phone-login-request-otp",
    ),
    path(
        "phone-login/verify-otp/",
        PhoneLoginVerifyOTPView.as_view(),
        name="phone-login-verify-otp",
    ),
    path(
        "profile/",
        UserProfileView.as_view(),
        name="user-profile",
    ),
]