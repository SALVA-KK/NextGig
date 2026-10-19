import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


def deliver_notification_direct(instance):
    """
    Dispatches direct real-time delivery for a notification:
    1. Real-time WebSocket push via Channels.
    2. Asynchronous FCM push via Celery task.
    """
    recipient_id = instance.recipient_id

    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        serialized_data = NotificationSerializer(instance).data
        group_name = f"user_notifications_{recipient_id}"

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "notification.message",
                "notification": serialized_data,
            },
        )
    except Exception as exc:
        logger.warning(
            "Failed to dispatch real-time WebSocket push for notification %s: %s",
            instance.id,
            type(exc).__name__,
        )

    # Trigger FCM Web Push if enabled and user has active tokens
    try:
        from django.conf import settings
        if getattr(settings, "FCM_ENABLED", False):
            from .models import DeviceToken
            if DeviceToken.objects.filter(user_id=recipient_id, is_active=True).exists():
                from .tasks import send_push_notification
                send_push_notification.delay(instance.id)
    except Exception as exc:
        logger.warning(
            "Failed to enqueue FCM push notification task for notification %s: %s",
            instance.id,
            type(exc).__name__,
        )


@receiver(post_save, sender=Notification)
def notification_post_save_push(sender, instance, created, **kwargs):
    """
    Pushes newly created notifications via WebSocket to the recipient's isolated group.
    - Operates only on newly created instances (created=True).
    - Preserves raw=True guard for fixtures/loaddata.
    - Defers dispatch until transaction commits using transaction.on_commit.
    - Gracefully wraps send in try/except so channel layer / network / Redis failures
      never break notification persistence, Celery tasks, or HTTP requests.
    """
    if kwargs.get("raw", False) or not created:
        return

    def _push():
        from django.conf import settings
        if getattr(settings, "AWS_EVENTS_ENABLED", False):
            try:
                from .aws_events import publish_notification_event
                if publish_notification_event(instance):
                    return
            except Exception as exc:
                logger.warning(
                    "Failed to publish notification %s to SQS, falling back to direct push: %s",
                    instance.id,
                    type(exc).__name__,
                )

        deliver_notification_direct(instance)

    transaction.on_commit(_push)

