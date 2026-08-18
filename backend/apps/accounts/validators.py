import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class PasswordComplexityValidator:
    """
    Custom password validator requiring:
    - Minimum length of 8 characters, maximum of 128 characters
    - At least one uppercase letter (A-Z)
    - At least one lowercase letter (a-z)
    - At least one digit (0-9)
    - At least one special character (!@#$%^&*...)
    """

    def __init__(self, min_length=8, max_length=128):
        self.min_length = min_length
        self.max_length = max_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("This password must be at least %(min_length)d characters long."),
                code="password_too_short",
                params={"min_length": self.min_length},
            )

        if len(password) > self.max_length:
            raise ValidationError(
                _("This password cannot exceed %(max_length)d characters."),
                code="password_too_long",
                params={"max_length": self.max_length},
            )

        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                _("Password must contain at least one uppercase letter (A-Z)."),
                code="password_no_upper",
            )

        if not re.search(r"[a-z]", password):
            raise ValidationError(
                _("Password must contain at least one lowercase letter (a-z)."),
                code="password_no_lower",
            )

        if not re.search(r"\d", password):
            raise ValidationError(
                _("Password must contain at least one digit (0-9)."),
                code="password_no_digit",
            )

        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?`~]", password):
            raise ValidationError(
                _("Password must contain at least one special character (!@#$%^&*...)."),
                code="password_no_symbol",
            )

    def get_help_text(self):
        return _(
            "Your password must be between 8 and 128 characters long and include at least "
            "one uppercase letter, one lowercase letter, one digit, and one special character."
        )
