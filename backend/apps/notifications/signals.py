import logging
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from .serializers import NotificationSerializer

logger = logging.getLogger(__name__)


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

    recipient_id = instance.recipient_id

    def _push():
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

    transaction.on_commit(_push)
