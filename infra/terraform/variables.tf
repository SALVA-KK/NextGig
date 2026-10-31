variable "aws_region" {
  type        = string
  description = "AWS region for NextGig resources"
  default     = "ap-southeast-2"
}

variable "s3_bucket_name" {
  type        = string
  description = "Name of the existing NextGig media S3 bucket to import"
  default     = "nextgig-media-salva-2610"
}

variable "main_queue_name" {
  type        = string
  description = "Name of the main notifications SQS queue"
  default     = "nextgig-notifications-queue"
}

variable "dlq_name" {
  type        = string
  description = "Name of the dead-letter notifications SQS queue"
  default     = "nextgig-notifications-dlq"
}

variable "delivery_queue_name" {
  type        = string
  description = "Name of the delivery notifications SQS queue polled by application"
  default     = "nextgig-notifications-delivery-queue"
}

variable "sns_topic_name" {
  type        = string
  description = "Name of the notifications SNS topic"
  default     = "nextgig-notifications-topic"
}

variable "lambda_function_name" {
  type        = string
  description = "Name of the notification handler Lambda function"
  default     = "nextgig-notification-handler"
}

