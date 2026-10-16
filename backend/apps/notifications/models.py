from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Notification(models.Model):
    """
    Model representing database-backed in-app user notifications.
    """

    class NotificationType(models.TextChoices):
        NEW_APPLICATION = "new_application", _("New Application Received")
        APPLICATION_STATUS_CHANGED = "application_status_changed", _("Application Status Updated")
        APPLICATION_WITHDRAWN = "application_withdrawn", _("Application Withdrawn")
        OPPORTUNITY_EXPIRED = "opportunity_expired", _("Opportunity Expired")
        OPPORTUNITY_FORCE_CLOSED = "opportunity_force_closed", _("Opportunity Force Closed")
        OPPORTUNITY_REOPENED = "opportunity_reopened", _("Opportunity Reopened")
        PROVIDER_WELCOME = "provider_welcome", _("Welcome Provider")
        PROVIDER_VERIFIED = "provider_verified", _("Provider Verified")
        PROVIDER_UNVERIFIED = "provider_unverified", _("Provider Unverified")
        RECOMMENDATIONS_DIGEST = "recommendations_digest", _("Daily Recommendations Digest")
        NEW_CHAT_MESSAGE = "new_chat_message", _("New Chat Message")

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()

    opportunity = models.ForeignKey(
        "opportunities.Opportunity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    application = models.ForeignKey(
        "opportunities.Application",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )

    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    event_key = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "notifications"
        verbose_name = _("notification")
        verbose_name_plural = _("notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["recipient", "is_read", "-created_at"],
                name="notif_recip_read_created_idx",
            ),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.email} ({self.notification_type}) - Read={self.is_read}"


class DeviceToken(models.Model):
    """
    Model storing FCM device registration tokens for web push notifications.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_tokens",
        db_index=True,
    )
    token = models.CharField(max_length=512, unique=True, db_index=True)
    platform = models.CharField(max_length=50, default="web")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_device_tokens"
        verbose_name = _("device token")
        verbose_name_plural = _("device tokens")
        ordering = ["-last_seen_at"]

    def __str__(self):
        return f"DeviceToken({self.user_id}, {self.platform}, active={self.is_active})"
