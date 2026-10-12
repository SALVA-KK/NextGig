import re
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.opportunities.models import Opportunity

User = get_user_model()


class SeedDemoOpportunitiesCommandTestCase(TestCase):
    def setUp(self):
        self.provider = User.objects.create_user(
            email="provider_seed@example.com",
            password="Password123!",
            full_name="Seed Provider User",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.student = User.objects.create_user(
            email="student_seed@example.com",
            password="Password123!",
            full_name="Seed Student User",
            role=User.Role.STUDENT,
            is_verified=True,
        )

    def test_creates_all_12_for_provider_and_refuses_student_or_missing_email(self):
        """
        Command creates all 12 demo listings for a valid provider, but raises CommandError
        if the poster email is missing, non-existent, or belongs to a student.
        """
        # 1. Missing / empty email raises CommandError
        with self.assertRaises(CommandError) as ctx_empty:
            call_command("seed_demo_opportunities", poster_email="")
        self.assertIn("required", str(ctx_empty.exception))

        # 2. Non-existent email raises CommandError
        with self.assertRaises(CommandError) as ctx_missing:
            call_command("seed_demo_opportunities", poster_email="doesnotexist@example.com")
        self.assertIn("does not exist", str(ctx_missing.exception))

        # 3. Student email raises CommandError
        with self.assertRaises(CommandError) as ctx_student:
            call_command("seed_demo_opportunities", poster_email=self.student.email)
        self.assertIn("must be a provider", str(ctx_student.exception))

        # 3. Valid provider creates all 12
        out = StringIO()
        call_command("seed_demo_opportunities", poster_email=self.provider.email, stdout=out)
        self.assertEqual(Opportunity.objects.filter(poster=self.provider).count(), 12)
        output = out.getvalue()
        self.assertIn("Created: 12", output)
        self.assertIn("UI/UX Design Intern for a Mobile App", output)
        self.assertIn("Mobile App Beta Testers", output)

    def test_idempotent_second_run_creates_zero_and_reports_exists(self):
        """
        A second execution does not create duplicate listings and reports existing ones.
        """
        # First run creates 12
        call_command("seed_demo_opportunities", poster_email=self.provider.email, stdout=StringIO())
        self.assertEqual(Opportunity.objects.filter(poster=self.provider).count(), 12)

        # Second run should skip all 12
        out = StringIO()
        call_command("seed_demo_opportunities", poster_email=self.provider.email, stdout=out)
        self.assertEqual(Opportunity.objects.filter(poster=self.provider).count(), 12)
        output = out.getvalue()
        self.assertIn("Created: 0", output)
        self.assertIn("Existing: 12", output)
        self.assertIn("[exists]", output)

    def test_dry_run_writes_nothing(self):
        """
        --dry-run simulates the creation and writes 0 records to the database.
        """
        out = StringIO()
        call_command(
            "seed_demo_opportunities",
            poster_email=self.provider.email,
            dry_run=True,
            stdout=out,
        )
        self.assertEqual(Opportunity.objects.filter(poster=self.provider).count(), 0)
        output = out.getvalue()
        self.assertIn("[DRY-RUN", output)
        self.assertIn("Would create: 12", output)

    def test_close_ids_closes_only_open_listings_leaves_others_untouched_and_never_deletes(self):
        """
        --close-ids closes open opportunities, leaves already-closed or draft ones untouched,
        and never deletes records.
        """
        opp_open = Opportunity.objects.create(
            poster=self.provider,
            title="Active Open Opp",
            category=Opportunity.Category.FULL_TIME,
            pay_type=Opportunity.PayType.MONTHLY,
            status=Opportunity.Status.OPEN,
        )
        opp_closed = Opportunity.objects.create(
            poster=self.provider,
            title="Already Closed Opp",
            category=Opportunity.Category.PART_TIME,
            pay_type=Opportunity.PayType.HOURLY,
            status=Opportunity.Status.CLOSED,
            close_reason=Opportunity.CloseReason.OWNER_CLOSED,
        )
        opp_draft = Opportunity.objects.create(
            poster=self.provider,
            title="Draft Opp",
            category=Opportunity.Category.FREELANCE,
            pay_type=Opportunity.PayType.UNPAID,
            status=Opportunity.Status.DRAFT,
        )

        initial_count = Opportunity.objects.count()

        out = StringIO()
        call_command(
            "seed_demo_opportunities",
            poster_email=self.provider.email,
            close_ids=f"{opp_open.id},{opp_closed.id},{opp_draft.id},999999",
            stdout=out,
        )

        # No records were deleted
        self.assertEqual(Opportunity.objects.count(), initial_count + 12)

        # Open record was closed with ADMIN_MODERATED
        opp_open.refresh_from_db()
        self.assertEqual(opp_open.status, Opportunity.Status.CLOSED)
        self.assertEqual(opp_open.close_reason, Opportunity.CloseReason.ADMIN_MODERATED)
        self.assertIsNone(opp_open.closed_by)

        # Already closed record was untouched
        opp_closed.refresh_from_db()
        self.assertEqual(opp_closed.status, Opportunity.Status.CLOSED)
        self.assertEqual(opp_closed.close_reason, Opportunity.CloseReason.OWNER_CLOSED)

        # Draft record was untouched
        opp_draft.refresh_from_db()
        self.assertEqual(opp_draft.status, Opportunity.Status.DRAFT)

        output = out.getvalue()
        self.assertIn(f"Closed open opportunity #{opp_open.id}", output)
        self.assertIn(f"Opportunity #{opp_closed.id} status is already 'closed', left untouched", output)
        self.assertIn(f"Opportunity #{opp_draft.id} status is already 'draft', left untouched", output)

    def test_deadlines_in_future_and_contact_info_contains_no_email_or_phone(self):
        """
        All seeded listings have deadlines strictly in the future, and contact_info
        contains no email addresses, phone digits, or real names.
        """
        call_command("seed_demo_opportunities", poster_email=self.provider.email, stdout=StringIO())
        today = timezone.localdate()

        seeded_opps = Opportunity.objects.filter(poster=self.provider)
        self.assertEqual(seeded_opps.count(), 12)

        email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        phone_digit_pattern = re.compile(r"\d{3,}")

        for opp in seeded_opps:
            # Deadline is strictly in the future
            self.assertIsNotNone(opp.deadline)
            self.assertGreater(opp.deadline, today)

            # Contact info matches safe placeholder
            self.assertEqual(opp.contact_info, "Apply through NextGig")
            self.assertIsNone(email_pattern.search(opp.contact_info))
            self.assertIsNone(phone_digit_pattern.search(opp.contact_info))
            self.assertNotIn("@", opp.contact_info)

    @override_settings(RAG_AUTO_INDEX=True)
    def test_signal_handler_called_when_rag_auto_index_is_true(self):
        """
        Creating listings via the command executes normal model save(), triggering
        the post_save signal and enqueuing indexing tasks when RAG_AUTO_INDEX=True.
        """
        with patch("apps.opportunities.tasks.index_opportunity_task.delay") as mock_delay:
            with self.captureOnCommitCallbacks(execute=True):
                call_command(
                    "seed_demo_opportunities",
                    poster_email=self.provider.email,
                    stdout=StringIO(),
                )
            # All 12 created open listings trigger the indexing task delay
            self.assertEqual(mock_delay.call_count, 12)
