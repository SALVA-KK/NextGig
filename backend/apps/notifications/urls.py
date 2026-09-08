from django.urls import path
from .views import (
    MarkAllNotificationsReadView,
    MarkNotificationReadView,
    NotificationDeleteView,
    NotificationListAPIView,
    UnreadNotificationCountView,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListAPIView.as_view(), name="notification-list"),
    path("unread-count/", UnreadNotificationCountView.as_view(), name="notification-unread-count"),
    path("<int:pk>/read/", MarkNotificationReadView.as_view(), name="notification-mark-read"),
    path("mark-all-read/", MarkAllNotificationsReadView.as_view(), name="notification-mark-all-read"),
    path("<int:pk>/", NotificationDeleteView.as_view(), name="notification-delete"),
]
