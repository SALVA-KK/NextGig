import logging
from google.oauth2 import id_token
from google.auth.transport import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def verify_google_id_token(token):
    """
    Verifies a Google OAuth 2.0 ID Token received from client-side Google OAuth SDK.
    Validates token signature, expiration, and target audience against settings.GOOGLE_CLIENT_ID.
    Returns a dict containing verified user claims ('email', 'name', 'google_id') on success.
    Returns None on any verification failure (expired, invalid signature, wrong audience, malformed).
    """
    if not token or not isinstance(token, str):
        return None

    client_id = getattr(
        settings,
        "GOOGLE_CLIENT_ID",
        "852841732506-4ff826cb1d8qe39m4l6b4bmgfe0l6pal.apps.googleusercontent.com",
    )

    try:
        id_info = id_token.verify_oauth2_token(
            token.strip(),
            requests.Request(),
            audience=client_id,
        )

        email = id_info.get("email")
        if not email:
            logger.warning("Google ID token verified but missing email claim.")
            return None

        if id_info.get("email_verified") is False:
            logger.warning("Google ID token verified but email_verified claim is False.")
            return None

        return {
            "email": email.strip().lower(),
            "name": id_info.get("name") or email.split("@")[0],
            "google_id": id_info.get("sub"),
        }
    except ValueError as exc:
        logger.warning("Google ID token verification failed: %s", exc)
        return None
    except Exception as exc:
        logger.error("Unexpected exception during Google ID token verification: %s", exc)
        return None
