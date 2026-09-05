from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsVerifiedUser(BasePermission):
    """
    Permission check granting access only to authenticated users with verified email/identity (is_verified=True).
    """

    message = "You must verify your email/account before performing this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "is_verified", False)
        )


class IsOwnerOrReadOnly(BasePermission):
    """
    Object-level permission allowing read access to anyone,
    and update/delete access only to the opportunity poster or an administrator.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        is_owner = obj.poster == request.user
        is_admin = getattr(request.user, "role", None) == "admin" or getattr(request.user, "is_staff", False)

        return is_owner or is_admin


class IsApplicantOrPoster(BasePermission):
    """
    Permission for status updates on an Application.
    - Poster (or Admin) can update status to under_review, accepted, or rejected.
    - Applicant can set status to 'withdrawn' (only if current status is applied or under_review).
    - Other users receive 403 Forbidden.
    """

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        user = request.user
        is_poster = obj.opportunity.poster == user or getattr(user, "role", None) == "admin" or getattr(user, "is_staff", False)
        is_applicant = obj.applicant == user

        if is_poster or is_applicant:
            return True

        return False
