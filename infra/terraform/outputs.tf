output "s3_bucket_name" {
  description = "Name of the media S3 bucket"
  value       = aws_s3_bucket.media.id
}

output "s3_bucket_arn" {
  description = "ARN of the media S3 bucket"
  value       = aws_s3_bucket.media.arn
}

output "s3_bucket_regional_domain_name" {
  description = "Regional domain name of the media S3 bucket"
  value       = aws_s3_bucket.media.bucket_regional_domain_name
}

output "sqs_main_queue_name" {
  description = "Name of the main notifications SQS queue"
  value       = aws_sqs_queue.notifications_main.name
}

output "sqs_main_queue_url" {
  description = "URL of the main notifications SQS queue"
  value       = aws_sqs_queue.notifications_main.url
}

output "sqs_main_queue_arn" {
  description = "ARN of the main notifications SQS queue"
  value       = aws_sqs_queue.notifications_main.arn
}

output "sqs_dlq_name" {
  description = "Name of the notifications Dead Letter Queue (DLQ)"
  value       = aws_sqs_queue.notifications_dlq.name
}

output "sqs_dlq_url" {
  description = "URL of the notifications Dead Letter Queue (DLQ)"
  value       = aws_sqs_queue.notifications_dlq.url
}

output "sqs_dlq_arn" {
  description = "ARN of the notifications Dead Letter Queue (DLQ)"
  value       = aws_sqs_queue.notifications_dlq.arn
}

output "sqs_delivery_queue_name" {
  description = "Name of the notifications delivery SQS queue polled by application"
  value       = aws_sqs_queue.notifications_delivery.name
}

output "sqs_delivery_queue_url" {
  description = "URL of the notifications delivery SQS queue"
  value       = aws_sqs_queue.notifications_delivery.url
}

output "sqs_delivery_queue_arn" {
  description = "ARN of the notifications delivery SQS queue"
  value       = aws_sqs_queue.notifications_delivery.arn
}

output "sns_topic_name" {
  description = "Name of the notifications SNS topic"
  value       = aws_sns_topic.notifications.name
}

output "sns_topic_arn" {
  description = "ARN of the notifications SNS topic"
  value       = aws_sns_topic.notifications.arn
}

output "lambda_function_name" {
  description = "Name of the notification handler Lambda function"
  value       = aws_lambda_function.notification_handler.function_name
}

output "lambda_function_arn" {
  description = "ARN of the notification handler Lambda function"
  value       = aws_lambda_function.notification_handler.arn
}

