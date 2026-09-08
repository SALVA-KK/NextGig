from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recipient",
        "actor",
        "notification_type",
        "title",
        "is_read",
        "created_at",
    )
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = (
        "recipient__email",
        "actor__email",
        "title",
        "message",
        "event_key",
    )
    raw_id_fields = ("recipient", "actor", "opportunity", "application")
    ordering = ("-created_at",)
