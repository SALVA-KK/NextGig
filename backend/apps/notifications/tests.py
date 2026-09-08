from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.opportunities.models import Application, Opportunity
from apps.opportunities.tasks import close_expired_opportunities
from .models import Notification

User = get_user_model()


class NotificationAPITests(APITestCase):
    """
    Test suite for in-app Notifications model, API endpoints, permissions, transactions,
    idempotency, and integration with Opportunity application and expiration workflows.
    """

    def setUp(self):
        self.poster = User.objects.create_user(
            email="poster_notif@example.com",
            password="Password123!",
            full_name="Poster User",
            role="provider",
            is_verified=True,
        )

        self.student = User.objects.create_user(
            email="student_notif@example.com",
            password="Password123!",
            full_name="Student Applicant",
            role="student",
            is_verified=True,
        )

        self.other_student = User.objects.create_user(
            email="other_student_notif@example.com",
            password="Password123!",
            full_name="Other Student",
            role="student",
            is_verified=True,
        )

        self.opportunity = Opportunity.objects.create(
            poster=self.poster,
            title="Backend Engineer Gig",
            description="Build Django REST APIs",
            category=Opportunity.Category.FREELANCE,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.HOURLY,
            status=Opportunity.Status.OPEN,
            deadline=date.today() + timedelta(days=10),
        )

        self.list_url = reverse("notifications:notification-list")
        self.unread_count_url = reverse("notifications:notification-unread-count")
        self.mark_all_read_url = reverse("notifications:notification-mark-all-read")

    def test_student_application_creates_in_app_notification_for_poster(self):
        """Applying to an opportunity creates an in-app Notification record for the poster."""
        apply_url = reverse("opportunities:opportunity-apply", kwargs={"pk": self.opportunity.pk})
        self.client.force_authenticate(user=self.student)

        response = self.client.post(apply_url, {"cover_note": "I love Django!"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        application = Application.objects.get(applicant=self.student, opportunity=self.opportunity)
        notif = Notification.objects.filter(recipient=self.poster).first()

        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, Notification.NotificationType.NEW_APPLICATION)
        self.assertEqual(notif.actor, self.student)
        self.assertEqual(notif.opportunity, self.opportunity)
        self.assertEqual(notif.application, application)
        self.assertEqual(notif.event_key, f"new_app:{application.id}")
        self.assertFalse(notif.is_read)

    def test_poster_status_change_creates_notification_for_applicant(self):
        """Poster updating status creates an in-app Notification for the applicant."""
        app = Application.objects.create(applicant=self.student, opportunity=self.opportunity, status="applied")
        status_url = f"/api/applications/{app.pk}/status/"

        self.client.force_authenticate(user=self.poster)
        res_review = self.client.patch(status_url, {"status": "under_review"})
        self.assertEqual(res_review.status_code, status.HTTP_200_OK)

        notif = Notification.objects.filter(recipient=self.student).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.notification_type, Notification.NotificationType.APPLICATION_STATUS_CHANGED)
        self.assertEqual(notif.actor, self.poster)
        self.assertEqual(notif.event_key, f"app_status:{app.id}:applied->under_review")

        # Second transition under_review -> accepted
        res_accept = self.client.patch(status_url, {"status": "accepted"})
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)

        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 2)
        notif_accept = Notification.objects.filter(recipient=self.student).first()
        self.assertEqual(notif_accept.event_key, f"app_status:{app.id}:under_review->accepted")

    def test_resubmitting_identical_status_does_not_create_duplicate_notification(self):
        """Re-submitting the status that is already set creates zero duplicate notifications."""
        app = Application.objects.create(applicant=self.student, opportunity=self.opportunity, status="under_review")
        status_url = f"/api/applications/{app.pk}/status/"

        self.client.force_authenticate(user=self.poster)
        res = self.client.patch(status_url, {"status": "under_review"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 0)

    def test_student_withdrawal_creates_notification_for_poster(self):
        """Student withdrawing their application creates an in-app notification for the poster (not student)."""
        app = Application.objects.create(applicant=self.student, opportunity=self.opportunity, status="applied")
        status_url = f"/api/applications/{app.pk}/status/"

        self.client.force_authenticate(user=self.student)
        res = self.client.patch(status_url, {"status": "withdrawn"})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Poster receives notification
        poster_notif = Notification.objects.filter(recipient=self.poster).first()
        self.assertIsNotNone(poster_notif)
        self.assertEqual(poster_notif.notification_type, Notification.NotificationType.APPLICATION_WITHDRAWN)
        self.assertEqual(poster_notif.event_key, f"app_withdraw:{app.id}")

        # Student receives 0 notifications
        self.assertEqual(Notification.objects.filter(recipient=self.student).count(), 0)

    def test_close_expired_opportunities_creates_transactional_notification(self):
        """Expired OPEN opportunity creates an in-app notification for poster when closed by Celery Beat task."""
        expired_opp = Opportunity.objects.create(
            poster=self.poster,
            title="Expired Internship",
            description="Old listing",
            category=Opportunity.Category.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.UNPAID,
            status=Opportunity.Status.OPEN,
            deadline=date.today() - timedelta(days=2),
        )

        closed_count = close_expired_opportunities()
        self.assertEqual(closed_count, 1)

        expired_opp.refresh_from_db()
        self.assertEqual(expired_opp.status, Opportunity.Status.CLOSED)

        notif = Notification.objects.filter(recipient=self.poster, notification_type=Notification.NotificationType.OPPORTUNITY_EXPIRED).first()
        self.assertIsNotNone(notif)
        self.assertEqual(notif.opportunity, expired_opp)
        self.assertEqual(notif.event_key, f"opp_expire:{expired_opp.id}")

        # Running task again does not create duplicate notification
        second_run_count = close_expired_opportunities()
        self.assertEqual(second_run_count, 0)
        self.assertEqual(Notification.objects.filter(recipient=self.poster, notification_type=Notification.NotificationType.OPPORTUNITY_EXPIRED).count(), 1)

    def test_user_notification_privacy_isolation(self):
        """User A cannot list or mark as read User B's notifications."""
        notif_poster = Notification.objects.create(
            recipient=self.poster,
            notification_type=Notification.NotificationType.NEW_APPLICATION,
            title="Poster Notif",
            message="Secret message",
        )

        self.client.force_authenticate(user=self.student)
        list_resp = self.client.get(self.list_url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(list_resp.data["count"], 0)

        mark_read_url = reverse("notifications:notification-mark-read", kwargs={"pk": notif_poster.pk})
        patch_resp = self.client.patch(mark_read_url)
        self.assertEqual(patch_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unread_count_endpoint(self):
        """GET /api/notifications/unread-count/ returns accurate count for current user."""
        Notification.objects.create(recipient=self.student, notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED, title="N1", message="M1", is_read=False)
        Notification.objects.create(recipient=self.student, notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED, title="N2", message="M2", is_read=False)
        Notification.objects.create(recipient=self.student, notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED, title="N3", message="M3", is_read=True)

        self.client.force_authenticate(user=self.student)
        resp = self.client.get(self.unread_count_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)

    def test_mark_single_and_all_notifications_read(self):
        """Single and bulk mark-all-as-read endpoints update read state idempotently."""
        n1 = Notification.objects.create(recipient=self.student, notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED, title="N1", message="M1", is_read=False)
        n2 = Notification.objects.create(recipient=self.student, notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED, title="N2", message="M2", is_read=False)

        self.client.force_authenticate(user=self.student)

        # Mark single as read
        mark_read_url = reverse("notifications:notification-mark-read", kwargs={"pk": n1.pk})
        patch_resp = self.client.patch(mark_read_url)
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_resp.data["is_read"])
        self.assertIsNotNone(patch_resp.data["read_at"])

        # Re-marking single read is idempotent and preserves read_at
        n1.refresh_from_db()
        first_read_at = n1.read_at
        patch_resp2 = self.client.patch(mark_read_url)
        self.assertEqual(patch_resp2.status_code, status.HTTP_200_OK)
        n1.refresh_from_db()
        self.assertEqual(n1.read_at, first_read_at)

        # Mark all read
        mark_all_resp = self.client.post(self.mark_all_read_url)
        self.assertEqual(mark_all_resp.status_code, status.HTTP_200_OK)

        n2.refresh_from_db()
        self.assertTrue(n2.is_read)
        self.assertIsNotNone(n2.read_at)

    def test_deleting_related_opportunity_or_application_sets_null(self):
        """Deleting an Opportunity or Application sets FK to NULL (SET_NULL) without deleting notification record."""
        app = Application.objects.create(applicant=self.student, opportunity=self.opportunity, status="applied")
        notif = Notification.objects.create(
            recipient=self.poster,
            actor=self.student,
            notification_type=Notification.NotificationType.NEW_APPLICATION,
            title="App Notif",
            message="Test message",
            opportunity=self.opportunity,
            application=app,
        )

        app.delete()
        notif.refresh_from_db()
        self.assertIsNone(notif.application)
        self.assertEqual(notif.opportunity, self.opportunity)

        self.opportunity.delete()
        notif.refresh_from_db()
        self.assertIsNone(notif.opportunity)
        self.assertEqual(notif.title, "App Notif")
