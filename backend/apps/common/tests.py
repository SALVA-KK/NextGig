from unittest.mock import MagicMock, patch
from django.test import TestCase, override_settings
import httpx

from apps.common.gemini_client import (
    AIConfigError,
    AIBusyError,
    AIFailureError,
    generate_text,
)


class GeminiClientTestCase(TestCase):
    """
    Unit tests for the reusable Gemini client module (apps/common/gemini_client.py).
    """

    def test_missing_api_key_raises_ai_config_error(self):
        with override_settings(GOOGLE_API_KEY=""):
            with self.assertRaises(AIConfigError):
                generate_text("Hello")

    @patch("apps.common.gemini_client.time.sleep")
    @patch("apps.common.gemini_client.genai.Client")
    def test_primary_503_fallback_succeeds_assert_model_args(self, mock_client_class, mock_sleep):
        from google.genai.errors import ServerError

        error_503 = ServerError(503, {"error": {"message": "Service Unavailable"}})
        success_resp = MagicMock(text="Generated text output")

        mock_inst = MagicMock()
        mock_inst.models.generate_content.side_effect = [error_503, success_resp]
        mock_client_class.return_value = mock_inst

        with override_settings(
            GOOGLE_API_KEY="test_key_123",
            GEMINI_MODEL="primary-model",
            GEMINI_FALLBACK_MODEL="fallback-model",
        ):
            result = generate_text("Analyze this text")

        self.assertEqual(result, "Generated text output")
        self.assertEqual(mock_inst.models.generate_content.call_count, 2)

        first_call_kwargs = mock_inst.models.generate_content.call_args_list[0].kwargs
        second_call_kwargs = mock_inst.models.generate_content.call_args_list[1].kwargs

        self.assertEqual(first_call_kwargs["model"], "primary-model")
        self.assertEqual(second_call_kwargs["model"], "fallback-model")
        mock_sleep.assert_called_once_with(2)

    @patch("apps.common.gemini_client.time.sleep")
    @patch("apps.common.gemini_client.genai.Client")
    def test_both_models_503_raises_ai_busy_error(self, mock_client_class, mock_sleep):
        from google.genai.errors import ServerError

        error_503 = ServerError(503, {"error": {"message": "Service Unavailable"}})
        mock_inst = MagicMock()
        mock_inst.models.generate_content.side_effect = [error_503, error_503]
        mock_client_class.return_value = mock_inst

        with override_settings(GOOGLE_API_KEY="test_key_123"):
            with self.assertRaises(AIBusyError):
                generate_text("Test prompt")

        self.assertEqual(mock_inst.models.generate_content.call_count, 2)

    @patch("apps.common.gemini_client.genai.Client")
    def test_gemini_404_not_retried_raises_ai_failure_error(self, mock_client_class):
        from google.genai.errors import ClientError

        error_404 = ClientError(404, {"error": {"message": "Model not found"}})
        mock_inst = MagicMock()
        mock_inst.models.generate_content.side_effect = error_404
        mock_client_class.return_value = mock_inst

        with override_settings(GOOGLE_API_KEY="test_key_123"):
            with self.assertRaises(AIFailureError):
                generate_text("Test prompt")

        self.assertEqual(mock_inst.models.generate_content.call_count, 1)

    @patch("apps.common.gemini_client.time.sleep")
    @patch("apps.common.gemini_client.genai.Client")
    def test_httpx_read_timeout_triggers_fallback(self, mock_client_class, mock_sleep):
        timeout_error = httpx.ReadTimeout("")
        success_resp = MagicMock(text="Timeout fallback output")

        mock_inst = MagicMock()
        mock_inst.models.generate_content.side_effect = [timeout_error, success_resp]
        mock_client_class.return_value = mock_inst

        with override_settings(
            GOOGLE_API_KEY="test_key_123",
            GEMINI_MODEL="primary-model",
            GEMINI_FALLBACK_MODEL="fallback-model",
        ):
            result = generate_text("Timeout prompt")

        self.assertEqual(result, "Timeout fallback output")
        self.assertEqual(mock_inst.models.generate_content.call_count, 2)
        mock_sleep.assert_called_once_with(2)

    @patch("apps.common.gemini_client.genai.Client")
    def test_contents_list_with_roles_passed_to_sdk(self, mock_client_class):
        success_resp = MagicMock(text="Role-based response")
        mock_inst = MagicMock()
        mock_inst.models.generate_content.return_value = success_resp
        mock_client_class.return_value = mock_inst

        contents = [
            {"role": "user", "text": "Hello"},
            {"role": "model", "text": "Hi there"},
            {"role": "user", "text": "Summarize this"},
        ]

        with override_settings(GOOGLE_API_KEY="test_key_123"):
            result = generate_text(contents)

        self.assertEqual(result, "Role-based response")
        call_contents = mock_inst.models.generate_content.call_args.kwargs["contents"]
        self.assertEqual(len(call_contents), 3)
        self.assertEqual(call_contents[0].role, "user")
        self.assertEqual(call_contents[1].role, "model")
        self.assertEqual(call_contents[2].role, "user")
