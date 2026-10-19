import json
import logging
import urllib.request
from unittest.mock import MagicMock, call, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.notifications.aws_events import (
    publish_notification_event,
    reset_sqs_client,
)
from apps.notifications.models import Notification
from apps.notifications.signals import deliver_notification_direct
from aws_lambda.notification_handler.handler import lambda_handler
from config.settings import RedactSecretFilter

User = get_user_model()


class RedactionFilterTests(TestCase):
    def setUp(self):
        self.filter = RedactSecretFilter()

    def test_redaction_filter_replaces_secret_in_msg(self):
        record = logging.LogRecord(
            name="django.server",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg='POST /api/internal/notifications/deliver/super-secret-xyz/ HTTP/1.1 200',
            args=(),
            exc_info=None,
        )
        self.assertTrue(self.filter.filter(record))
        self.assertNotIn("super-secret-xyz", record.msg)
        self.assertIn("/api/internal/notifications/deliver/[REDACTED]/", record.msg)

    def test_redaction_filter_replaces_secret_in_args_tuple(self):
        record = logging.LogRecord(
            name="django.server",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg='"%s" %s',
            args=(
                "POST /api/internal/notifications/deliver/my-secret-key-12345/ HTTP/1.1",
                403,
            ),
            exc_info=None,
        )
        self.assertTrue(self.filter.filter(record))
        self.assertNotIn("my-secret-key-12345", record.args[0])
        self.assertIn("/api/internal/notifications/deliver/[REDACTED]/", record.args[0])

    def test_redaction_filter_replaces_secret_in_args_dict(self):
        record = logging.LogRecord(
            name="django.request",
            level=logging.WARNING,
            pathname=__file__,
            lineno=10,
            msg='Access denied on %(path)s',
            args=(
                {"path": "/api/internal/notifications/deliver/dict-secret-token/"},
            ),
            exc_info=None,
        )
        self.assertTrue(self.filter.filter(record))
        self.assertNotIn("dict-secret-token", record.args["path"])
        self.assertIn("/api/internal/notifications/deliver/[REDACTED]/", record.args["path"])


class SQSPublishAndSignalTests(TestCase):
    def setUp(self):
        reset_sqs_client()
        cache.clear()
        self.user = User.objects.create_user(
            email="sqs_user@example.com",
            password="Password123!",
            full_name="SQS User",
            role="student",
            is_verified=True,
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
            title="SQS Test Notif",
            message="Testing SQS message payload",
        )

    def tearDown(self):
        reset_sqs_client()

    @patch("apps.notifications.aws_events.get_sqs_client")
    @patch("apps.notifications.aws_events.get_queue_url", return_value="https://sqs.us-east-1.amazonaws.com/123/queue")
    def test_publish_payload_exact_fields(self, mock_get_url, mock_get_client):
        mock_sqs = MagicMock()
        mock_get_client.return_value = mock_sqs

        success = publish_notification_event(self.notification)
        self.assertTrue(success)

        mock_sqs.send_message.assert_called_once()
        call_kwargs = mock_sqs.send_message.call_args[1]
        self.assertEqual(call_kwargs["QueueUrl"], "https://sqs.us-east-1.amazonaws.com/123/queue")

        payload = json.loads(call_kwargs["MessageBody"])
        expected_payload = {
            "notification_id": self.notification.id,
            "recipient_id": self.user.id,
            "notification_type": str(self.notification.notification_type),
        }
        self.assertEqual(payload, expected_payload)
        self.assertEqual(set(payload.keys()), {"notification_id", "recipient_id", "notification_type"})

    @override_settings(AWS_EVENTS_ENABLED=True)
    @patch("apps.notifications.aws_events.publish_notification_event", return_value=False)
    @patch("apps.notifications.signals.deliver_notification_direct")
    def test_publish_failure_falls_back_to_direct_push(self, mock_deliver, mock_publish):
        with self.captureOnCommitCallbacks(execute=True):
            Notification.objects.create(
                recipient=self.user,
                notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                title="Fallback Notif",
                message="Fallback test",
            )
        mock_publish.assert_called_once()
        mock_deliver.assert_called_once()

    @override_settings(AWS_EVENTS_ENABLED=False)
    @patch("apps.notifications.aws_events.publish_notification_event")
    @patch("apps.notifications.signals.deliver_notification_direct")
    def test_flag_disabled_preserves_direct_push(self, mock_deliver, mock_publish):
        with self.captureOnCommitCallbacks(execute=True):
            Notification.objects.create(
                recipient=self.user,
                notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                title="Flag Off Notif",
                message="Flag off test",
            )
        mock_publish.assert_not_called()
        mock_deliver.assert_called_once()


class InternalDeliveryEndpointTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="endpoint_user@example.com",
            password="Password123!",
            full_name="Endpoint User",
            role="student",
            is_verified=True,
        )
        self.notif = Notification.objects.create(
            recipient=self.user,
            notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
            title="Endpoint Notif",
            message="Endpoint test body",
        )
        self.secret = "test-internal-secret"

    @override_settings(INTERNAL_SERVICE_SECRET="")
    def test_empty_configured_secret_returns_403(self):
        # Even when supplied secret is also empty, it must reject with 403
        resp1 = self.client.post("/api/internal/notifications/deliver/test-secret/", data={}, format="json")
        self.assertEqual(resp1.status_code, status.HTTP_403_FORBIDDEN)

        resp2 = self.client.post("/api/internal/notifications/deliver//", data={}, format="json")
        self.assertIn(resp2.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    @override_settings(INTERNAL_SERVICE_SECRET="correct-secret")
    def test_wrong_secret_returns_403(self):
        resp = self.client.post(
            "/api/internal/notifications/deliver/wrong-secret/",
            data=json.dumps({"notification_id": self.notif.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(INTERNAL_SERVICE_SECRET="test-secret")
    @patch("apps.notifications.internal_views.deliver_notification_direct")
    def test_text_plain_content_type_accepted(self, mock_deliver):
        payload = json.dumps({"notification_id": self.notif.id})
        resp = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=payload,
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "delivered")
        mock_deliver.assert_called_once_with(self.notif)

    @override_settings(INTERNAL_SERVICE_SECRET="test-secret")
    @patch("apps.notifications.internal_views.deliver_notification_direct")
    def test_sns_envelope_accepted(self, mock_deliver):
        sns_envelope = {
            "Type": "Notification",
            "MessageId": "sns-msg-12345",
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:nextgig-notifications-topic",
            "Message": json.dumps({"notification_id": self.notif.id}),
            "Timestamp": "2026-10-19T10:00:00.000Z",
        }
        resp = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=json.dumps(sns_envelope),
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "delivered")
        mock_deliver.assert_called_once_with(self.notif)

    @override_settings(INTERNAL_SERVICE_SECRET="test-secret")
    @patch("apps.notifications.internal_views.deliver_notification_direct")
    def test_raw_json_body_accepted(self, mock_deliver):
        resp = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=json.dumps({"notification_id": self.notif.id}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "delivered")
        mock_deliver.assert_called_once_with(self.notif)

    @override_settings(INTERNAL_SERVICE_SECRET="test-secret")
    def test_non_int_notification_id_returns_400(self):
        cases = [
            {"notification_id": "string-id"},
            {"notification_id": True},
            {"notification_id": None},
            {"notification_id": 12.34},
            {},
        ]
        for data in cases:
            resp = self.client.post(
                "/api/internal/notifications/deliver/test-secret/",
                data=json.dumps(data),
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(INTERNAL_SERVICE_SECRET="test-secret")
    def test_unknown_notification_id_returns_404(self):
        resp = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=json.dumps({"notification_id": 999999}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @override_settings(
        INTERNAL_SERVICE_SECRET="test-secret",
        AWS_SNS_TOPIC_ARN="arn:aws:sns:us-east-1:123456789012:configured-topic",
    )
    @patch("apps.notifications.internal_views.get_sns_client")
    def test_confirm_subscription_called_with_configured_topic_arn(self, mock_get_sns):
        mock_sns = MagicMock()
        mock_get_sns.return_value = mock_sns

        sub_confirmation = {
            "Type": "SubscriptionConfirmation",
            "Token": "236245235342-token-abc",
            "TopicArn": "arn:aws:sns:attacker-forged-arn",
            "SubscribeURL": "http://attacker-controlled.com/confirm",
        }
        resp = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=json.dumps(sub_confirmation),
            content_type="text/plain",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()["status"], "confirmed")

        mock_sns.confirm_subscription.assert_called_once_with(
            TopicArn="arn:aws:sns:us-east-1:123456789012:configured-topic",
            Token="236245235342-token-abc",
        )

    @override_settings(INTERNAL_SERVICE_SECRET="test-secret")
    @patch("apps.notifications.internal_views.deliver_notification_direct")
    def test_failed_delivery_does_not_poison_dedupe(self, mock_deliver):
        mock_deliver.side_effect = RuntimeError("WebSocket cluster failure")

        resp1 = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=json.dumps({"notification_id": self.notif.id}),
            content_type="application/json",
        )
        self.assertEqual(resp1.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Dedupe key must NOT remain set
        dedupe_key = f"notif_delivered:{self.notif.id}"
        self.assertIsNone(cache.get(dedupe_key))

        # Subsequent retry without failure succeeds and caches dedupe key
        mock_deliver.side_effect = None
        resp2 = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=json.dumps({"notification_id": self.notif.id}),
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.json()["status"], "delivered")
        self.assertEqual(cache.get(dedupe_key), 1)

    @override_settings(INTERNAL_SERVICE_SECRET="test-secret")
    @patch("apps.notifications.internal_views.deliver_notification_direct")
    def test_successful_delivery_deduplicates(self, mock_deliver):
        resp1 = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=json.dumps({"notification_id": self.notif.id}),
            content_type="application/json",
        )
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertEqual(resp1.json()["status"], "delivered")
        self.assertEqual(mock_deliver.call_count, 1)

        # Second delivery request for same notification is deduplicated
        resp2 = self.client.post(
            "/api/internal/notifications/deliver/test-secret/",
            data=json.dumps({"notification_id": self.notif.id}),
            content_type="application/json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.json()["status"], "duplicate_skipped")
        self.assertEqual(mock_deliver.call_count, 1)


class LambdaHandlerTests(TestCase):
    @patch.dict("os.environ", {
        "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:nextgig-topic",
        "LAMBDA_DIRECT_DELIVERY": "false",
    })
    @patch("aws_lambda.notification_handler.handler.get_sns_client")
    @patch("urllib.request.urlopen")
    def test_handler_publishes_to_sns_and_does_not_call_urllib(self, mock_urlopen, mock_get_sns):
        mock_sns = MagicMock()
        mock_get_sns.return_value = mock_sns

        event = {
            "Records": [
                {
                    "messageId": "msg-001",
                    "body": json.dumps({"notification_id": 10, "recipient_id": 1, "notification_type": "status"}),
                }
            ]
        }
        res = lambda_handler(event, None)
        self.assertEqual(res, {"batchItemFailures": []})

        mock_sns.publish.assert_called_once_with(
            TopicArn="arn:aws:sns:us-east-1:123456789012:nextgig-topic",
            Message=json.dumps({"notification_id": 10, "recipient_id": 1, "notification_type": "status"}),
        )
        mock_urlopen.assert_not_called()

    @patch.dict("os.environ", {
        "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:nextgig-topic",
        "LAMBDA_DIRECT_DELIVERY": "true",
        "DELIVERY_ENDPOINT_URL": "http://web:8000/api/internal/notifications/deliver/secret/",
    })
    @patch("aws_lambda.notification_handler.handler.get_sns_client")
    @patch("urllib.request.urlopen")
    def test_handler_direct_delivery_calls_urllib(self, mock_urlopen, mock_get_sns):
        mock_sns = MagicMock()
        mock_get_sns.return_value = mock_sns

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        event = {
            "Records": [
                {
                    "messageId": "msg-002",
                    "body": json.dumps({"notification_id": 20}),
                }
            ]
        }
        res = lambda_handler(event, None)
        self.assertEqual(res, {"batchItemFailures": []})
        mock_sns.publish.assert_called_once()
        mock_urlopen.assert_called_once()

    @patch.dict("os.environ", {
        "SNS_TOPIC_ARN": "arn:aws:sns:us-east-1:123456789012:nextgig-topic",
        "LAMBDA_DIRECT_DELIVERY": "false",
    })
    @patch("aws_lambda.notification_handler.handler.get_sns_client")
    def test_handler_partial_failures(self, mock_get_sns):
        mock_sns = MagicMock()
        mock_get_sns.return_value = mock_sns

        def _publish_side_effect(**kwargs):
            if "msg-fail" in kwargs.get("Message", ""):
                raise RuntimeError("SNS throttle")
            return {"MessageId": "sns-1"}

        mock_sns.publish.side_effect = _publish_side_effect

        event = {
            "Records": [
                {"messageId": "msg-1", "body": "msg-success"},
                {"messageId": "msg-2", "body": "msg-fail"},
                {"messageId": "msg-3", "body": "msg-success-2"},
            ]
        }
        res = lambda_handler(event, None)
        self.assertEqual(res, {
            "batchItemFailures": [
                {"itemIdentifier": "msg-2"},
            ]
        })


class PollQueueCommandTests(TestCase):
    @patch("boto3.client")
    @patch("apps.notifications.management.commands.poll_notification_queue.lambda_handler")
    def test_poll_queue_deletes_only_successful_messages(self, mock_handler, mock_boto):
        mock_sqs = MagicMock()
        mock_boto.return_value = mock_sqs

        mock_sqs.get_queue_url.return_value = {"QueueUrl": "https://sqs.us-east-1.amazonaws.com/123/queue"}
        mock_sqs.receive_message.return_value = {
            "Messages": [
                {"MessageId": "msg-success-1", "ReceiptHandle": "rcpt-1", "Body": '{"id": 1}'},
                {"MessageId": "msg-fail-2", "ReceiptHandle": "rcpt-2", "Body": '{"id": 2}'},
                {"MessageId": "msg-success-3", "ReceiptHandle": "rcpt-3", "Body": '{"id": 3}'},
            ]
        }

        mock_handler.return_value = {
            "batchItemFailures": [
                {"itemIdentifier": "msg-fail-2"},
            ]
        }

        call_command("poll_notification_queue", "--once")

        # delete_message should be called for msg-success-1 and msg-success-3, NOT for msg-fail-2
        delete_calls = mock_sqs.delete_message.call_args_list
        deleted_receipts = [c[1]["ReceiptHandle"] for c in delete_calls]

        self.assertIn("rcpt-1", deleted_receipts)
        self.assertIn("rcpt-3", deleted_receipts)
        self.assertNotIn("rcpt-2", deleted_receipts)
        self.assertEqual(len(deleted_receipts), 2)
