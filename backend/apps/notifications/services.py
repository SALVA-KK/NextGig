import logging
from django.db import IntegrityError
from .models import Notification

logger = logging.getLogger(__name__)


def create_notification(
    recipient,
    notification_type,
    title,
    message,
    actor=None,
    opportunity=None,
    application=None,
    event_key=None,
):
    """
    Helper function to safely create in-app database notifications.
    Uses the database's unique constraint on `event_key` via get_or_create / IntegrityError
    to prevent duplicate notifications concurrently.
    Does NOT wrap operations in an independent transaction boundary; it operates within
    the caller's atomic transaction context.
    """
    if event_key:
        try:
            notification, created = Notification.objects.get_or_create(
                event_key=event_key,
                defaults={
                    "recipient": recipient,
                    "actor": actor,
                    "notification_type": notification_type,
                    "title": title,
                    "message": message,
                    "opportunity": opportunity,
                    "application": application,
                },
            )
            return notification
        except IntegrityError:
            logger.info(f"Duplicate notification attempt blocked by unique event_key='{event_key}'.")
            return Notification.objects.filter(event_key=event_key).first()

    return Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        opportunity=opportunity,
        application=application,
    )
