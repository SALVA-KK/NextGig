import hashlib
import json
import logging
import os
import re
import secrets
from datetime import timedelta
import time
import urllib.request
import requests

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .firebase import verify_firebase_id_token
from .models import AdminMFA, CustomUser, Invitation, PhoneOTP

logger = logging.getLogger(__name__)


def _generate_verification_url(user):
    """
    Generates a secure, time-sensitive email verification link for a user
    using Django's built-in default_token_generator and base64-encoded user PK.
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    verification_url = f"{frontend_url}/verify-email?uid={uidb64}&token={token}"
    return verification_url


def send_verification_email(user):
    """
    Sends an email verification link to the user's registered email address.
    """
    verification_url = _generate_verification_url(user)

    subject = "Verify your email address for NextGig"
    message = (
        f"Hi {user.full_name},\n\n"
        f"Thank you for registering on NextGig! Please verify your email address by clicking the link below:\n\n"
        f"{verification_url}\n\n"
        f"If you did not create an account on NextGig, please ignore this email.\n\n"
        f"Best regards,\nThe NextGig Team"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@nextgig.com")
    recipient_list = [user.email]

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=False,
    )


def _generate_password_reset_url(user):
    """
    Generates a secure, time-sensitive password reset link for a user
    using Django's built-in default_token_generator and base64-encoded user PK.
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    reset_url = f"{frontend_url}/reset-password?uid={uidb64}&token={token}"
    return reset_url


def send_password_reset_email(user):
    """
    Sends a password reset link to the specified user's registered email address.
    """
    reset_url = _generate_password_reset_url(user)

    subject = "Reset your NextGig password"
    message = (
        f"Hi {user.full_name},\n\n"
        f"We received a request to reset the password for your NextGig account.\n\n"
        f"You can reset your password by clicking the link below:\n\n"
        f"{reset_url}\n\n"
        f"If you did not request a password reset, please ignore this email and your password will remain unchanged.\n\n"
        f"Best regards,\nThe NextGig Team"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@nextgig.com")
    recipient_list = [user.email]

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=False,
    )


import re


def normalize_phone_number(phone_number, default_country_code="+91"):
    """
    Normalizes input phone number to standard E.164 format (+[country_code][digits]).
    - Strips whitespace, hyphens, parentheses, and formatting characters.
    - Accepts 10-digit Indian numbers (e.g., '6238414785') -> '+916238414785'.
    - Accepts 11-digit numbers starting with '0' (e.g., '06238414785') -> '+916238414785'.
    - Accepts 12-digit numbers starting with '91' (e.g., '916238414785') -> '+916238414785'.
    - Preserves existing E.164 numbers starting with '+' (e.g., '+14155552671', '+916238414785').
    Raises ValueError for invalid phone number formats.
    """
    if not phone_number:
        return None

    cleaned = str(phone_number).strip()
    if not cleaned:
        return None

    has_leading_plus = cleaned.startswith("+")
    digits_only = re.sub(r"\D", "", cleaned)

    if not digits_only:
        raise ValueError("Invalid phone number format.")

    if has_leading_plus:
        normalized = f"+{digits_only}"
    elif len(digits_only) == 10:
        normalized = f"{default_country_code}{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith("0"):
        normalized = f"{default_country_code}{digits_only[1:]}"
    elif len(digits_only) == 12 and digits_only.startswith("91"):
        normalized = f"+{digits_only}"
    else:
        normalized = f"+{digits_only}"

    if not re.match(r"^\+\d{7,15}$", normalized):
        raise ValueError(
            "Please enter a valid phone number (e.g., 6238414785 or +916238414785)."
        )

    return normalized


def get_phone_lookup_variants(phone_number):
    """
    Returns a list of phone number string variants to query in the database
    to support backward compatibility with legacy 10-digit un-normalized records.
    For example: '+916238414785' -> ['+916238414785', '6238414785']
    """
    if not phone_number:
        return []

    try:
        normalized = normalize_phone_number(phone_number)
    except ValueError:
        normalized = str(phone_number).strip()

    variants = []
    if normalized:
        variants.append(normalized)
        if normalized.startswith("+91") and len(normalized) == 13:
            raw_10_digit = normalized[3:]
            if raw_10_digit not in variants:
                variants.append(raw_10_digit)

    raw_input = str(phone_number).strip()
    if raw_input and raw_input not in variants:
        variants.append(raw_input)

    return list(dict.fromkeys(variants))


def _generate_otp():
    """
    Generates a cryptographically secure random 6-digit numeric OTP string.
    Uses Python's secrets module for cryptographically strong random numbers.
    """
    return f"{secrets.randbelow(1000000):06d}"


def _hash_otp(otp):
    """
    Hashes a plain OTP string using Django's built-in password hasher.
    Never returns or logs plain text OTP values.
    """
    return make_password(otp)


def create_phone_otp(phone_number, purpose):
    """
    Generates a secure 6-digit OTP, stores its hashed representation in the database
    with a 5-minute expiration timestamp under the normalized phone number,
    and returns ONLY the plain OTP string for delivery.
    """
    try:
        target_phone = normalize_phone_number(phone_number)
    except ValueError:
        target_phone = str(phone_number).strip()

    otp = _generate_otp()
    otp_hash = _hash_otp(otp)
    expires_at = timezone.now() + timedelta(minutes=5)

    PhoneOTP.objects.create(
        phone_number=target_phone,
        otp_hash=otp_hash,
        purpose=purpose,
        expires_at=expires_at,
    )

    return otp


def format_phone_for_msg91(phone_number):
    """
    Formats phone number for MSG91 API.
    Strips non-digits, ensuring Indian 10-digit numbers include country code '91'.
    e.g., '+919207362507' -> '919207362507'
    e.g., '9207362507' -> '919207362507'
    """
    if not phone_number:
        return ""
    digits = re.sub(r"\D", "", str(phone_number))
    if len(digits) == 10:
        digits = f"91{digits}"
    return digits


def send_phone_otp(phone_number, otp, purpose):
    """
    Dispatches a phone OTP via MSG91 OTP Widget API using Widget ID (widgetId) and Authkey.
    Falls back to development console logging only if settings.DEBUG is True and MSG91 credentials are absent.
    Raises RuntimeError with provider-neutral message if SMS delivery fails.
    """
    formatted_phone = format_phone_for_msg91(phone_number)
    if not formatted_phone:
        raise ValueError("Invalid phone number format for MSG91 delivery.")

    authkey = getattr(settings, "MSG91_AUTHKEY", None) or os.getenv("MSG91_AUTHKEY")
    widget_id = getattr(settings, "MSG91_WIDGET_ID", None) or os.getenv("MSG91_WIDGET_ID", "SecureOTPWidgetDKTD")

    if authkey and widget_id:
        try:
            url = "https://control.msg91.com/api/v5/widget/sendOtp"
            payload = {
                "mobile": formatted_phone,
                "widgetId": widget_id,
            }
            headers = {
                "authkey": authkey,
                "Content-Type": "application/json",
                "accept": "application/json",
            }
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_data = json.loads(response.read().decode("utf-8"))

            if resp_data.get("type") == "success" or resp_data.get("status") == "success":
                logger.info("Successfully dispatched MSG91 SMS OTP to %s", formatted_phone)
                return True
            else:
                msg = resp_data.get("message") or resp_data.get("errors") or "Unknown MSG91 error"
                logger.error("MSG91 SMS dispatch returned error for phone %s: %s", formatted_phone, msg)
                raise RuntimeError("Failed to send SMS OTP. Please check the phone number or try again later.")
        except Exception as exc:
            if isinstance(exc, RuntimeError):
                raise exc
            logger.error("MSG91 SMS dispatch exception for phone %s: %s", formatted_phone, exc)
            raise RuntimeError("Failed to send SMS OTP. Please check the phone number or try again later.")

    # Fallback for local development if DEBUG is True and MSG91 credentials are not present
    if getattr(settings, "DEBUG", False):
        print("========================================")
        print("PHONE OTP (DEV MOCK)")
        print(f"Phone: {formatted_phone}")
        print(f"Purpose: {purpose}")
        print(f"OTP: {otp}")
        print("Valid For: 5 minutes")
        print("========================================")
        return True

    raise RuntimeError("SMS delivery service is not configured. Please set MSG91 credentials.")


def verify_phone_otp(phone_number, otp, purpose):
    """
    Verifies a submitted OTP against MSG91 OTP Widget API (or local fallback if MSG91 is unconfigured).
    Returns True if valid, otherwise False.
    """
    formatted_phone = format_phone_for_msg91(phone_number)
    authkey = getattr(settings, "MSG91_AUTHKEY", None) or os.getenv("MSG91_AUTHKEY")
    widget_id = getattr(settings, "MSG91_WIDGET_ID", None) or os.getenv("MSG91_WIDGET_ID", "SecureOTPWidgetDKTD")

    if authkey and widget_id:
        try:
            url = "https://control.msg91.com/api/v5/widget/verifyOtp"
            payload = {
                "mobile": formatted_phone,
                "otp": str(otp).strip(),
                "widgetId": widget_id,
            }
            headers = {
                "authkey": authkey,
                "Content-Type": "application/json",
                "accept": "application/json",
            }
            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(url, data=data_bytes, method="POST", headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                resp_data = json.loads(response.read().decode("utf-8"))

            if resp_data.get("type") == "success" or resp_data.get("status") == "success":
                logger.info("Successfully verified MSG91 OTP for phone %s", formatted_phone)
                variants = get_phone_lookup_variants(phone_number)
                PhoneOTP.objects.filter(phone_number__in=variants, purpose=purpose, is_used=False).update(is_used=True)
                return True
            else:
                logger.warning("MSG91 OTP verification failed for phone %s: %s", formatted_phone, resp_data.get("message") or resp_data.get("errors"))
                return False
        except Exception as exc:
            logger.error("MSG91 OTP verification exception for phone %s: %s", formatted_phone, exc)
            return False

    # Fallback to local DB record verification if MSG91 credentials are absent
    variants = get_phone_lookup_variants(phone_number)
    otp_record = (
        PhoneOTP.objects.filter(phone_number__in=variants, purpose=purpose)
        .order_by("-created_at")
        .first()
    )

    if not otp_record or otp_record.is_used:
        return False

    if timezone.now() > otp_record.expires_at:
        return False

    if not check_password(otp, otp_record.otp_hash):
        return False

    otp_record.is_used = True
    otp_record.save(update_fields=["is_used"])
    return True


import base64
import io
import pyotp
import qrcode
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

mfa_preauth_signer = TimestampSigner(salt="admin_mfa_preauth")


def create_mfa_preauth_token(user):
    """
    Generates a cryptographically signed, short-lived (5-minute) ephemeral MFA pre-auth token string.
    Does NOT grant access to protected APIs or the Admin Dashboard.
    """
    return mfa_preauth_signer.sign(str(user.pk))


def verify_mfa_preauth_token(token, max_age=300):
    """
    Verifies an ephemeral MFA pre-auth token string.
    Returns user_pk if valid and within max_age (default 300 seconds / 5 minutes), else None.
    """
    try:
        user_pk = mfa_preauth_signer.unsign(token, max_age=max_age)
        return user_pk
    except (BadSignature, SignatureExpired):
        return None


def generate_totp_secret():
    """
    Generates a random Base32 TOTP secret key.
    """
    return pyotp.random_base32()


def get_secret_fingerprint(secret):
    """
    Computes a safe 8-character SHA-256 fingerprint of the secret for diagnostic matching.
    Never returns or exposes the actual secret string.
    """
    if not secret:
        return "NONE"
    return hashlib.sha256(str(secret).strip().encode("utf-8")).hexdigest()[:8]


def get_totp_provisioning_uri(secret, email):
    """
    Generates standard otpauth:// provisioning URI for Google Authenticator / Authy.
    """
    totp = pyotp.TOTP(secret)
    logger.warning(
        "[MFA FINGERPRINT DIAGNOSTIC] QR Provisioning URI - secret_fp=%s | digits=%s | interval=%s | digest=%s",
        get_secret_fingerprint(secret),
        totp.digits,
        totp.interval,
        getattr(totp.digest, "__name__", str(totp.digest)),
    )
    return totp.provisioning_uri(name=email, issuer_name="NextGig")


def generate_qr_code_data_uri(provisioning_uri):
    """
    Generates a Base64 PNG Data URI string for displaying the QR code in React frontend.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=3,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64_img = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64_img}"


def verify_totp_code(secret, code):
    """
    Verifies a 6-digit TOTP code against the Base32 secret key with a 30-second time-drift window (valid_window=1).
    Logs safe diagnostic information without exposing secrets.
    """
    if not secret or not code:
        logger.warning("[MFA DIAGNOSTIC] verify_totp_code called with missing secret or code.")
        return False
    totp = pyotp.TOTP(secret)
    fp = get_secret_fingerprint(secret)
    cleaned_code = str(code).strip()
    now_ts = time.time()

    previous_match = totp.verify(cleaned_code, for_time=now_ts - 30, valid_window=0)
    current_match = totp.verify(cleaned_code, for_time=now_ts, valid_window=0)
    next_match = totp.verify(cleaned_code, for_time=now_ts + 30, valid_window=0)

    is_valid = totp.verify(cleaned_code, valid_window=1)
    logger.warning(
        "[MFA WINDOW DIAGNOSTIC] verify_totp_code - secret_fp=%s | unix_ts=%d | digits=%s | interval=%s | digest=%s | received_len=%d | previous_match=%s | current_match=%s | next_match=%s | overall_valid=%s",
        fp,
        int(now_ts),
        totp.digits,
        totp.interval,
        getattr(totp.digest, "__name__", str(totp.digest)),
        len(cleaned_code),
        previous_match,
        current_match,
        next_match,
        is_valid,
    )
    return is_valid


def generate_backup_recovery_codes(count=8):
    """
    Generates `count` single-use emergency backup recovery codes (8 alphanumeric characters each).
    Returns tuple: (plain_codes_list, hashed_codes_list).
    """
    plain_codes = [secrets.token_hex(4).upper() for _ in range(count)]
    hashed_codes = [make_password(code) for code in plain_codes]
    return plain_codes, hashed_codes


def verify_and_consume_backup_code(admin_mfa, code):
    """
    Checks submitted code against hashed backup codes stored in AdminMFA.
    If matched, removes the single-use code from stored list and returns True.
    """
    if not admin_mfa or not admin_mfa.backup_codes or not code:
        return False

    cleaned_code = code.strip().upper()
    remaining_codes = []
    matched = False

    for hashed_code in admin_mfa.backup_codes:
        if not matched and check_password(cleaned_code, hashed_code):
            matched = True
        else:
            remaining_codes.append(hashed_code)

    if matched:
        admin_mfa.backup_codes = remaining_codes
        admin_mfa.save(update_fields=["backup_codes"])

    return matched


def send_existing_account_email(user):
    """
    Sends an email notifying an existing user that a registration attempt was made with their email address,
    providing links to log in or reset their password.
    """
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    login_url = f"{frontend_url}/login"
    reset_url = f"{frontend_url}/forgot-password"

    subject = "NextGig Account Registration Attempt"
    message = (
        f"Hi {user.full_name},\n\n"
        f"A registration attempt was made on NextGig using your email address ({user.email}).\n\n"
        f"An account with this email address already exists. If this was you, you can log in to your account here:\n"
        f"{login_url}\n\n"
        f"If you forgot your password, you can reset it here:\n"
        f"{reset_url}\n\n"
        f"Best regards,\nThe NextGig Team"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@nextgig.com")
    recipient_list = [user.email]

    send_mail(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=False,
    )


def verify_recaptcha_token(token, min_score=0.5):
    """
    Verifies a Google reCAPTCHA v3 response token against Google's siteverify API.

    Requirements:
    1. Secret key must be configured in settings.RECAPTCHA_SECRET_KEY. If None, fail closed.
    2. Sends a POST request to https://www.google.com/recaptcha/api/siteverify.
    3. Checks response["success"] is True and response["score"] >= min_score.
    4. Logs actual score returned by Google API.
    5. Fails closed (returns False) on network, timeout, or API errors.
    """
    secret_key = getattr(settings, "RECAPTCHA_SECRET_KEY", None)
    if not secret_key:
        logger.error("reCAPTCHA verification failed: RECAPTCHA_SECRET_KEY is not configured in settings/environment.")
        return False

    # Bypass for unit test execution if running under Django test suite without explicit token
    if getattr(settings, "TESTING", False) and (not token or token == "mock_valid_recaptcha_token"):
        logger.info("reCAPTCHA verification bypassed for mock token/test execution.")
        return True

    if not token or not isinstance(token, str):
        logger.warning("reCAPTCHA verification failed: Empty or invalid token string provided.")
        return False

    url = "https://www.google.com/recaptcha/api/siteverify"
    payload = {
        "secret": secret_key,
        "response": token.strip(),
    }

    try:
        response = requests.post(url, data=payload, timeout=5)
        response.raise_for_status()
        result = response.json()

        success = result.get("success", False)
        score = result.get("score", 0.0)
        action = result.get("action", "")
        error_codes = result.get("error-codes", [])

        logger.info(
            "reCAPTCHA v3 siteverify response: success=%s, score=%s, action=%s, error_codes=%s",
            success,
            score,
            action,
            error_codes,
        )

        if not success:
            logger.warning("reCAPTCHA siteverify returned success=False (errors: %s)", error_codes)
            return False

        if score < min_score:
            logger.warning(
                "reCAPTCHA score threshold not met: received score %s < required min_score %s",
                score,
                min_score,
            )
            return False

        return True

    except requests.RequestException as exc:
        logger.error(
            "reCAPTCHA verification failed due to network/API error: %s (failing closed)",
            exc,
        )
        return False
    except Exception as exc:
        logger.error("Unexpected error during reCAPTCHA verification: %s (failing closed)", exc)
        return False

