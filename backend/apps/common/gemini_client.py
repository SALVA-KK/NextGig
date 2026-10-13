import logging
import math
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


def _l2_normalize(vec: List[float]) -> List[float]:
    """
    Normalizes a vector to unit L2 length.
    If the vector has zero norm or NaN, returns a zero vector safely.
    """
    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0 or math.isnan(norm):
        return [0.0] * len(vec)
    return [x / norm for x in vec]


EMBEDDING_BATCH_SIZE = 50
DEFAULT_EMBEDDING_TIMEOUT_SECONDS = 20.0


def embed_texts(
    texts: List[str],
    *,
    task_type: str,
    timeout: Optional[Union[int, float]] = None,
) -> List[List[float]]:
    """
    Generates vector embeddings for a list of texts using Google Gemini API.

    :param texts: List of text strings to embed.
    :param task_type: "RETRIEVAL_DOCUMENT" for stored text, "RETRIEVAL_QUERY" for queries.
    :param timeout: Optional timeout in seconds per attempt (defaults to 20 seconds).
    :return: List of L2-normalized float vectors.
    :raises AIConfigError: If GOOGLE_API_KEY, GEMINI_EMBEDDING_MODEL, or GEMINI_EMBEDDING_DIM is missing/invalid.
    :raises AIBusyError: If the Gemini service is busy (503, 429, timeout).
    :raises AIFailureError: If the API returns errors, empty, or incomplete embeddings.
    """
    if not isinstance(texts, list):
        raise ValueError("texts must be a list of strings.")
    if not texts:
        return []

    if task_type not in ("RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"):
        raise ValueError(
            f"Invalid task_type: '{task_type}'. Must be 'RETRIEVAL_DOCUMENT' or 'RETRIEVAL_QUERY'."
        )

    if timeout is not None:
        try:
            timeout_sec = float(timeout)
            if timeout_sec <= 0:
                raise ValueError
        except (ValueError, TypeError):
            raise ValueError("timeout must be a positive number.")
    else:
        timeout_sec = DEFAULT_EMBEDDING_TIMEOUT_SECONDS

    api_key = getattr(settings, "GOOGLE_API_KEY", "")
    if not api_key or not str(api_key).strip():
        logger.error("GOOGLE_API_KEY is missing or empty in settings.")
        raise AIConfigError("Gemini API key is not configured.")

    embedding_model = getattr(settings, "GEMINI_EMBEDDING_MODEL", None)
    if not embedding_model or not str(embedding_model).strip():
        logger.error("GEMINI_EMBEDDING_MODEL is missing or empty in settings.")
        raise AIConfigError("Gemini embedding model is not configured.")

    embedding_dim = getattr(settings, "GEMINI_EMBEDDING_DIM", None)
    if embedding_dim is None:
        logger.error("GEMINI_EMBEDDING_DIM is missing or empty in settings.")
        raise AIConfigError("Gemini embedding dimension is not configured.")
    try:
        dim = int(embedding_dim)
        if dim <= 0:
            raise ValueError
    except (ValueError, TypeError):
        logger.error("GEMINI_EMBEDDING_DIM must be a positive integer.")
        raise AIConfigError("Gemini embedding dimension must be a positive integer.")

    client = genai.Client(api_key=api_key)
    http_opts = types.HttpOptions(
        timeout=int(timeout_sec * 1000),
        retry_options=types.HttpRetryOptions(attempts=1),
    )


    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), EMBEDDING_BATCH_SIZE):
        batch = texts[i : i + EMBEDDING_BATCH_SIZE]
        try:
            response = client.models.embed_content(
                model=embedding_model,
                contents=batch,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=dim,
                    http_options=http_opts,
                ),
            )
        except Exception as exc:
            status_code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
            logger.error(
                "Gemini API failure during embed_content (status=%s): %s",
                status_code,
                type(exc).__name__,
            )
            if _is_busy_exception(exc):
                raise AIBusyError("The AI service is busy right now.") from exc
            raise AIFailureError("Could not generate embeddings from Gemini API.") from exc

        if not response or not getattr(response, "embeddings", None) or len(response.embeddings) != len(batch):
            logger.error("Gemini API returned empty or incomplete embeddings response.")
            raise AIFailureError("Embedding API returned incomplete or empty results.")

        for emb in response.embeddings:
            values = getattr(emb, "values", None)
            if values is None:
                logger.error("Gemini embedding object is missing 'values'.")
                raise AIFailureError("Missing embedding values in API response.")
            all_embeddings.append(_l2_normalize(list(values)))

    return all_embeddings
