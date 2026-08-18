from rest_framework.throttling import SimpleRateThrottle


class RegisterBurstRateThrottle(SimpleRateThrottle):
    """
    Short "burst" rate throttle for registration.
    Limits registration submissions to max 1 request per 4 seconds per IP address.
    Blocks automated bot submissions while remaining completely invisible to real users.
    """

    scope = "register_burst"
    rate = "1/4s"

    def parse_rate(self, rate):
        if rate == "1/4s":
            return (1, 4)
        return super().parse_rate(rate)

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class RegisterSustainedRateThrottle(SimpleRateThrottle):
    """
    Sustained longer-window rate throttle for registration.
    Limits registration submissions to max 20 requests per hour per IP address.
    Safety net against slow automated abuse while allowing real users ample
    attempts to fix form validation errors.
    """

    scope = "register_sustained"
    rate = "20/hour"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class ForgotPasswordIPRateThrottle(SimpleRateThrottle):
    """
    IP-based rate throttle for forgot-password requests.
    Limits password reset email requests to max 3 per hour per IP address.
    Prevents an IP from exhausting SMTP resources or abusing the endpoint.
    """

    scope = "forgot_password_ip"
    rate = "3/hour"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class ForgotPasswordEmailRateThrottle(SimpleRateThrottle):
    """
    Email-based rate throttle for forgot-password requests.
    Limits password reset email requests to max 3 per hour per target email address.
    Prevents distributed botnets/proxies from flooding a specific user's inbox.
    """

    scope = "forgot_password_email"
    rate = "3/hour"

    def get_cache_key(self, request, view):
        if request.user and request.user.is_authenticated:
            return None

        email = request.data.get("email") if hasattr(request, "data") else None
        if email and isinstance(email, str) and email.strip():
            normalized_email = email.strip().lower()
            return self.cache_format % {
                "scope": self.scope,
                "ident": normalized_email,
            }

        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }

