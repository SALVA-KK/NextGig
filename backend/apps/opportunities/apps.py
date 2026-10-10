from django.apps import AppConfig


class OpportunitiesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.opportunities"

    def ready(self):
        import apps.opportunities.signals  # noqa: F401
