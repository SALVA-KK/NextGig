from django.contrib import admin
from .models import DeviceToken, Notification


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


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "platform", "is_active", "created_at", "last_seen_at")
    list_filter = ("platform", "is_active", "created_at", "last_seen_at")
    search_fields = ("user__email", "token")
    raw_id_fields = ("user",)
    ordering = ("-last_seen_at",)
