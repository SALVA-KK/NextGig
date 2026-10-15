import json
import logging
from datetime import date, timedelta
from unittest.mock import MagicMock, mock_open, patch

import requests
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.opportunities.models import Application, Opportunity
from apps.opportunities.tasks import close_expired_opportunities
from .fcm import (
    FCMTransientError,
    check_project_id_mismatch,
    get_fcm_credentials,
    reset_fcm_cache,
    send_fcm_v1_message,
)
from .models import DeviceToken, Notification
from .services import create_notification
from .tasks import send_push_notification

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


from unittest.mock import patch
from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_save
from django.test import TransactionTestCase, override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from config.asgi import application
from apps.notifications.routing import websocket_urlpatterns
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import create_notification


inner_application = URLRouter(websocket_urlpatterns)


@override_settings(
    ALLOWED_HOSTS=["localhost", "127.0.0.1", "testserver"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class NotificationWebSocketTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.user_a = User.objects.create_user(
            email="ws_user_a@example.com",
            password="Password123!",
            full_name="User Alpha",
            role="student",
            is_verified=True,
        )
        self.user_b = User.objects.create_user(
            email="ws_user_b@example.com",
            password="Password123!",
            full_name="User Beta",
            role="student",
            is_verified=True,
        )
        self.token_a = self._get_token(self.user_a)
        self.token_b = self._get_token(self.user_b)
        self.expired_token_a = self._get_expired_token(self.user_a)

    def _get_token(self, user):
        return str(RefreshToken.for_user(user).access_token)

    def _get_expired_token(self, user):
        tok = RefreshToken.for_user(user).access_token
        tok.set_exp(lifetime=timedelta(seconds=-10))
        return str(tok)

    async def test_valid_token_connects_successfully(self):
        communicator = WebsocketCommunicator(
            inner_application,
            f"/ws/notifications/?token={self.token_a}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_missing_token_rejected_with_4401(self):
        communicator = WebsocketCommunicator(
            inner_application,
            "/ws/notifications/",
        )
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_invalid_token_rejected_with_4401(self):
        communicator = WebsocketCommunicator(
            inner_application,
            "/ws/notifications/?token=invalid_jwt_token_payload",
        )
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_expired_token_rejected_with_4401(self):
        communicator = WebsocketCommunicator(
            inner_application,
            f"/ws/notifications/?token={self.expired_token_a}",
        )
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_inactive_user_rejected_with_4401(self):
        await sync_to_async(User.objects.filter(id=self.user_a.id).update)(is_active=False)
        communicator = WebsocketCommunicator(
            inner_application,
            f"/ws/notifications/?token={self.token_a}",
        )
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_wrong_origin_rejected_on_full_application(self):
        """AllowedHostsOriginValidator on full ASGI application rejects disallowed Origin."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/?token={self.token_a}",
            headers=[(b"origin", b"http://malicious-attacker.com")],
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_valid_origin_connects_on_full_application(self):
        """AllowedHostsOriginValidator on full ASGI application allows matching Origin."""
        communicator = WebsocketCommunicator(
            application,
            f"/ws/notifications/?token={self.token_a}",
            headers=[(b"origin", b"http://localhost:5173")],
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_creating_notification_pushes_to_owner_and_nothing_to_different_user(self):
        comm_a = WebsocketCommunicator(
            inner_application,
            f"/ws/notifications/?token={self.token_a}",
        )
        comm_b = WebsocketCommunicator(
            inner_application,
            f"/ws/notifications/?token={self.token_b}",
        )

        connected_a, _ = await comm_a.connect()
        connected_b, _ = await comm_b.connect()
        self.assertTrue(connected_a)
        self.assertTrue(connected_b)

        # Create notification for User A inside atomic block so on_commit triggers
        def _create_notif():
            with transaction.atomic():
                return create_notification(
                    recipient=self.user_a,
                    notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                    title="Status Updated",
                    message="Your application was accepted",
                )

        notif = await sync_to_async(_create_notif)()

        # User A receives exactly one event
        response = await comm_a.receive_json_from()
        self.assertEqual(response["type"], "notification")
        self.assertEqual(response["notification"]["id"], notif.id)
        self.assertEqual(response["notification"]["title"], "Status Updated")

        # Payload equals REST serializer output
        expected_serialized = await sync_to_async(lambda: NotificationSerializer(notif).data)()
        self.assertEqual(response["notification"], expected_serialized)

        # User B receives nothing
        self.assertTrue(await comm_b.receive_nothing())

        await comm_a.disconnect()
        await comm_b.disconnect()

    async def test_client_message_cannot_subscribe_to_another_group(self):
        communicator = WebsocketCommunicator(
            inner_application,
            f"/ws/notifications/?token={self.token_a}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Client attempts to send subscription or action payload
        await communicator.send_json_to({"action": "subscribe", "group": "user_notifications_9999"})

        # Consumer ignores inbound client message and doesn't crash or send anything back
        self.assertTrue(await communicator.receive_nothing())

        await communicator.disconnect()

    async def test_channel_layer_exception_does_not_break_notification_creation(self):
        channel_layer = get_channel_layer()

        def _create_notif():
            with transaction.atomic():
                return create_notification(
                    recipient=self.user_a,
                    notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                    title="Resilient Notif",
                    message="Channel layer failure will not prevent DB save",
                )

        with patch.object(channel_layer, "group_send", side_effect=Exception("Redis connection lost")):
            notif = await sync_to_async(_create_notif)()

        # Notification is safely committed and saved in database
        self.assertIsNotNone(notif.id)
        saved_notif = await sync_to_async(Notification.objects.filter(id=notif.id).first)()
        self.assertIsNotNone(saved_notif)
        self.assertEqual(saved_notif.title, "Resilient Notif")

    async def test_raw_true_save_does_not_push(self):
        communicator = WebsocketCommunicator(
            inner_application,
            f"/ws/notifications/?token={self.token_a}",
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        notif = await sync_to_async(Notification)(
            recipient=self.user_a,
            notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
            title="Raw Save Notif",
            message="Loaddata/fixture raw=True will not push",
        )
        # Call post_save with raw=True
        await sync_to_async(post_save.send)(
            sender=Notification,
            instance=notif,
            created=True,
            raw=True,
        )

        self.assertTrue(await communicator.receive_nothing())
        await communicator.disconnect()


class DeviceTokenAPITests(APITestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(
            email="token_user_a@example.com",
            password="Password123!",
            full_name="User A",
            role="student",
            is_verified=True,
        )
        self.user_b = User.objects.create_user(
            email="token_user_b@example.com",
            password="Password123!",
            full_name="User B",
            role="student",
            is_verified=True,
        )
        self.tokens_url = reverse("notifications:device-tokens")
        cache.clear()

    def test_register_device_token_authenticated(self):
        self.client.force_authenticate(user=self.user_a)
        res = self.client.post(
            self.tokens_url,
            {"token": "sample_fcm_token_1234567890", "platform": "web"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, {"status": "registered"})

        token_obj = DeviceToken.objects.get(token="sample_fcm_token_1234567890")
        self.assertEqual(token_obj.user, self.user_a)
        self.assertEqual(token_obj.platform, "web")
        self.assertTrue(token_obj.is_active)

        # Re-registering existing token for same user returns 200 and updates last_seen_at
        res_repeat = self.client.post(
            self.tokens_url,
            {"token": "sample_fcm_token_1234567890", "platform": "web"},
            format="json",
        )
        self.assertEqual(res_repeat.status_code, status.HTTP_200_OK)

    def test_reassign_device_token_across_users(self):
        # User A registers token first
        self.client.force_authenticate(user=self.user_a)
        self.client.post(
            self.tokens_url,
            {"token": "shared_browser_token_1234567890", "platform": "web"},
            format="json",
        )
        self.assertEqual(DeviceToken.objects.filter(user=self.user_a).count(), 1)

        # User B registers same token from shared browser
        self.client.force_authenticate(user=self.user_b)
        res_b = self.client.post(
            self.tokens_url,
            {"token": "shared_browser_token_1234567890", "platform": "web"},
            format="json",
        )
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)

        # Token is now owned by User B, User A has 0 tokens
        token_obj = DeviceToken.objects.get(token="shared_browser_token_1234567890")
        self.assertEqual(token_obj.user, self.user_b)
        self.assertEqual(DeviceToken.objects.filter(user=self.user_a).count(), 0)

    def test_unregister_device_token_authenticated(self):
        DeviceToken.objects.create(
            user=self.user_a,
            token="token_to_remove_1234567890",
            platform="web",
        )
        self.client.force_authenticate(user=self.user_a)
        res = self.client.delete(
            self.tokens_url,
            {"token": "token_to_remove_1234567890"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(DeviceToken.objects.filter(token="token_to_remove_1234567890").exists())

    def test_unregister_device_token_owned_by_another_user_returns_404(self):
        DeviceToken.objects.create(
            user=self.user_a,
            token="user_a_private_token_12345",
            platform="web",
        )
        self.client.force_authenticate(user=self.user_b)
        res = self.client.delete(
            self.tokens_url,
            {"token": "user_a_private_token_12345"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        # Token still belongs to User A
        self.assertTrue(DeviceToken.objects.filter(token="user_a_private_token_12345", user=self.user_a).exists())

    def test_device_token_endpoint_unauthenticated(self):
        res_post = self.client.post(
            self.tokens_url,
            {"token": "unauth_token_1234567890"},
            format="json",
        )
        self.assertEqual(res_post.status_code, status.HTTP_401_UNAUTHORIZED)

        res_delete = self.client.delete(
            self.tokens_url,
            {"token": "unauth_token_1234567890"},
            format="json",
        )
        self.assertEqual(res_delete.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_device_token_invalid_payload(self):
        self.client.force_authenticate(user=self.user_a)
        res_short = self.client.post(
            self.tokens_url,
            {"token": "short"},
            format="json",
        )
        self.assertEqual(res_short.status_code, status.HTTP_400_BAD_REQUEST)

        res_delete_invalid = self.client.delete(
            self.tokens_url,
            {"token": ""},
            format="json",
        )
        self.assertEqual(res_delete_invalid.status_code, status.HTTP_400_BAD_REQUEST)

    def test_device_token_throttling_31st_request_returns_429(self):
        self.client.force_authenticate(user=self.user_a)
        for i in range(30):
            res = self.client.post(
                self.tokens_url,
                {"token": f"fcm_token_throttle_test_{i:04d}", "platform": "web"},
                format="json",
            )
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res_31 = self.client.post(
            self.tokens_url,
            {"token": "fcm_token_throttle_test_0031", "platform": "web"},
            format="json",
        )
        self.assertEqual(res_31.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class FCMHttpV1ServiceTests(TestCase):
    def setUp(self):
        reset_fcm_cache()

    def tearDown(self):
        reset_fcm_cache()

    @override_settings(FCM_ENABLED=False)
    def test_get_credentials_returns_none_when_fcm_disabled(self):
        creds, project_id = get_fcm_credentials()
        self.assertIsNone(creds)
        self.assertIsNone(project_id)

    @override_settings(FCM_ENABLED=True, FIREBASE_CREDENTIALS_FILE="/nonexistent/path/creds.json")
    def test_missing_credentials_file_logs_warning_once_and_returns_none(self):
        with self.assertLogs("apps.notifications.fcm", level="WARNING") as cm:
            creds, project_id = get_fcm_credentials()
            self.assertIsNone(creds)
            self.assertIsNone(project_id)
            # Second call must not log another warning
            get_fcm_credentials()

        self.assertEqual(len(cm.output), 1)
        self.assertIn("FCM credentials file not found", cm.output[0])

    @override_settings(FCM_ENABLED=True, FIREBASE_CREDENTIALS_FILE="/mock/service-account.json")
    def test_lazy_credential_loading_caching_and_refresh(self):
        mock_json = json.dumps({"project_id": "test-fcm-project-v1"})

        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=mock_json)):
                with patch("google.oauth2.service_account.Credentials.from_service_account_file") as mock_from_file:
                    mock_creds = MagicMock()
                    mock_creds.valid = False
                    mock_creds.token = "initial_token"
                    mock_from_file.return_value = mock_creds

                    # First call loads creds and refreshes because valid=False
                    creds, project_id = get_fcm_credentials()
                    self.assertEqual(project_id, "test-fcm-project-v1")
                    self.assertEqual(creds, mock_creds)
                    mock_from_file.assert_called_once()
                    mock_creds.refresh.assert_called_once()

                    # Second call with valid=True reuses module cache without refresh or re-reading
                    mock_creds.valid = True
                    mock_creds.refresh.reset_mock()
                    creds2, project_id2 = get_fcm_credentials()
                    self.assertEqual(creds2, mock_creds)
                    self.assertEqual(project_id2, "test-fcm-project-v1")
                    mock_creds.refresh.assert_not_called()
                    self.assertEqual(mock_from_file.call_count, 1)

    def test_project_id_mismatch_warning_logged_once(self):
        with self.assertLogs("apps.notifications.fcm", level="WARNING") as cm:
            check_project_id_mismatch("service_acct_proj", candidate="different_proj")
            # Second call does not duplicate log
            check_project_id_mismatch("service_acct_proj", candidate="different_proj")

        self.assertEqual(len(cm.output), 1)
        self.assertIn("Firebase project mismatch detected", cm.output[0])

    @patch("apps.notifications.fcm.get_fcm_credentials")
    @patch("requests.post")
    def test_fcm_v1_send_success_with_explicit_timeout(self, mock_post, mock_get_creds):
        mock_creds = MagicMock()
        mock_creds.token = "oauth2_bearer_token"
        mock_get_creds.return_value = (mock_creds, "test-project-123")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = send_fcm_v1_message(
            device_token="device_token_xyz_12345",
            title="Gig Opportunity",
            body="New freelance project available",
            data={"notification_id": "42", "notification_type": "new_gig"},
            link="/dashboard",
        )

        self.assertEqual(res, {"status": "ok"})
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        self.assertEqual(kwargs.get("timeout"), 10)
        self.assertEqual(kwargs.get("headers", {}).get("Authorization"), "Bearer oauth2_bearer_token")
        self.assertEqual(
            mock_post.call_args[0][0],
            "https://fcm.googleapis.com/v1/projects/test-project-123/messages:send",
        )

    @patch("apps.notifications.fcm.get_fcm_credentials")
    @patch("requests.post")
    def test_fcm_v1_send_unregistered_deactivates(self, mock_post, mock_get_creds):
        mock_creds = MagicMock()
        mock_creds.token = "token"
        mock_get_creds.return_value = (mock_creds, "test-project-123")

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {
                "status": "INVALID_ARGUMENT",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError",
                        "errorCode": "UNREGISTERED",
                    }
                ],
            }
        }
        mock_post.return_value = mock_resp

        res = send_fcm_v1_message(
            device_token="unregistered_token_12345",
            title="Title",
            body="Body",
        )
        self.assertEqual(res.get("status"), "deactivate")
        self.assertEqual(res.get("error"), "UNREGISTERED")

    @patch("apps.notifications.fcm.get_fcm_credentials")
    @patch("requests.post")
    def test_fcm_v1_send_not_found_deactivates(self, mock_post, mock_get_creds):
        mock_creds = MagicMock()
        mock_get_creds.return_value = (mock_creds, "test-project-123")

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"error": {"status": "NOT_FOUND"}}
        mock_post.return_value = mock_resp

        res = send_fcm_v1_message(
            device_token="not_found_token_12345",
            title="Title",
            body="Body",
        )
        self.assertEqual(res.get("status"), "deactivate")

    @patch("apps.notifications.fcm.get_fcm_credentials")
    @patch("requests.post")
    def test_fcm_v1_send_invalid_argument_deactivates(self, mock_post, mock_get_creds):
        mock_creds = MagicMock()
        mock_get_creds.return_value = (mock_creds, "test-project-123")

        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.json.return_value = {
            "error": {
                "status": "INVALID_ARGUMENT",
                "details": [
                    {
                        "@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError",
                        "errorCode": "INVALID_ARGUMENT",
                    }
                ],
            }
        }
        mock_post.return_value = mock_resp

        res = send_fcm_v1_message(
            device_token="invalid_arg_token_12345",
            title="Title",
            body="Body",
        )
        self.assertEqual(res.get("status"), "deactivate")
        self.assertEqual(res.get("error"), "INVALID_ARGUMENT")

    @patch("apps.notifications.fcm.get_fcm_credentials")
    @patch("requests.post")
    def test_fcm_v1_send_429_raises_transient_error(self, mock_post, mock_get_creds):
        mock_creds = MagicMock()
        mock_get_creds.return_value = (mock_creds, "test-project-123")

        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        with self.assertRaises(FCMTransientError):
            send_fcm_v1_message("token_12345", "Title", "Body")

    @patch("apps.notifications.fcm.get_fcm_credentials")
    @patch("requests.post")
    def test_fcm_v1_send_503_raises_transient_error(self, mock_post, mock_get_creds):
        mock_creds = MagicMock()
        mock_get_creds.return_value = (mock_creds, "test-project-123")

        mock_resp = MagicMock()
        mock_resp.status_code = 503
        mock_post.return_value = mock_resp

        with self.assertRaises(FCMTransientError):
            send_fcm_v1_message("token_12345", "Title", "Body")

    @patch("apps.notifications.fcm.get_fcm_credentials")
    @patch("requests.post")
    def test_fcm_v1_send_timeout_raises_transient_error(self, mock_post, mock_get_creds):
        mock_creds = MagicMock()
        mock_get_creds.return_value = (mock_creds, "test-project-123")
        mock_post.side_effect = requests.Timeout("Read timeout")

        with self.assertRaises(FCMTransientError):
            send_fcm_v1_message("token_12345", "Title", "Body")

    @patch("apps.notifications.fcm.get_fcm_credentials")
    @patch("requests.post")
    def test_fcm_v1_send_permission_denied_gives_up(self, mock_post, mock_get_creds):
        mock_creds = MagicMock()
        mock_get_creds.return_value = (mock_creds, "test-project-123")

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.json.return_value = {"error": {"status": "PERMISSION_DENIED"}}
        mock_post.return_value = mock_resp

        res = send_fcm_v1_message("token_12345", "Title", "Body")
        self.assertEqual(res.get("status"), "error")
        self.assertEqual(res.get("error"), "PERMISSION_DENIED")


class FCMPushCeleryTaskTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="push_recipient@example.com",
            password="Password123!",
            full_name="Push Recipient",
            role="student",
            is_verified=True,
        )
        self.other_user = User.objects.create_user(
            email="other_push_user@example.com",
            password="Password123!",
            full_name="Other User",
            role="student",
            is_verified=True,
        )
        self.notification = Notification.objects.create(
            recipient=self.user,
            title="Interview Requested",
            message="You have been invited to interview.",
            notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
        )

    @override_settings(FCM_ENABLED=False)
    def test_task_skipped_when_fcm_disabled(self):
        res = send_push_notification(self.notification.id)
        self.assertEqual(res, "fcm_disabled")

    @override_settings(FCM_ENABLED=True)
    def test_task_skipped_when_no_active_tokens(self):
        res = send_push_notification(self.notification.id)
        self.assertEqual(res, "no_active_tokens")

    @override_settings(FCM_ENABLED=True)
    @patch("apps.notifications.tasks.send_fcm_v1_message")
    def test_task_delivers_to_active_tokens_only_and_payload_isolated(self, mock_send):
        DeviceToken.objects.create(
            user=self.user,
            token="active_token_1234567890",
            is_active=True,
        )
        DeviceToken.objects.create(
            user=self.user,
            token="inactive_token_9876543210",
            is_active=False,
        )

        mock_send.return_value = {"status": "ok"}

        res = send_push_notification(self.notification.id)
        self.assertEqual(res, "done")
        self.assertEqual(mock_send.call_count, 1)

        _, kwargs = mock_send.call_args
        self.assertEqual(kwargs.get("device_token"), "active_token_1234567890")
        self.assertEqual(kwargs.get("title"), "Interview Requested")
        self.assertEqual(kwargs.get("body"), "You have been invited to interview.")
        self.assertEqual(
            kwargs.get("data"),
            {
                "notification_id": str(self.notification.id),
                "notification_type": str(Notification.NotificationType.APPLICATION_STATUS_CHANGED),
            },
        )
        # Ensure recipient email and private fields are NOT passed
        self.assertNotIn("email", kwargs.get("data"))
        self.assertNotIn("push_recipient@example.com", str(kwargs))

    @override_settings(FCM_ENABLED=True)
    @patch("apps.notifications.tasks.send_fcm_v1_message")
    def test_task_deactivates_unregistered_token(self, mock_send):
        token = DeviceToken.objects.create(
            user=self.user,
            token="dead_token_1234567890",
            is_active=True,
        )
        mock_send.return_value = {"status": "deactivate", "error": "UNREGISTERED"}

        res = send_push_notification(self.notification.id)
        self.assertEqual(res, "done")

        token.refresh_from_db()
        self.assertFalse(token.is_active)

    @override_settings(FCM_ENABLED=True)
    @patch("apps.notifications.tasks.send_fcm_v1_message")
    def test_task_retries_on_transient_error(self, mock_send):
        DeviceToken.objects.create(
            user=self.user,
            token="token_for_retry_12345",
            is_active=True,
        )
        mock_send.side_effect = FCMTransientError("Rate limit 429")

        with patch.object(send_push_notification, "retry", side_effect=Exception("TaskRetried")) as mock_retry:
            with self.assertRaises(Exception) as cm:
                send_push_notification(self.notification.id)
            self.assertEqual(str(cm.exception), "TaskRetried")
            mock_retry.assert_called_once()

    @override_settings(FCM_ENABLED=True)
    @patch("apps.notifications.tasks.send_fcm_v1_message")
    def test_user_a_tokens_never_dispatched_for_user_b(self, mock_send):
        token_a = DeviceToken.objects.create(
            user=self.user,
            token="token_user_a_only_12345",
            is_active=True,
        )
        token_b = DeviceToken.objects.create(
            user=self.other_user,
            token="token_user_b_only_12345",
            is_active=True,
        )

        mock_send.return_value = {"status": "ok"}
        send_push_notification(self.notification.id)

        # Only Token A called, Token B never called
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args[1].get("device_token"), token_a.token)
        self.assertNotEqual(mock_send.call_args[1].get("device_token"), token_b.token)

    @override_settings(FCM_ENABLED=True)
    @patch("apps.notifications.tasks.send_fcm_v1_message")
    def test_logging_never_exposes_device_tokens(self, mock_send):
        secret_token_val = "SECRET_FCM_DEVICE_TOKEN_XYZ_9999"
        DeviceToken.objects.create(
            user=self.user,
            token=secret_token_val,
            is_active=True,
        )
        mock_send.return_value = {"status": "ok"}

        with self.assertLogs("apps.notifications.tasks", level="INFO") as cm:
            send_push_notification(self.notification.id)

        for log_line in cm.output:
            self.assertNotIn(secret_token_val, log_line)
            self.assertIn(f"notification {self.notification.id}", log_line)

    @override_settings(FCM_ENABLED=True)
    @patch("apps.notifications.tasks.send_fcm_v1_message")
    def test_task_retry_only_resends_failed_token_and_does_not_duplicate_success(self, mock_send):
        token_1 = DeviceToken.objects.create(
            user=self.user,
            token="token_success_12345",
            is_active=True,
        )
        token_2 = DeviceToken.objects.create(
            user=self.user,
            token="token_fail_12345",
            is_active=True,
        )

        def _send_side_effect(device_token, **kwargs):
            if device_token == token_1.token:
                return {"status": "ok"}
            elif device_token == token_2.token:
                raise FCMTransientError("Rate limit 429")
            return {"status": "error"}

        mock_send.side_effect = _send_side_effect

        with patch.object(send_push_notification, "retry", side_effect=Exception("TaskRetried")) as mock_retry:
            with self.assertRaises(Exception) as cm:
                send_push_notification(self.notification.id)
            self.assertEqual(str(cm.exception), "TaskRetried")
            mock_retry.assert_called_once()
            retry_args = mock_retry.call_args[1].get("args") or mock_retry.call_args[0]
            # retry is called with only the second token's id
            self.assertEqual(retry_args[0], self.notification.id)
            self.assertEqual(retry_args[1], [token_2.id])

        # Both tokens were attempted in the first run (token 1 succeeded, token 2 failed)
        self.assertEqual(mock_send.call_count, 2)

        # Now simulate the retry run: invoke task with token_ids=[token_2.id]
        mock_send.reset_mock()
        mock_send.side_effect = None
        mock_send.return_value = {"status": "ok"}

        retry_result = send_push_notification(self.notification.id, token_ids=[token_2.id])
        self.assertEqual(retry_result, "done")
        # Token 1 is NOT sent twice; mock_send is called ONLY once for token 2
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(mock_send.call_args[1].get("device_token"), token_2.token)

    @override_settings(FCM_ENABLED=True)
    @patch("apps.notifications.tasks.send_fcm_v1_message")
    def test_task_max_retries_exceeded_does_not_raise(self, mock_send):
        DeviceToken.objects.create(
            user=self.user,
            token="token_always_transient_12345",
            is_active=True,
        )
        mock_send.side_effect = FCMTransientError("Service Unavailable 503")

        with patch.object(
            send_push_notification,
            "retry",
            side_effect=send_push_notification.MaxRetriesExceededError("Max retries exceeded"),
        ):
            # Calling task when max retries exceeded must NOT raise an exception
            res = send_push_notification(self.notification.id)
            self.assertEqual(res, "max_retries_exceeded")


class FCMSignalIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="signal_push_user@example.com",
            password="Password123!",
            full_name="Signal User",
            role="student",
            is_verified=True,
        )

    @override_settings(FCM_ENABLED=True)
    def test_signal_enqueues_celery_task_when_tokens_exist(self):
        DeviceToken.objects.create(
            user=self.user,
            token="signal_active_token_12345",
            is_active=True,
        )
        with patch("apps.notifications.tasks.send_push_notification.delay") as mock_delay:
            with self.captureOnCommitCallbacks(execute=True):
                notif = create_notification(
                    recipient=self.user,
                    notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                    title="Signal Enqueue Test",
                    message="Testing task delay on commit",
                )

            mock_delay.assert_called_once_with(notif.id)

    @override_settings(FCM_ENABLED=True)
    def test_signal_does_not_enqueue_when_no_active_tokens(self):
        with patch("apps.notifications.tasks.send_push_notification.delay") as mock_delay:
            with self.captureOnCommitCallbacks(execute=True):
                create_notification(
                    recipient=self.user,
                    notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                    title="No Tokens Test",
                    message="No active tokens exists",
                )

            mock_delay.assert_not_called()

    @override_settings(FCM_ENABLED=False)
    def test_signal_does_not_enqueue_when_fcm_disabled(self):
        DeviceToken.objects.create(
            user=self.user,
            token="disabled_fcm_token_12345",
            is_active=True,
        )
        with patch("apps.notifications.tasks.send_push_notification.delay") as mock_delay:
            with self.captureOnCommitCallbacks(execute=True):
                create_notification(
                    recipient=self.user,
                    notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                    title="FCM Disabled Test",
                    message="Flag is disabled",
                )

            mock_delay.assert_not_called()

    @override_settings(FCM_ENABLED=True)
    def test_signal_raw_true_does_not_enqueue(self):
        DeviceToken.objects.create(
            user=self.user,
            token="raw_true_token_12345",
            is_active=True,
        )
        with patch("apps.notifications.tasks.send_push_notification.delay") as mock_delay:
            with self.captureOnCommitCallbacks(execute=True):
                notif = Notification(
                    recipient=self.user,
                    notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                    title="Raw True Notification",
                    message="Loaddata raw=True test",
                )
                from django.db.models.signals import post_save
                post_save.send(
                    sender=Notification,
                    instance=notif,
                    created=True,
                    raw=True,
                )

            mock_delay.assert_not_called()

    @override_settings(FCM_ENABLED=True)
    def test_signal_celery_broker_failure_does_not_break_db_save(self):
        DeviceToken.objects.create(
            user=self.user,
            token="resilient_token_12345",
            is_active=True,
        )
        with patch(
            "apps.notifications.tasks.send_push_notification.delay",
            side_effect=Exception("Celery broker connection refused"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                notif = create_notification(
                    recipient=self.user,
                    notification_type=Notification.NotificationType.APPLICATION_STATUS_CHANGED,
                    title="Resilient DB Notification",
                    message="Failure in Celery must not prevent DB commit",
                )

            self.assertIsNotNone(notif.id)
            self.assertTrue(Notification.objects.filter(id=notif.id).exists())


