from django.urls import path

from .views import StudentRegistrationView

app_name = "accounts"

urlpatterns = [
    path("register/", StudentRegistrationView.as_view(), name="student-register"),
]
