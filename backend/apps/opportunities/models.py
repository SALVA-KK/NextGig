from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _


class Opportunity(models.Model):
    """
    Model representing a job, internship, gig, or project opportunity posted on NextGig.
    """

    class Category(models.TextChoices):
        PART_TIME = "part_time", _("Part Time")
        INTERNSHIP = "internship", _("Internship")
        FREELANCE = "freelance", _("Freelance")
        STARTUP_HIRING = "startup_hiring", _("Startup Hiring")
        PROJECT_COLLABORATION = "project_collaboration", _("Project Collaboration")
        TUTORING = "tutoring", _("Tutoring")
        VOLUNTEER = "volunteer", _("Volunteer")
        EVENT_BASED = "event_based", _("Event Based")

    class PayType(models.TextChoices):
        HOURLY = "hourly", _("Hourly")
        MONTHLY = "monthly", _("Monthly")
        STIPEND = "stipend", _("Stipend")
        UNPAID = "unpaid", _("Unpaid")

    class WorkMode(models.TextChoices):
        REMOTE = "remote", _("Remote")
        ONSITE = "onsite", _("Onsite")
        HYBRID = "hybrid", _("Hybrid")

    class Status(models.TextChoices):
        OPEN = "open", _("Open")
        CLOSED = "closed", _("Closed")
        DRAFT = "draft", _("Draft")

    poster = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="posted_opportunities",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=Category.choices)
    required_skills = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    pay_type = models.CharField(max_length=20, choices=PayType.choices)
    pay_amount = models.DecimalField(
        null=True,
        blank=True,
        max_digits=10,
        decimal_places=2,
    )
    duration = models.CharField(max_length=100, blank=True)
    working_hours = models.CharField(max_length=100, blank=True)
    work_mode = models.CharField(max_length=20, choices=WorkMode.choices)
    location_text = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    latitude = models.DecimalField(
        null=True,
        blank=True,
        max_digits=9,
        decimal_places=6,
    )
    longitude = models.DecimalField(
        null=True,
        blank=True,
        max_digits=9,
        decimal_places=6,
    )
    vacancies = models.PositiveIntegerField(default=1)
    deadline = models.DateField(null=True, blank=True)
    contact_info = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "opportunities"
        verbose_name = _("opportunity")
        verbose_name_plural = _("opportunities")
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["status", "category", "city"],
                name="opp_status_cat_city_idx",
            ),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_category_display()}) - {self.status}"
