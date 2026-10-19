import json
import logging
import boto3
from botocore.config import Config
from django.conf import settings

logger = logging.getLogger(__name__)

_SQS_CLIENT = None
_QUEUE_URL = None


def get_sqs_client():
    global _SQS_CLIENT
    if _SQS_CLIENT is None:
        config = Config(
            connect_timeout=2,
            read_timeout=3,
            retries={"max_attempts": 0},
        )
        kwargs = {
            "region_name": getattr(settings, "AWS_REGION", "us-east-1"),
            "config": config,
        }
        endpoint_url = getattr(settings, "AWS_ENDPOINT_URL", None)
        if endpoint_url:
            kwargs["endpoint_url"] = endpoint_url
        access_key = getattr(settings, "AWS_ACCESS_KEY_ID", None)
        secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
        if access_key and secret_key:
            kwargs["aws_access_key_id"] = access_key
            kwargs["aws_secret_access_key"] = secret_key

        _SQS_CLIENT = boto3.client("sqs", **kwargs)
    return _SQS_CLIENT


def get_queue_url(sqs_client=None):
    global _QUEUE_URL
    if _QUEUE_URL is not None:
        return _QUEUE_URL
    client = sqs_client or get_sqs_client()
    queue_name = getattr(settings, "AWS_SQS_QUEUE_NAME", "nextgig-notifications-queue")
    response = client.get_queue_url(QueueName=queue_name)
    _QUEUE_URL = response["QueueUrl"]
    return _QUEUE_URL


def reset_sqs_client():
    global _SQS_CLIENT, _QUEUE_URL
    _SQS_CLIENT = None
    _QUEUE_URL = None


def publish_notification_event(notification) -> bool:
    """
    Publishes an IDs-only notification event to the configured SQS queue.
    Payload strictly contains:
      - notification_id
      - recipient_id
      - notification_type
    Returns True on success, False on any failure. Never raises.
    """
    try:
        sqs = get_sqs_client()
        queue_url = get_queue_url(sqs)
        payload = {
            "notification_id": notification.id,
            "recipient_id": notification.recipient_id,
            "notification_type": str(notification.notification_type),
        }
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(payload),
        )
        return True
    except Exception as exc:
        logger.warning(
            "Failed to publish notification %s to SQS: %s",
            getattr(notification, "id", None),
            type(exc).__name__,
        )
        return False
