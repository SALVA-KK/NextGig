from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, LogoutView, StudentRegistrationView, VerifyEmailView

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
]