import logging
import time
from typing import Any, Dict, List, Optional, Union

import httpx
from django.conf import settings
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


class AIConfigError(Exception):
    """Raised when Google Gemini API key or required settings are missing."""
    pass


class AIBusyError(Exception):
    """Raised when Gemini API or network transports are busy/unavailable after fallbacks."""
    pass


class AIFailureError(Exception):
    """Raised when Gemini API returns non-retryable errors or empty content."""
    pass


def _is_busy_exception(exc: Exception) -> bool:
    status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    err_msg = str(exc).lower()
    exc_name = type(exc).__name__.lower()

    if status_code in (503, 429, 408):
        return True
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError, TimeoutError, ConnectionError)):
        return True
    if "timeout" in exc_name or "connect" in exc_name:
        return True
    if "timeout" in err_msg or "timed out" in err_msg or "service unavailable" in err_msg or "too many requests" in err_msg:
        return True
    if status_code is None and not err_msg:
        return True
    return False


def generate_text(
    contents: Union[str, List[Dict[str, str]]],
    *,
    system_instruction: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Generates text using Google Gemini API with built-in model fallback and hardened error handling.

    :param contents: plain string or list of dicts like [{"role": "user"|"model", "text": str}]
    :param system_instruction: optional system prompt instruction
    :param max_output_tokens: optional token limit for response
    :param temperature: optional temperature value
    :return: generated response text string
    :raises AIConfigError: if GOOGLE_API_KEY is missing/empty
    :raises AIBusyError: if service/network is busy after primary and fallback attempts
    :raises AIFailureError: for non-retryable errors or empty response output
    """
    api_key = getattr(settings, "GOOGLE_API_KEY", "")
    if not api_key or not str(api_key).strip():
        logger.error("GOOGLE_API_KEY is missing or empty in settings.")
        raise AIConfigError("Gemini API key is not configured.")

    primary_model = settings.GEMINI_MODEL
    fallback_model = settings.GEMINI_FALLBACK_MODEL
    models_to_try = [primary_model, fallback_model]

    # Format contents for SDK if list of role dicts is provided
    formatted_contents: Any = contents
    if isinstance(contents, list):
        formatted_contents = []
        for item in contents:
            if isinstance(item, dict) and "role" in item and "text" in item:
                role = item["role"]
                text_val = item["text"]
                formatted_contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=text_val)],
                    )
                )

    config_kwargs: Dict[str, Any] = {}
    if temperature is not None:
        config_kwargs["temperature"] = temperature
    if max_output_tokens is not None:
        config_kwargs["max_output_tokens"] = max_output_tokens
    if system_instruction is not None:
        config_kwargs["system_instruction"] = system_instruction

    http_opts = types.HttpOptions(
        timeout=20000,  # 20 seconds timeout per attempt in milliseconds
        retry_options=types.HttpRetryOptions(attempts=1),  # Disable SDK internal retries
    )
    config_kwargs["http_options"] = http_opts

    client = genai.Client(api_key=api_key)
    raw_response_text = None
    last_error_is_busy = False

    for idx, model_name in enumerate(models_to_try):
        if idx > 0:
            time.sleep(2)

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=formatted_contents,
                config=types.GenerateContentConfig(**config_kwargs),
            )
            raw_response_text = response.text if response and hasattr(response, "text") else ""
            last_error_is_busy = False
            break
        except Exception as exc:
            status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            logger.error(
                "Gemini API failure on model %s (status=%s): %s %s",
                model_name,
                status_code,
                type(exc).__name__,
                exc,
            )

            is_busy = _is_busy_exception(exc)
            last_error_is_busy = is_busy

            if not is_busy or idx == len(models_to_try) - 1:
                break

    if raw_response_text is None:
        if last_error_is_busy:
            raise AIBusyError("The AI service is busy right now.")
        raise AIFailureError("Could not generate text from Gemini API.")

    if not raw_response_text or not raw_response_text.strip():
        raise AIFailureError("Empty response text returned from Gemini API.")

    return raw_response_text
