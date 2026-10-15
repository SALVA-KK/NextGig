import json
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

_cached_creds = None
_cached_project_id = None
_mismatch_warned = False
_missing_warned = False

FCM_SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
FCM_V1_SEND_URL = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"


class FCMTransientError(Exception):
    """
    Exception raised for transient FCM errors (HTTP 429, 5xx, timeouts)
    to trigger Celery task retry with exponential backoff.
    """
    pass


def reset_fcm_cache():
    """Helper for tests to reset cached credentials and warning flags."""
    global _cached_creds, _cached_project_id, _mismatch_warned, _missing_warned
    _cached_creds = None
    _cached_project_id = None
    _mismatch_warned = False
    _missing_warned = False


def check_project_id_mismatch(project_id, candidate=None):
    """
    Checks if a configured project_id / sender matches the service account project_id.
    Logs a warning at most once if a mismatch is detected.
    """
    global _mismatch_warned
    if _mismatch_warned:
        return
    expected = os.getenv("FIREBASE_PROJECT_ID") or candidate
    if expected and project_id and expected != project_id:
        logger.warning(
            "Firebase project mismatch detected: expected '%s' vs service account '%s'.",
            expected,
            project_id,
        )
        _mismatch_warned = True


def get_fcm_credentials():
    """
    Lazily loads and caches service account credentials and project_id.
    Refreshes the OAuth2 access token only when expired.
    When FCM_ENABLED is False, avoids importing Google libraries and returns (None, None).
    Never logs the private key or token contents.
    """
    global _cached_creds, _cached_project_id, _missing_warned

    if not getattr(settings, "FCM_ENABLED", False):
        return None, None

    if _cached_creds is not None and _cached_project_id is not None:
        try:
            if not _cached_creds.valid:
                from google.auth.transport.requests import Request
                _cached_creds.refresh(Request())
            return _cached_creds, _cached_project_id
        except Exception as exc:
            logger.warning("FCM credentials refresh failed: %s; push disabled.", type(exc).__name__)
            return None, None

    cred_file = getattr(
        settings,
        "FIREBASE_CREDENTIALS_FILE",
        os.path.join(settings.BASE_DIR, "firebase-service-account.json"),
    )

    if not cred_file or not os.path.exists(cred_file):
        if not _missing_warned:
            logger.warning(
                "FCM credentials file not found at %s; FCM push disabled.",
                cred_file or "(empty)",
            )
            _missing_warned = True
        return None, None

    try:
        with open(cred_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            project_id = data.get("project_id")

        if not project_id:
            if not _missing_warned:
                logger.warning("FCM service account file is missing 'project_id'; push disabled.")
                _missing_warned = True
            return None, None

        check_project_id_mismatch(project_id)

        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        creds = service_account.Credentials.from_service_account_file(
            cred_file,
            scopes=FCM_SCOPES,
        )
        creds.refresh(Request())

        _cached_creds = creds
        _cached_project_id = project_id
        return _cached_creds, _cached_project_id

    except Exception as exc:
        if not _missing_warned:
            logger.warning(
                "Failed to initialize FCM credentials from %s: %s; push disabled.",
                cred_file,
                type(exc).__name__,
            )
            _missing_warned = True
        return None, None


def send_fcm_v1_message(device_token, title, body, data=None, link="/dashboard", timeout=10):
    """
    Sends a push notification to a single device token via FCM HTTP v1 API.

    Returns:
      {"status": "ok"}
      {"status": "deactivate", "error": error_code}
      {"status": "error", "error": error_code}
      {"status": "disabled", "error": ...}

    Raises:
      FCMTransientError on HTTP 429, 5xx, or network timeouts for Celery retry.
    """
    creds, project_id = get_fcm_credentials()
    if not creds or not project_id:
        return {"status": "disabled", "error": "FCM disabled or credentials unavailable"}

    import requests

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Content-Type": "application/json; UTF-8",
    }

    message_payload = {
        "message": {
            "token": device_token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": {str(k): str(v) for k, v in (data or {}).items()},
            "webpush": {
                "fcm_options": {
                    "link": link or "/dashboard",
                }
            },
        }
    }

    url = FCM_V1_SEND_URL.format(project_id=project_id)

    try:
        response = requests.post(
            url,
            json=message_payload,
            headers=headers,
            timeout=timeout,
        )
    except (requests.ConnectionError, requests.Timeout) as exc:
        raise FCMTransientError(f"Network error sending FCM push: {type(exc).__name__}") from exc

    if response.status_code == 200:
        return {"status": "ok"}

    if response.status_code in (429, 500, 502, 503, 504):
        raise FCMTransientError(f"FCM transient error status {response.status_code}")

    error_code = None
    try:
        err_json = response.json()
        error_info = err_json.get("error", {})
        error_code = error_info.get("status") or error_info.get("message")
        details = error_info.get("details", [])
        for d in details:
            if isinstance(d, dict) and d.get("@type") == "type.googleapis.com/google.firebase.fcm.v1.FcmError":
                error_code = d.get("errorCode", error_code)
                break
    except Exception:
        error_code = f"HTTP_{response.status_code}"

    # UNREGISTERED / NOT_FOUND / INVALID_ARGUMENT mean mark the token inactive
    deactivate_codes = (
        "UNREGISTERED",
        "NOT_FOUND",
        "INVALID_ARGUMENT",
        "REGISTRATION_TOKEN_NOT_REGISTERED",
    )
    if response.status_code == 404 or (
        error_code and any(dc in str(error_code).upper() for dc in deactivate_codes)
    ):
        return {"status": "deactivate", "error": error_code}

    return {"status": "error", "error": error_code}
