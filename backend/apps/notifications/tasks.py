import logging
from celery import shared_task
from django.conf import settings
from .models import DeviceToken, Notification
from .fcm import FCMTransientError, send_fcm_v1_message

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=5)
def send_push_notification(self, notification_id: int, token_ids: list[int] | None = None):
    """
    Celery task that delivers a Web Push notification to active device tokens
    belonging to the notification recipient using FCM HTTP v1 API.

    Guarantees:
    - Never logs device token values or credentials.
    - Sends ONLY title, message, notification_type, and notification_id.
    - Deactivates unregistered/invalid tokens (UNREGISTERED, NOT_FOUND, INVALID_ARGUMENT).
    - Retries only failed tokens (not yet delivered) on transient errors (429, 5xx, timeouts),
      finishing the loop for remaining tokens before retrying with only the failed ids.
    - Retries max 2 times with exponential backoff; max retries exceeded does not raise.
    """
    if not getattr(settings, "FCM_ENABLED", False):
        return "fcm_disabled"

    notification = (
        Notification.objects.filter(id=notification_id)
        .select_related("recipient")
        .first()
    )
    if not notification:
        logger.warning("FCM push skipped: Notification %s not found.", notification_id)
        return "not_found"

    token_qs = DeviceToken.objects.filter(
        user=notification.recipient,
        is_active=True,
    )
    if token_ids is not None:
        token_qs = token_qs.filter(id__in=token_ids)

    tokens = list(token_qs.only("id", "token"))
    if not tokens:
        return "no_active_tokens"

    payload_data = {
        "notification_id": str(notification.id),
        "notification_type": str(notification.notification_type),
    }

    deactivated_count = 0
    success_count = 0
    failed_token_ids = []
    last_transient_exc = None

    for dt in tokens:
        try:
            result = send_fcm_v1_message(
                device_token=dt.token,
                title=notification.title,
                body=notification.message,
                data=payload_data,
                link="/dashboard",
            )
            res_status = result.get("status")

            if res_status == "ok":
                success_count += 1
            elif res_status == "deactivate":
                DeviceToken.objects.filter(id=dt.id).update(is_active=False)
                deactivated_count += 1
                logger.info(
                    "FCM token deactivated for notification %s (reason: %s)",
                    notification_id,
                    result.get("error"),
                )
            else:
                logger.warning(
                    "FCM push failed for notification %s (reason: %s)",
                    notification_id,
                    result.get("error"),
                )

        except FCMTransientError as exc:
            failed_token_ids.append(dt.id)
            last_transient_exc = exc
            logger.warning(
                "Transient FCM error for notification %s on retry %s/2: %s",
                notification_id,
                self.request.retries,
                type(exc).__name__,
            )
        except Exception as exc:
            logger.warning(
                "Unexpected error sending FCM push for notification %s: %s",
                notification_id,
                type(exc).__name__,
            )

    logger.info(
        "FCM push completed for notification %s: %d sent, %d deactivated, %d transiently failed.",
        notification_id,
        success_count,
        deactivated_count,
        len(failed_token_ids),
    )

    if failed_token_ids and last_transient_exc is not None:
        try:
            raise self.retry(
                args=[notification_id, failed_token_ids],
                exc=last_transient_exc,
                countdown=5 * (2 ** self.request.retries),
            )
        except self.MaxRetriesExceededError:
            logger.warning(
                "FCM push max retries exceeded for notification %s.",
                notification_id,
            )
            return "max_retries_exceeded"

    return "done"
