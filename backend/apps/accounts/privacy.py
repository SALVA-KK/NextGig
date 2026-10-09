"""
Shared privacy helper for gating user contact information (phone number and WhatsApp number).
Used across public profile serializers to enforce user privacy preferences.
"""


def get_gated_phone_number(user, profile=None):
    """
    Returns phone_number only if profile exists and profile.show_phone is True.
    Checks profile.phone_number first, falling back to user.phone_number.
    Otherwise returns None (consistently with PosterPublicSerializer).
    """
    if profile is None:
        if getattr(user, "role", None) == "provider":
            profile = getattr(user, "provider_profile", None)
        elif getattr(user, "role", None) == "student":
            profile = getattr(user, "student_profile", None)

    if profile and getattr(profile, "show_phone", False):
        if hasattr(profile, "phone_number") and profile.phone_number:
            return profile.phone_number
        return getattr(user, "phone_number", None)
    return None


def get_gated_whatsapp_number(profile):
    """
    Returns whatsapp_number only if profile exists and profile.show_whatsapp is True.
    Otherwise returns None (consistently with PosterPublicSerializer).
    """
    if profile and getattr(profile, "show_whatsapp", False):
        return getattr(profile, "whatsapp_number", None)
    return None
