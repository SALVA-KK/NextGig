from django.urls import path

from .views import LoginView, StudentRegistrationView, VerifyEmailView

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
]