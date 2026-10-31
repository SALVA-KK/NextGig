resource "aws_sns_topic" "notifications" {
  name = var.sns_topic_name
}

resource "aws_sns_topic_subscription" "notifications_delivery" {
  topic_arn            = aws_sns_topic.notifications.arn
  protocol             = "sqs"
  endpoint             = aws_sqs_queue.notifications_delivery.arn
  raw_message_delivery = true
}

