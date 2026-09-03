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


class AdminMFA(models.Model):
    """
    Dedicated model for storing Admin TOTP Multi-Factor Authentication settings.
    Keeps MFA secrets strictly isolated from student and provider accounts.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="mfa_settings",
        help_text=_("Admin user associated with these MFA settings."),
    )

    totp_secret = models.CharField(
        _("TOTP secret"),
        max_length=64,
        help_text=_("Base32 TOTP secret key for authenticator app verification."),
    )

    is_enabled = models.BooleanField(
        _("is enabled"),
        default=False,
        help_text=_("Flag indicating whether MFA is active for this admin account."),
    )

    backup_codes = models.JSONField(
        _("backup codes"),
        default=list,
        help_text=_("Hashed single-use emergency recovery codes."),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "admin_mfa"
        verbose_name = _("admin MFA setting")
        verbose_name_plural = _("admin MFA settings")

    def __str__(self):
        return f"AdminMFA for {self.user.email} (enabled={self.is_enabled})"


class Invitation(models.Model):
    """
    Model for platform user invitations.
    Stores cryptographically secure unique tokens generated by authenticated users.
    Tracks invitation status, expiration, and the newly registered user upon acceptance.
    """

    inviter = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
        help_text=_("User who generated the invitation link."),
    )

    token = models.CharField(
        _("invitation token"),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Unique cryptographically secure token string."),
    )

    is_used = models.BooleanField(
        _("is used"),
        default=False,
        help_text=_("Flag indicating whether the invitation has been accepted."),
    )

    invited_user = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_invitation",
        help_text=_("New user account created via this invitation."),
    )

    expires_at = models.DateTimeField(
        _("expires at"),
        null=True,
        blank=True,
        help_text=_("Optional expiration timestamp for the invitation token."),
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        db_table = "invitations"
        verbose_name = _("invitation")
        verbose_name_plural = _("invitations")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation by {self.inviter.email} (token={self.token[:8]}..., is_used={self.is_used})"


class ProviderProfile(models.Model):
    """
    Model representing an organization, company, or individual provider profile on NextGig.
    Linked OneToOne with CustomUser where role='provider'.
    """

    class OrganizationType(models.TextChoices):
        COMPANY = "company", _("Company")
        STARTUP = "startup", _("Startup")
        CAFE = "cafe", _("Cafe")
        RESTAURANT = "restaurant", _("Restaurant")
        SHOP = "shop", _("Shop")
        NGO = "ngo", _("NGO")
        EDUCATIONAL_INSTITUTION = "educational_institution", _("Educational Institution")
        FREELANCER = "freelancer", _("Freelancer")
        INDIVIDUAL = "individual", _("Individual")
        EVENT_ORGANIZER = "event_organizer", _("Event Organizer")
        OTHER = "other", _("Other")

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="provider_profile",
    )
    organization_name = models.CharField(max_length=200)
    organization_type = models.CharField(
        max_length=50,
        choices=OrganizationType.choices,
        default=OrganizationType.COMPANY,
    )
    description = models.TextField(blank=True)
    contact_person = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Admin verification flag for provider organization."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "provider_profiles"
        verbose_name = _("provider profile")
        verbose_name_plural = _("provider profiles")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.organization_name} ({self.user.email})"



