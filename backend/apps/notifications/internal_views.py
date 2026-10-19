import hmac
import json
import logging
import boto3
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .signals import deliver_notification_direct

logger = logging.getLogger(__name__)


def get_sns_client():
    kwargs = {
        "region_name": getattr(settings, "AWS_REGION", "us-east-1"),
    }
    endpoint_url = getattr(settings, "AWS_ENDPOINT_URL", None)
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
    secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key
    return boto3.client("sns", **kwargs)


class NotificationDeliverInternalView(APIView):
    """
    Internal service endpoint for notification delivery via SQS -> Lambda -> SNS -> HTTP.
    Authenticated exclusively via URL secret matched against settings.INTERNAL_SERVICE_SECRET.
    Never uses JWT or session auth.
    """
    authentication_classes = []
    permission_classes = []
    throttle_classes = []
    parser_classes = []  # Read raw request.body directly to support text/plain and application/json

    def post(self, request, secret=None):
        # 1. Secret authentication
        configured_secret = getattr(settings, "INTERNAL_SERVICE_SECRET", "")
        # Reject every request if configured secret is empty or unset, before comparing
        if not configured_secret:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not secret:
            return Response(status=status.HTTP_403_FORBIDDEN)
        if not hmac.compare_digest(secret.encode("utf-8"), configured_secret.encode("utf-8")):
            return Response(status=status.HTTP_403_FORBIDDEN)

        # 2. Parse request body (supports application/json, text/plain, etc.)
        try:
            body_str = request.body.decode("utf-8")
            data = json.loads(body_str)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if not isinstance(data, dict):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # 3. Handle SubscriptionConfirmation
        msg_type = data.get("Type")
        if msg_type == "SubscriptionConfirmation":
            token = data.get("Token")
            if not token:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            topic_arn = getattr(settings, "AWS_SNS_TOPIC_ARN", "")
            if not topic_arn:
                topic_name = getattr(settings, "AWS_SNS_TOPIC_NAME", "nextgig-notifications-topic")
                region = getattr(settings, "AWS_REGION", "us-east-1")
                topic_arn = f"arn:aws:sns:{region}:123456789012:{topic_name}"
            try:
                sns_client = get_sns_client()
                sns_client.confirm_subscription(
                    TopicArn=topic_arn,
                    Token=token,
                )
                logger.info("Confirmed SNS subscription for configured topic ARN")
                return Response({"status": "confirmed"}, status=status.HTTP_200_OK)
            except Exception as exc:
                logger.warning("Failed to confirm SNS subscription: %s", type(exc).__name__)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. Handle Notification (SNS envelope or raw JSON)
        if msg_type == "Notification":
            message_raw = data.get("Message")
            if isinstance(message_raw, str):
                try:
                    payload = json.loads(message_raw)
                except Exception:
                    return Response(status=status.HTTP_400_BAD_REQUEST)
            elif isinstance(message_raw, dict):
                payload = message_raw
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        else:
            payload = data

        if not isinstance(payload, dict):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # 5. Validate notification_id is strictly an int (and not bool or other type)
        notification_id = payload.get("notification_id")
        if notification_id is None or isinstance(notification_id, bool) or not isinstance(notification_id, int):
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # 6. Check dedupe cache before delivery
        dedupe_key = f"notif_delivered:{notification_id}"
        if cache.get(dedupe_key):
            return Response(
                {"status": "duplicate_skipped", "notification_id": notification_id},
                status=status.HTTP_200_OK,
            )

        # 7. Load notification from DB
        notification = (
            Notification.objects.filter(id=notification_id)
            .select_related("recipient")
            .first()
        )
        if not notification:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # 8. Deliver and update dedupe cache only after delivery succeeds
        try:
            deliver_notification_direct(notification)
            cache.add(dedupe_key, 1, timeout=86400)
        except Exception as exc:
            cache.delete(dedupe_key)
            logger.warning(
                "Internal delivery failed for notification %s: %s",
                notification_id,
                type(exc).__name__,
            )
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(
            {"status": "delivered", "notification_id": notification_id},
            status=status.HTTP_200_OK,
        )
