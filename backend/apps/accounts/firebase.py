import os
import logging
import firebase_admin
from firebase_admin import credentials, auth
from django.conf import settings

logger = logging.getLogger(__name__)


def get_firebase_app():
    """
    Initializes and returns the singleton Firebase Admin App instance.
    Reads service account credentials path from settings.FIREBASE_CREDENTIALS_PATH.
    Returns None if credentials file is missing or invalid.
    """
    if firebase_admin._apps:
        return firebase_admin.get_app()

    cred_path = getattr(
        settings,
        "FIREBASE_CREDENTIALS_PATH",
        os.path.join(settings.BASE_DIR, "config", "firebase-credentials.json"),
    )

    if os.path.exists(cred_path):
        try:
            cred = credentials.Certificate(cred_path)
            app = firebase_admin.initialize_app(cred)
            logger.info("Successfully initialized Firebase Admin SDK from %s", cred_path)
            return app
        except Exception as exc:
            logger.error("Failed to initialize Firebase Admin SDK: %s", exc)
            return None
    else:
        logger.warning("Firebase credentials file not found at %s", cred_path)
        return None


def verify_firebase_id_token(id_token):
    """
    Verifies a Firebase ID Token received from the client-side Firebase Auth SDK.
    Returns the verified phone_number string from decoded claims (e.g. '+919207362507').
    Returns None if token verification fails, is expired, or contains no phone_number claim.
    """
    if not id_token or not isinstance(id_token, str):
        return None

    app = get_firebase_app()
    if not app:
        logger.error("Firebase Admin app is not initialized. Cannot verify ID token.")
        return None

    try:
        decoded_token = auth.verify_id_token(id_token.strip(), app=app)
        phone_number = decoded_token.get("phone_number")
        if not phone_number:
            logger.warning("Firebase ID token verified successfully but contains no phone_number claim.")
            return None
        return phone_number
    except auth.InvalidIdTokenError:
        logger.warning("Invalid Firebase ID token received.")
        return None
    except auth.ExpiredIdTokenError:
        logger.warning("Expired Firebase ID token received.")
        return None
    except Exception as exc:
        logger.error("Firebase ID token verification exception: %s", exc)
        return None
