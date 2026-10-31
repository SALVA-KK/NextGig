resource "aws_sqs_queue" "notifications_dlq" {
  name                      = var.dlq_name
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue" "notifications_main" {
  name                       = var.main_queue_name
  visibility_timeout_seconds = 180

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.notifications_dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue" "notifications_delivery" {
  name                      = var.delivery_queue_name
  message_retention_seconds = 1209600
}

resource "aws_sqs_queue_policy" "notifications_delivery" {
  queue_url = aws_sqs_queue.notifications_delivery.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowSNSToSendMessages"
        Effect    = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.notifications_delivery.arn
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_sns_topic.notifications.arn
          }
        }
      }
    ]
  })
}

