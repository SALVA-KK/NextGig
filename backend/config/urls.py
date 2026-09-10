"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.accounts.admin_views import (
    AdminAuditLogListView,
    AdminPendingProvidersListView,
    AdminToggleUserActiveView,
    AdminUserListView,
    AdminVerifyProviderView,
)
from apps.opportunities.admin_views import (
    AdminDeleteOpportunityView,
    AdminForceCloseOpportunityView,
    AdminOpportunityListView,
)
from apps.opportunities.views import (
    ApplicationResumeDownloadView,
    ApplicationStatusUpdateView,
    MyApplicationsListView,
    ReceivedApplicationsListView,
    SavedOpportunityListView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    # Accounts API endpoints
    path("api/accounts/", include("apps.accounts.urls")),
    # Opportunities API endpoints
    path("api/opportunities/", include("apps.opportunities.urls")),
    # Notifications API endpoints
    path("api/notifications/", include("apps.notifications.urls")),
    # Saved Opportunities endpoint
    path("api/saved-opportunities/", SavedOpportunityListView.as_view(), name="root-saved-opportunity-list"),
    # Applications API endpoints
    path("api/applications/", MyApplicationsListView.as_view(), name="root-my-applications-list"),
    path("api/applications/received/", ReceivedApplicationsListView.as_view(), name="root-received-applications-list"),
    path("api/applications/<int:pk>/status/", ApplicationStatusUpdateView.as_view(), name="root-application-status-update"),
    path("api/applications/<int:pk>/resume/", ApplicationResumeDownloadView.as_view(), name="root-application-resume-download"),

    # Admin Panel API Endpoints
    path("api/admin/providers/pending/", AdminPendingProvidersListView.as_view(), name="admin-pending-providers"),
    path("api/admin/providers/<int:pk>/verify/", AdminVerifyProviderView.as_view(), name="admin-verify-provider"),
    path("api/admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("api/admin/users/<int:pk>/toggle-active/", AdminToggleUserActiveView.as_view(), name="admin-toggle-user-active"),
    path("api/admin/opportunities/", AdminOpportunityListView.as_view(), name="admin-opportunity-list"),
    path("api/admin/opportunities/<int:pk>/force-close/", AdminForceCloseOpportunityView.as_view(), name="admin-force-close-opportunity"),
    path("api/admin/opportunities/<int:pk>/", AdminDeleteOpportunityView.as_view(), name="admin-delete-opportunity"),
    path("api/admin/audit-log/", AdminAuditLogListView.as_view(), name="admin-audit-log"),

    # OpenAPI 3 Schema & API Documentation UI
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
