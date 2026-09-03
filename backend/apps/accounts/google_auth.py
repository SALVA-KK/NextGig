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
        "852841732506-f1bvs03hg92g9gl1k0f29nd9gjamoljk.apps.googleusercontent.com",
    )
    logger.info("[GOOGLE_OAUTH_AUDIENCE] Verifying Google ID token with audience: %s", client_id)

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
        logger.warning("[GOOGLE_OAUTH_VERIFY_FAILURE] ValueError: %s | audience=%s", exc, client_id)
        print(f"[GOOGLE_OAUTH_EXACT_ERROR] ValueError: {exc} | Audience used: {client_id}")
        return None
    except Exception as exc:
        logger.error("[GOOGLE_OAUTH_VERIFY_FAILURE] Exception (%s): %s | audience=%s", type(exc).__name__, exc, client_id)
        print(f"[GOOGLE_OAUTH_EXACT_ERROR] Exception ({type(exc).__name__}): {exc} | Audience used: {client_id}")
        return None
