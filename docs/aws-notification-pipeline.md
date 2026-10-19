# AWS Notification Pipeline Design (Moto Emulation)

## 1. Architectural Overview

The notification delivery pipeline decouples in-app notification creation from downstream delivery (WebSocket broadcast and FCM push) through an asynchronous AWS messaging pipeline:

```text
[Django Database Transaction Commit]
       │
       ▼
apps.notifications.signals (notification_post_save_push)
       │
       ▼
apps.notifications.aws_events (publish_notification_event)
       │
       ▼
  [SQS Queue: nextgig-notifications-queue] ──(redrive maxReceiveCount: 3)──> [SQS DLQ: nextgig-notifications-dlq]
       │
       ▼
Lambda Handler (aws_lambda.notification_handler.handler)
       │ (Invoked in dev via poll_notification_queue command)
       ▼
  [SNS Topic: nextgig-notifications-topic]
       │
       ▼ (HTTP Subscription)
Django Internal Endpoint: POST /api/internal/notifications/deliver/<secret>/
       │
       ├─► Validates URL shared secret via hmac.compare_digest
       ├─► Deduplicates delivery via cache.add("notif_delivered:<id>")
       └─► Invokes deliver_notification_direct()
              ├─► Django Channels WebSocket group_send (real-time UI update)
              └─► Celery FCM push notification task (send_push_notification.delay)
```

---

## 2. Emulated vs. Real Components in Local Development

In the local Docker environment, AWS infrastructure is emulated using the open-source **Moto** server (`motoserver/moto:5.0.5`):

| Component | Status in Local Dev | Implementation Details |
| :--- | :--- | :--- |
| **SQS (Main Queue & DLQ)** | **Emulated** | Handled by Moto standalone server running at `http://moto:5000`. |
| **SNS (Topic & Subscription)** | **Emulated** | Handled by Moto standalone server running at `http://moto:5000`. |
| **Lambda Event Source Mapping** | **Emulated (Stand-in)** | Real Lambda execution in Moto is **not** used. Instead, the `python manage.py poll_notification_queue` management command (running in the `lambda_poller` Docker service) acts as a local event-source mapping stand-in. It long-polls SQS, invokes `lambda_handler(event, None)` in-process, and deletes only successful messages. |
| **Django Internal Delivery Endpoint** | **Real** | Runs on `nextgig_web` (`/api/internal/notifications/deliver/<secret>/`). Authenticates requests, inspects payload, and deduplicates. |
| **WebSocket Delivery** | **Real** | Uses Django Channels and Redis channel layer to deliver real-time messages to active browser clients. |
| **FCM Delivery** | **Real / Configured** | Uses Celery worker and Firebase Admin SDK / HTTP v1 API. |

---

## 3. Fallback and Resilience Guarantees

1. **SQS Publish Failure Fallback**:
   - If SQS publishing fails (e.g. SQS is unreachable or `AWS_EVENTS_ENABLED` is `false`), the post-save signal immediately falls back to direct synchronous/Celery delivery via `deliver_notification_direct()`. Database saves and user actions are never interrupted.
2. **Idempotency & Deduplication**:
   - The delivery endpoint deduplicates requests using `cache.add("notif_delivered:<id>", 1, timeout=86400)`. Duplicate deliveries are safely skipped.
   - If delivery execution raises an error, the dedupe key is cleared so SQS/SNS retries can succeed.
3. **Partial Batch Failures**:
   - The Lambda handler accumulates failed record IDs in `batchItemFailures`, ensuring SQS redrives only unacknowledged or failed messages until reaching the Dead Letter Queue (DLQ).

---

## 4. How to Switch to Production AWS

To transition from the local Moto emulator to real Amazon Web Services:

1. **Remove Endpoint Override**:
   - Unset `AWS_ENDPOINT_URL` (or leave it blank) so `boto3` defaults to standard AWS regional endpoints.
2. **Provide Real AWS Credentials / IAM Roles**:
   - In production (e.g., ECS/EKS/EC2), attach an IAM role to the task/instance with permissions:
     - `sqs:SendMessage`, `sqs:GetQueueUrl` on the main SQS queue.
     - `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` on the queue (if worker runs in container).
     - `sns:Publish` on the SNS topic.
3. **Deploy Lambda Function to AWS**:
   - Package `backend/aws_lambda/notification_handler/handler.py` as an AWS Lambda function.
   - Configure an **SQS Trigger** (Event Source Mapping) pointing to `nextgig-notifications-queue` with `ReportBatchItemFailures` enabled.
   - Configure Lambda environment variables:
     - `SNS_TOPIC_ARN`: The ARN of the production SNS topic.
     - `LAMBDA_DIRECT_DELIVERY`: `"false"`.
   - Turn off or remove the local `lambda_poller` container service.
4. **Configure SNS Subscription**:
   - Set up an HTTPS subscription from the SNS topic to `https://<your-domain>/api/internal/notifications/deliver/<secret>/`.
   - Set `INTERNAL_SERVICE_SECRET` securely in the production environment.
5. **Enable Pipeline**:
   - Set `AWS_EVENTS_ENABLED=true` in Django production settings.

---

## 5. Limitations

1. **In-Memory Emulator State**: The Moto container runs entirely in memory. Restarting or recreating the container wipes all created SQS queues and SNS subscriptions; `python manage.py aws_setup_resources` must be re-run after a Moto restart.
2. **Delivery Retry Scope**: Pipeline retries (SQS redrive / DLQ) only cover transport and HTTP invocation failures. In-process WebSocket channel layer failures and downstream FCM delivery exceptions are caught and logged inside `deliver_notification_direct` (preserving existing error resilience), so they do not trigger SQS retries.
3. **Best-Effort Deduplication**: Cache-based deduplication (`notif_delivered:<id>`) is best-effort and relies on Redis cache key persistence within the TTL window (24 hours).

