from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Opportunity, SavedOpportunity


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for Opportunity model.
    """

    list_display = (
        "title",
        "poster",
        "category",
        "work_mode",
        "status",
        "city",
        "created_at",
    )

    list_filter = (
        "category",
        "status",
        "work_mode",
        "pay_type",
    )

    search_fields = (
        "title",
        "city",
        "description",
        "poster__email",
        "poster__full_name",
    )

    ordering = ("-created_at",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (
            _("Basic Information"),
            {
                "fields": (
                    "poster",
                    "title",
                    "description",
                    "category",
                    "status",
                    "vacancies",
                )
            },
        ),
        (
            _("Work & Pay Details"),
            {
                "fields": (
                    "work_mode",
                    "pay_type",
                    "pay_amount",
                    "duration",
                    "working_hours",
                    "required_skills",
                )
            },
        ),
        (
            _("Location & Contacts"),
            {
                "fields": (
                    "location_text",
                    "city",
                    "latitude",
                    "longitude",
                    "contact_info",
                    "deadline",
                )
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )


@admin.register(SavedOpportunity)
class SavedOpportunityAdmin(admin.ModelAdmin):
    """
    Admin panel configuration for SavedOpportunity model.
    """

    list_display = (
        "user",
        "opportunity",
        "created_at",
    )

    search_fields = (
        "user__email",
        "user__full_name",
        "opportunity__title",
    )

    ordering = ("-created_at",)

    readonly_fields = ("created_at",)

