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


MAX_RESUME_SIZE = 5 * 1024 * 1024  # 5 MB in bytes
ALLOWED_RESUME_EXTENSIONS = [".pdf", ".docx"]


def validate_resume_file(file):
    """
    Validates uploaded resume file:
    - Must exist and be non-empty
    - Must not exceed 5 MB in size
    - Extension must be .pdf or .docx
    - Validates file signature (magic bytes) to prevent executable/renamed file uploads.
    """
    import os

    if not file:
        raise ValidationError(_("Please select a resume file."))

    file_size = getattr(file, "size", 0)
    if not file_size or file_size == 0:
        raise ValidationError(_("Uploaded file is empty. Please select a valid resume file."))

    if file_size > MAX_RESUME_SIZE:
        raise ValidationError(_("File is too large. Maximum allowed file size is 5 MB."))

    filename = getattr(file, "name", "")
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_RESUME_EXTENSIONS:
        raise ValidationError(
            _("Unsupported file type. Only PDF (.pdf) and Word (.docx) files are allowed.")
        )

    # Magic Bytes Inspection
    try:
        file.seek(0)
        header = file.read(2048)
        file.seek(0)
    except Exception:
        raise ValidationError(_("Unable to read uploaded file. Please select a valid file."))

    if ext == ".pdf":
        if not header.startswith(b"%PDF-"):
            raise ValidationError(
                _("Invalid or corrupted PDF file. Please select a genuine PDF document.")
            )

    elif ext == ".docx":
        # DOCX files are OpenXML ZIP packages starting with PK\x03\x04
        if not header.startswith(b"PK\x03\x04"):
            raise ValidationError(
                _("Invalid or corrupted Word document. Please select a genuine DOCX file.")
            )

    return file

