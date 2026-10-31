# NextGig AWS Terraform Infrastructure

This directory contains the Terraform configuration for the NextGig production AWS infrastructure in the `ap-southeast-2` (Sydney) region.

All provisioned resources are designed to operate strictly within the **AWS Free Tier** limits.

---

## Architecture Overview

```text
Django Application (Post-Save Signal)
       │
       ▼
 [SQS Main Queue: nextgig-notifications-queue] ──(redrive maxReceiveCount: 3)──> [SQS DLQ: nextgig-notifications-dlq]
       │
       ▼ (Event Source Mapping with ReportBatchItemFailures)
 [AWS Lambda: nextgig-notification-handler]
       │
       ▼ (Publish)
 [SNS Topic: nextgig-notifications-topic]
       │
       ▼ (SQS Subscription with RawMessageDelivery)
 [SQS Delivery Queue: nextgig-notifications-delivery-queue]
       │
       ▼ (Polled by Application)
 Django Background Worker / Channels / Push Notification
```

### Managed Resources:
1. **S3 Media Storage (`s3.tf`, `imports.tf`)**:
   - Manages the existing S3 bucket `nextgig-media-salva-2610`.
   - Imported declaratively using Terraform `import {}` blocks in `imports.tf`.
   - Bucket public access block: allows public policy (`BlockPublicPolicy = false`, `RestrictPublicBuckets = false`).
   - Bucket policy: allows public `s3:GetObject` on `profile_pics/*`; keeps `resumes/*` private.
2. **SQS Messaging Pipeline (`sqs.tf`)**:
   - `nextgig-notifications-dlq`: dead-letter queue with 14-day retention (`1209600` seconds).
   - `nextgig-notifications-queue`: main notifications queue with `visibility_timeout_seconds = 180` and redrive targeting the DLQ (`maxReceiveCount = 3`).
   - `nextgig-notifications-delivery-queue`: second queue subscribed to the SNS topic, polled by the application worker.
   - Queue policy on the delivery queue allowing `sqs:SendMessage` from `sns.amazonaws.com` restricted to the SNS topic ARN via `aws:SourceArn` condition.
3. **SNS Fan-out (`sns.tf`)**:
   - `nextgig-notifications-topic`: SNS topic fanning out messages to the delivery queue with `raw_message_delivery = true`.
4. **Lambda Event Processing (`lambda.tf`, `iam.tf`)**:
   - Zips `backend/aws_lambda/notification_handler/` using HashiCorp `archive` provider (excluding `__pycache__`, `*.pyc`, test files).
   - `nextgig-notification-handler`: Python 3.12, 128 MB memory, 30s timeout.
   - SQS Event Source Mapping attached to the main queue with `ReportBatchItemFailures`.
   - IAM role `nextgig-notification-lambda-role` with `AWSLambdaBasicExecutionRole` and least-privilege permissions on the main queue and SNS topic.

---

## Prerequisites

1. **Terraform CLI**: version `>= 1.16` (or compatible Terraform 1.6+ supporting `import {}` blocks).
2. **AWS Credentials**: export your AWS credentials and region in your shell:
   ```bash
   export AWS_ACCESS_KEY_ID="your-access-key-id"
   export AWS_SECRET_ACCESS_KEY="your-secret-access-key"
   export AWS_REGION="ap-southeast-2"
   ```
   *(No credentials are ever committed or hardcoded in Terraform code).*

---

## Deployment Steps

Run all commands from the `infra/terraform/` directory:

```bash
cd infra/terraform
```

### 1. Initialize Working Directory
Installs the pinned AWS (`>= 5.0, < 7.0`) and Archive (`~> 2.4`) providers:
```bash
terraform init
```

### 2. Validate Syntax and Configuration
Verifies that all HCL syntax and internal references are valid:
```bash
terraform validate
```

### 3. Generate Execution Plan
Terraform will plan the creation of the SQS queues, SNS topic, IAM role, and Lambda function, while planning the **import** of the existing S3 bucket (`nextgig-media-salva-2610`), its public access block, and its bucket policy:
```bash
terraform plan
```

### 4. Apply Infrastructure Changes
Applies the configuration:
```bash
terraform apply
```

---

## Post-Deployment Application Configuration

Update the environment variables in your NextGig root `.env` or production environment using the output values:

```env
AWS_REGION=ap-southeast-2
AWS_SQS_QUEUE_NAME=nextgig-notifications-queue
AWS_SQS_DLQ_NAME=nextgig-notifications-dlq
AWS_SNS_TOPIC_NAME=nextgig-notifications-topic
AWS_SNS_TOPIC_ARN=<output from terraform: sns_topic_arn>
S3_STORAGE_ENABLED=true
S3_BUCKET_NAME=nextgig-media-salva-2610
S3_REGION=ap-southeast-2
S3_PUBLIC_BASE=nextgig-media-salva-2610.s3.ap-southeast-2.amazonaws.com
S3_URL_PROTOCOL=https:
S3_ENDPOINT_URL=
AWS_ENDPOINT_URL=
```

---

## Destroying Infrastructure

To tear down all resources provisioned by Terraform:

```bash
terraform destroy
```

> **Note on Existing S3 Bucket:**
> If you wish to retain the S3 bucket and its uploaded media files upon destruction, remove the `aws_s3_bucket.media` resource from the Terraform state prior to running destroy:
> ```bash
> terraform state rm aws_s3_bucket.media
> terraform state rm aws_s3_bucket_public_access_block.media
> terraform state rm aws_s3_bucket_policy.media
> ```

