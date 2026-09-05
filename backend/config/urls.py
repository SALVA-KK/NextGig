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

from apps.opportunities.views import SavedOpportunityListView

urlpatterns = [
    path("admin/", admin.site.urls),
    # Accounts API endpoints
    path("api/accounts/", include("apps.accounts.urls")),
    # Opportunities API endpoints
    path("api/opportunities/", include("apps.opportunities.urls")),
    # Saved Opportunities endpoint
    path("api/saved-opportunities/", SavedOpportunityListView.as_view(), name="root-saved-opportunity-list"),
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
