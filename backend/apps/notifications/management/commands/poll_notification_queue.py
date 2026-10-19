import logging
import time
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand

from aws_lambda.notification_handler.handler import lambda_handler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Long-polls SQS notifications queue as a stand-in for Lambda event-source mapping."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Poll the queue once and exit immediately.",
        )
        parser.add_argument(
            "--wait-time",
            type=int,
            default=20,
            help="Long poll wait time in seconds (default: 20).",
        )

    def handle(self, *args, **options):
        run_once = options["once"]
        wait_time = options["wait_time"]

        endpoint_url = getattr(settings, "AWS_ENDPOINT_URL", None)
        region = getattr(settings, "AWS_REGION", "us-east-1")
        access_key = getattr(settings, "AWS_ACCESS_KEY_ID", "test")
        secret_key = getattr(settings, "AWS_SECRET_ACCESS_KEY", "test")

        boto_kwargs = {
            "region_name": region,
        }
        if endpoint_url:
            boto_kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            boto_kwargs["aws_access_key_id"] = access_key
            boto_kwargs["aws_secret_access_key"] = secret_key

        sqs = boto3.client("sqs", **boto_kwargs)
        queue_name = getattr(settings, "AWS_SQS_QUEUE_NAME", "nextgig-notifications-queue")

        queue_url = None

        while True:
            # 1. Resolve Queue URL with retry if not yet created
            if not queue_url:
                try:
                    resp = sqs.get_queue_url(QueueName=queue_name)
                    queue_url = resp["QueueUrl"]
                except ClientError as exc:
                    error_code = exc.response.get("Error", {}).get("Code", "")
                    if error_code in ("AWS.SimpleQueueService.NonExistentQueue", "QueueDoesNotExist"):
                        self.stdout.write(f"Queue '{queue_name}' does not exist yet; waiting to retry...")
                        if run_once:
                            break
                        time.sleep(5)
                        continue
                    else:
                        logger.warning("Error resolving queue URL: %s", type(exc).__name__)
                        if run_once:
                            break
                        time.sleep(5)
                        continue
                except Exception as exc:
                    logger.warning("Unexpected error resolving queue URL: %s", type(exc).__name__)
                    if run_once:
                        break
                    time.sleep(5)
                    continue

            # 2. Receive messages (long polling)
            try:
                resp = sqs.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=wait_time if not run_once else 1,
                    VisibilityTimeout=30,
                )
            except Exception as exc:
                logger.warning("Error receiving messages from SQS: %s", type(exc).__name__)
                if run_once:
                    break
                queue_url = None
                time.sleep(2)
                continue

            messages = resp.get("Messages", [])
            if not messages:
                if run_once:
                    break
                continue

            # 3. Format as SQS event and invoke Lambda handler in-process
            sqs_records = []
            for msg in messages:
                sqs_records.append({
                    "messageId": msg["MessageId"],
                    "receiptHandle": msg["ReceiptHandle"],
                    "body": msg["Body"],
                    "attributes": msg.get("Attributes", {}),
                })

            sqs_event = {"Records": sqs_records}
            result = lambda_handler(sqs_event, None)
            failures = result.get("batchItemFailures", [])
            failed_ids = {f.get("itemIdentifier") for f in failures if f.get("itemIdentifier")}

            # 4. Delete ONLY successful messages
            for msg in messages:
                msg_id = msg["MessageId"]
                if msg_id not in failed_ids:
                    try:
                        sqs.delete_message(
                            QueueUrl=queue_url,
                            ReceiptHandle=msg["ReceiptHandle"],
                        )
                    except Exception as exc:
                        logger.warning("Failed to delete processed message %s: %s", msg_id, type(exc).__name__)

            if run_once:
                break
