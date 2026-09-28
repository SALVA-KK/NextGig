from django.conf import settings
from rest_framework.throttling import SimpleRateThrottle


class AssistantBurstRateThrottle(SimpleRateThrottle):
    """
    Burst rate throttle for AI assistant chat.
    Limits requests to max 5 per minute per student user.
    """

    scope = "assistant_burst"
    rate = "5/minute"

    def get_cache_key(self, request, view):
        if getattr(settings, "TESTING", False):
            return None
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }


class AssistantSustainedRateThrottle(SimpleRateThrottle):
    """
    Sustained rate throttle for AI assistant chat.
    Limits requests to max 40 per hour per student user.
    """

    scope = "assistant_sustained"
    rate = "40/hour"

    def get_cache_key(self, request, view):
        if getattr(settings, "TESTING", False):
            return None
        if request.user and request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        return self.cache_format % {
            "scope": self.scope,
            "ident": ident,
        }
