from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def generate_verification_url(user):
    """
    Generates a secure, time-sensitive email verification link for a user
    using Django's built-in default_token_generator and base64-encoded user PK.
    """
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
#    verification_url = f"{frontend_url}/verify-email?uid={uidb64}&token={token}"
    verification_url = (
    f"http://127.0.0.1:8000/api/accounts/verify-email/"
    f"?uid={uidb64}&token={token}"
)
    return verification_url


def send_verification_email(user):
    """
    Sends an email verification link to the user's registered email address.
    """
    verification_url = generate_verification_url(user)

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
