import json
import boto3
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Idempotently sets up SQS queues (main + DLQ), SNS topic, and HTTP subscription."

    def handle(self, *args, **options):
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
        sns = boto3.client("sns", **boto_kwargs)

        dlq_name = getattr(settings, "AWS_SQS_DLQ_NAME", "nextgig-notifications-dlq")
        queue_name = getattr(settings, "AWS_SQS_QUEUE_NAME", "nextgig-notifications-queue")
        topic_name = getattr(settings, "AWS_SNS_TOPIC_NAME", "nextgig-notifications-topic")
        secret = getattr(settings, "INTERNAL_SERVICE_SECRET", "")

        # 1. Create or get DLQ
        dlq_resp = sqs.create_queue(QueueName=dlq_name)
        dlq_url = dlq_resp["QueueUrl"]
        dlq_attrs = sqs.get_queue_attributes(QueueUrl=dlq_url, AttributeNames=["QueueArn"])
        dlq_arn = dlq_attrs["Attributes"]["QueueArn"]

        # 2. Create or get Main Queue with redrive policy targeting DLQ
        redrive_policy = json.dumps({
            "deadLetterTargetArn": dlq_arn,
            "maxReceiveCount": "3",
        })
        sqs.create_queue(
            QueueName=queue_name,
            Attributes={"RedrivePolicy": redrive_policy},
        )

        # 3. Create or get SNS Topic
        topic_resp = sns.create_topic(Name=topic_name)
        topic_arn = topic_resp["TopicArn"]

        # 4. Create HTTP subscription from SNS topic to internal delivery endpoint
        delivery_url = f"http://web:8000/api/internal/notifications/deliver/{secret}/"
        try:
            sns.subscribe(
                TopicArn=topic_arn,
                Protocol="http",
                Endpoint=delivery_url,
                Attributes={"RawMessageDelivery": "true"},
            )
        except Exception:
            sns.subscribe(
                TopicArn=topic_arn,
                Protocol="http",
                Endpoint=delivery_url,
            )

        # Output resource names, counts, and topic ARN; NEVER the subscription URL or secret
        self.stdout.write(self.style.SUCCESS(
            f"Successfully verified resources: DLQ '{dlq_name}', Queue '{queue_name}', Topic '{topic_name}' (ARN: {topic_arn}, 1 subscription configured)."
        ))

