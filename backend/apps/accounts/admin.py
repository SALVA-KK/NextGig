from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, ProviderProfile


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Admin panel configuration for CustomUser model.
    """

    # Columns displayed on the admin user list table
    list_display = (
        "email",
        "full_name",
        "role",
        "phone_number",
        "is_verified",
        "is_staff",
        "is_active",
        "date_joined",
    )

    # Sidebar filters for list view
    list_filter = (
        "role",
        "is_verified",
        "is_active",
        "is_staff",
    )

    # Search bar targets
    search_fields = (
        "email",
        "full_name",
        "phone_number",
    )

    # Default list ordering (newest registered users first)
    ordering = ("-date_joined",)

    # Fieldset layout for editing an existing CustomUser
    fieldsets = (
        (
            _("Credentials"),
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            _("Personal Information"),
            {
                "fields": (
                    "full_name",
                    "phone_number",
                    "role",
                )
            },
        ),
        (
            _("Permissions & Verification"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_verified",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": (
                    "date_joined",
                    "email_verified_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    # Fieldset layout for adding a new CustomUser via admin panel
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "password1",
                    "password2",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    # Read-only timestamp fields prevent accidental manual overrides in admin UI
    readonly_fields = (
        "date_joined",
        "email_verified_at",
        "created_at",
        "updated_at",
    )


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for ProviderProfile model.
    Allows admins to inspect organization info and toggle `is_verified`.
    """

    list_display = (
        "organization_name",
        "user",
        "organization_type",
        "city",
        "is_verified",
        "created_at",
    )

    list_filter = (
        "organization_type",
        "is_verified",
    )

    list_editable = ("is_verified",)

    search_fields = (
        "organization_name",
        "user__email",
        "user__full_name",
        "city",
        "contact_person",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

