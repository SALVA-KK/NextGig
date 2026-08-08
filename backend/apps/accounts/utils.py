import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import PhoneOTP


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
    with a 5-minute expiration timestamp, and returns ONLY the plain OTP string for delivery.
    """
    otp = _generate_otp()
    otp_hash = _hash_otp(otp)
    expires_at = timezone.now() + timedelta(minutes=5)

    PhoneOTP.objects.create(
        phone_number=phone_number,
        otp_hash=otp_hash,
        purpose=purpose,
        expires_at=expires_at,
    )

    return otp


def send_phone_otp(phone_number, otp, purpose):
    """
    Development-only SMS delivery mock function.
    Prints formatted OTP delivery details to the Django server output console.

    In a production environment, this function can be swapped with a real SMS gateway driver
    (e.g., Twilio, MSG91, Fast2SMS) without requiring any changes to calling views or business logic.
    """
    print("========================================")
    print("PHONE OTP")
    print("")
    print("Phone:")
    print(f"{phone_number}")
    print("")
    print("Purpose:")
    print(f"{purpose}")
    print("")
    print("OTP:")
    print(f"{otp}")
    print("")
    print("Valid For:")
    print("5 minutes")
    print("")
    print("========================================")


def verify_phone_otp(phone_number, otp, purpose):
    """
    Verifies a submitted plain-text OTP against the latest active PhoneOTP record for a given phone number and purpose.
    Returns True if valid, unexpired, unused, and matched; otherwise returns False.
    Marks valid OTPs as used immediately to prevent replay attacks.
    """
    otp_record = (
        PhoneOTP.objects.filter(phone_number=phone_number, purpose=purpose)
        .order_by("-created_at")
        .first()
    )

    if not otp_record:
        return False

    if otp_record.is_used:
        return False

    if timezone.now() > otp_record.expires_at:
        return False

    if not check_password(otp, otp_record.otp_hash):
        return False

    otp_record.is_used = True
    otp_record.save(update_fields=["is_used"])
    return True
