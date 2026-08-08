from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model for NextGig platform using email as the primary login field.
    """

    class Role(models.TextChoices):
        STUDENT = "student", _("Student")
        PROVIDER = "provider", _("Provider")
        ADMIN = "admin", _("Admin")

    # Primary authentication identifier instead of a username. Must be unique across all accounts.
    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
        error_messages={
            "unique": _("A user with that email already exists."),
        },
    )

    # Full Name: Single field for user's full name to support diverse global naming structures.
    full_name = models.CharField(_("full name"), max_length=255)

    # Phone Number: Optional contact field for SMS notifications, phone verification, or OTP login.
    # Set to unique=True (with blank=True and null=True) to prevent duplicate phone numbers.
    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        unique=True,
        blank=True,
        null=True,
        error_messages={
            "unique": _("A user with that phone number already exists."),
        },
    )

    # Role: Role-Based Access Control (RBAC) choices (student, provider, admin).
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
    )

    # Status Flags
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user account is active. Unselect this instead of deleting accounts."
        ),
    )

    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into the Django admin site."),
    )

    is_verified = models.BooleanField(
        _("verified status"),
        default=False,
        help_text=_("Designates whether the user has verified their email/identity."),
    )

    # Email Verification Timestamp
    email_verified_at = models.DateTimeField(
        _("email verified at"),
        null=True,
        blank=True,
        help_text=_("Timestamp indicating when the user's email was verified."),
    )

    # Timestamps
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} ({self.role})"


class PhoneOTP(models.Model):
    """
    Model for storing hashed temporary phone OTPs for authentication, registration,
    password reset, and MFA workflows.
    """

    class OTPPurpose(models.TextChoices):
        LOGIN = "login", _("Login")
        REGISTRATION = "registration", _("Registration")
        PASSWORD_RESET = "password_reset", _("Password Reset")
        MFA = "mfa", _("Multi-Factor Authentication")

    phone_number = models.CharField(
        _("phone number"),
        max_length=20,
        db_index=True,
        help_text=_("Target phone number for OTP verification."),
    )

    otp_hash = models.CharField(
        _("OTP hash"),
        max_length=128,
        help_text=_("Hashed OTP value for secure verification."),
    )

    purpose = models.CharField(
        _("purpose"),
        max_length=20,
        choices=OTPPurpose.choices,
        help_text=_("Intended workflow purpose for this OTP."),
    )

    expires_at = models.DateTimeField(
        _("expires at"),
        help_text=_("Expiration timestamp for the OTP."),
    )

    is_used = models.BooleanField(
        _("is used"),
        default=False,
        help_text=_("Flag indicating whether the OTP has already been verified/used."),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        db_table = "phone_otps"
        verbose_name = _("phone OTP")
        verbose_name_plural = _("phone OTPs")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.phone_number} ({self.purpose})"
