import json
import logging
import os
import urllib.request
import urllib.error
import boto3

logger = logging.getLogger(__name__)


def get_sns_client():
    kwargs = {
        "region_name": os.getenv("AWS_REGION", "us-east-1"),
    }
    endpoint_url = os.getenv("AWS_ENDPOINT_URL")
    if endpoint_url and endpoint_url.strip():
        kwargs["endpoint_url"] = endpoint_url
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    if access_key and secret_key:
        kwargs["aws_access_key_id"] = access_key
        kwargs["aws_secret_access_key"] = secret_key
    return boto3.client("sns", **kwargs)


def _deliver_direct_http(record_body_str: str) -> bool:
    endpoint_url = os.getenv("DELIVERY_ENDPOINT_URL")
    if not endpoint_url:
        logger.warning("DELIVERY_ENDPOINT_URL not set for direct delivery")
        return False
    try:
        req = urllib.request.Request(
            endpoint_url,
            data=record_body_str.encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        logger.warning("Direct delivery POST failed: %s", type(exc).__name__)
        return False


def lambda_handler(event, context=None):
    """
    AWS Lambda handler for SQS event source mapping.
    Iterates SQS records, publishes each event to SNS topic.
    If LAMBDA_DIRECT_DELIVERY is 'true', also performs direct HTTP delivery.
    Returns partial failure batch response: {'batchItemFailures': [{'itemIdentifier': id}, ...]}.
    """
    records = event.get("Records", [])
    batch_item_failures = []

    topic_arn = os.getenv("SNS_TOPIC_ARN", "")
    direct_delivery = os.getenv("LAMBDA_DIRECT_DELIVERY", "false").strip().lower() in ("true", "1", "yes")

    sns_client = None

    for record in records:
        message_id = record.get("messageId")
        body = record.get("body", "")

        try:
            # 1. Publish to SNS topic (default path)
            if not topic_arn:
                raise ValueError("SNS_TOPIC_ARN is not configured")

            if sns_client is None:
                sns_client = get_sns_client()

            sns_client.publish(
                TopicArn=topic_arn,
                Message=body,
            )

            # 2. Optional direct delivery fallback path if enabled
            if direct_delivery:
                success = _deliver_direct_http(body)
                if not success:
                    raise RuntimeError("Direct HTTP delivery failed")

        except Exception as exc:
            logger.warning("Failed to process SQS record %s: %s", message_id, type(exc).__name__)
            if message_id:
                batch_item_failures.append({"itemIdentifier": message_id})

    return {"batchItemFailures": batch_item_failures}
