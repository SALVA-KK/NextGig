data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../backend/aws_lambda/notification_handler"
  output_path = "${path.module}/builds/notification_handler.zip"
  excludes = [
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "test_*.py",
    "*_test.py",
    "tests.py",
    "tests"
  ]
}

resource "aws_lambda_function" "notification_handler" {
  function_name    = var.lambda_function_name
  role             = aws_iam_role.lambda_exec.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      SNS_TOPIC_ARN          = aws_sns_topic.notifications.arn
      LAMBDA_DIRECT_DELIVERY = "false"
    }
  }
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn        = aws_sqs_queue.notifications_main.arn
  function_name           = aws_lambda_function.notification_handler.arn
  batch_size              = 10
  function_response_types = ["ReportBatchItemFailures"]
}

