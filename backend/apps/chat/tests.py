import json
from datetime import timedelta
from unittest.mock import patch

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import StudentProfile
from apps.notifications.models import Notification
from apps.notifications.routing import websocket_urlpatterns
from apps.opportunities.models import Application, Opportunity
from .models import Conversation, Message, MessageRequest

User = get_user_model()
inner_application = URLRouter(websocket_urlpatterns)


class ChatAPITests(APITestCase):
    """
    HTTP API tests for chat conversations and messages.
    """

    def setUp(self):
        cache.clear()

        # Provider poster
        self.provider_poster = User.objects.create_user(
            email="provider_poster@example.com",
            password="Password123!",
            full_name="Provider Poster",
            role="provider",
            is_verified=True,
        )

        # Student poster (students can also post opportunities)
        self.student_poster = User.objects.create_user(
            email="student_poster@example.com",
            password="Password123!",
            full_name="Student Poster",
            role="student",
            is_verified=True,
        )

        # Applicant student
        self.applicant = User.objects.create_user(
            email="applicant_student@example.com",
            password="Password123!",
            full_name="Applicant Student",
            role="student",
            is_verified=True,
        )

        # Third-party user
        self.third_party = User.objects.create_user(
            email="third_party@example.com",
            password="Password123!",
            full_name="Third Party User",
            role="student",
            is_verified=True,
        )

        # Opportunities
        self.provider_opp = Opportunity.objects.create(
            poster=self.provider_poster,
            title="Backend Engineer Intern",
            description="Build APIs with Django.",
            category=Opportunity.Category.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.STIPEND,
            status=Opportunity.Status.OPEN,
            deadline=timezone.now().date() + timedelta(days=30),
        )

        self.student_opp = Opportunity.objects.create(
            poster=self.student_poster,
            title="Peer Collaboration Project",
            description="Collaborate on open source.",
            category=Opportunity.Category.PROJECT_COLLABORATION,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.UNPAID,
            status=Opportunity.Status.OPEN,
            deadline=timezone.now().date() + timedelta(days=30),
        )

        # Applications
        self.provider_app = Application.objects.create(
            applicant=self.applicant,
            opportunity=self.provider_opp,
            status="applied",
            cover_note="Excited to apply!",
        )

        self.student_app = Application.objects.create(
            applicant=self.applicant,
            opportunity=self.student_opp,
            status="applied",
            cover_note="Excited to collaborate!",
        )

    # ---------------------------------------------------------
    # CREATION TESTS
    # ---------------------------------------------------------

    def test_unauthenticated_cannot_create_conversation(self):
        res = self.client.post("/api/chat/conversations/", {"application_id": self.provider_app.id})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_applicant_can_create_conversation_with_provider_poster(self):
        self.client.force_authenticate(user=self.applicant)
        res = self.client.post("/api/chat/conversations/", {"application_id": self.provider_app.id})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data
        self.assertIn("id", data)
        self.assertEqual(data["other_participant"]["id"], self.provider_poster.id)
        self.assertEqual(data["other_participant"]["full_name"], "Provider Poster")
        self.assertEqual(data["opportunity"]["id"], self.provider_opp.id)
        self.assertEqual(data["opportunity"]["title"], "Backend Engineer Intern")

    def test_provider_poster_can_create_conversation_with_applicant(self):
        self.client.force_authenticate(user=self.provider_poster)
        res = self.client.post("/api/chat/conversations/", {"application_id": self.provider_app.id})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.data
        self.assertEqual(data["other_participant"]["id"], self.applicant.id)
        self.assertEqual(data["other_participant"]["full_name"], "Applicant Student")

    def test_works_when_poster_is_student(self):
        self.client.force_authenticate(user=self.applicant)
        res = self.client.post("/api/chat/conversations/", {"application_id": self.student_app.id})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["other_participant"]["id"], self.student_poster.id)

        # Poster student can also access/create
        self.client.force_authenticate(user=self.student_poster)
        res2 = self.client.post("/api/chat/conversations/", {"application_id": self.student_app.id})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["id"], res.data["id"])

    def test_third_party_user_gets_404_on_creation(self):
        self.client.force_authenticate(user=self.third_party)
        res = self.client.post("/api/chat/conversations/", {"application_id": self.provider_app.id})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_duplicate_creation_returns_same_conversation_200(self):
        self.client.force_authenticate(user=self.applicant)
        res1 = self.client.post("/api/chat/conversations/", {"application_id": self.provider_app.id})
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post("/api/chat/conversations/", {"application_id": self.provider_app.id})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data["id"], res2.data["id"])
        self.assertEqual(Conversation.objects.count(), 1)

    def test_withdrawn_application_cannot_create_conversation(self):
        self.provider_app.status = "withdrawn"
        self.provider_app.save()

        self.client.force_authenticate(user=self.applicant)
        res = self.client.post("/api/chat/conversations/", {"application_id": self.provider_app.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("withdrawn", res.data["detail"].lower())

    def test_self_application_cannot_create_conversation(self):
        # Directly create self-application in DB for edge test
        self_app = Application(
            applicant=self.student_poster,
            opportunity=self.student_opp,
            status="applied",
        )
        self_app.save()

        self.client.force_authenticate(user=self.student_poster)
        res = self.client.post("/api/chat/conversations/", {"application_id": self_app.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("self-application", res.data["detail"].lower())

    # ---------------------------------------------------------
    # MESSAGES TESTS
    # ---------------------------------------------------------

    def test_non_participant_gets_404_on_messages_list_and_send(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        self.client.force_authenticate(user=self.third_party)
        # GET messages
        res_get = self.client.get(f"/api/chat/conversations/{conv.id}/messages/")
        self.assertEqual(res_get.status_code, status.HTTP_404_NOT_FOUND)

        # POST message
        res_post = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": "Hello"})
        self.assertEqual(res_post.status_code, status.HTTP_404_NOT_FOUND)

    def test_blank_whitespace_and_over_2000_bodies_rejected(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        self.client.force_authenticate(user=self.applicant)

        # Blank
        res_empty = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": ""})
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)

        # Whitespace only
        res_ws = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": "   \n\t  "})
        self.assertEqual(res_ws.status_code, status.HTTP_400_BAD_REQUEST)

        # Over 2000 characters
        res_long = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": "a" * 2001})
        self.assertEqual(res_long.status_code, status.HTTP_400_BAD_REQUEST)

    def test_body_is_stripped_on_send(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        self.client.force_authenticate(user=self.applicant)
        res = self.client.post(
            f"/api/chat/conversations/{conv.id}/messages/",
            {"body": "   Hello, this has padding!   \n"},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["body"], "Hello, this has padding!")
        msg = Message.objects.get(id=res.data["id"])
        self.assertEqual(msg.body, "Hello, this has padding!")

    def test_sending_after_withdrawal_blocked_while_history_stays_readable(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )
        # Send initial message while active
        Message.objects.create(conversation=conv, sender=self.applicant, body="Initial message")

        # Now applicant withdraws
        self.provider_app.status = "withdrawn"
        self.provider_app.save()

        self.client.force_authenticate(user=self.applicant)

        # Reading history is 200 OK
        res_list = self.client.get(f"/api/chat/conversations/{conv.id}/messages/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        results = res_list.data.get("results", res_list.data)
        self.assertEqual(len(results), 1)

        # Sending new message is blocked
        res_send = self.client.post(
            f"/api/chat/conversations/{conv.id}/messages/",
            {"body": "Trying to message after withdrawal"},
        )
        self.assertEqual(res_send.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("withdrawn", res_send.data["detail"].lower())

    def test_pagination_order_oldest_to_newest(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        m1 = Message.objects.create(conversation=conv, sender=self.applicant, body="Message 1")
        m2 = Message.objects.create(conversation=conv, sender=self.provider_poster, body="Message 2")
        m3 = Message.objects.create(conversation=conv, sender=self.applicant, body="Message 3")

        self.client.force_authenticate(user=self.applicant)
        res = self.client.get(f"/api/chat/conversations/{conv.id}/messages/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get("results", res.data)
        self.assertEqual([m["id"] for m in results], [m1.id, m2.id, m3.id])

    def test_sending_throttle_31st_returns_429(self):
        cache.clear()
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        self.client.force_authenticate(user=self.applicant)

        for i in range(30):
            res = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": f"Msg {i}"})
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # 31st send in the same minute
        res_31 = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": "Msg 31"})
        self.assertEqual(res_31.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    # ---------------------------------------------------------
    # READ / UNREAD TESTS
    # ---------------------------------------------------------

    def test_read_marks_only_other_users_messages(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        m_from_poster = Message.objects.create(
            conversation=conv, sender=self.provider_poster, body="Hello from poster"
        )
        m_from_applicant = Message.objects.create(
            conversation=conv, sender=self.applicant, body="Hello from applicant"
        )

        self.assertIsNone(m_from_poster.read_at)
        self.assertIsNone(m_from_applicant.read_at)

        # Applicant reads the conversation
        self.client.force_authenticate(user=self.applicant)
        res = self.client.post(f"/api/chat/conversations/{conv.id}/read/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["unread_total"], 0)

        m_from_poster.refresh_from_db()
        m_from_applicant.refresh_from_db()

        # Only poster's message was marked read
        self.assertIsNotNone(m_from_poster.read_at)
        # Applicant's own message remains unread from poster's perspective
        self.assertIsNone(m_from_applicant.read_at)

    def test_unread_count_endpoint_and_accuracy(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        Message.objects.create(conversation=conv, sender=self.provider_poster, body="Unread 1")
        Message.objects.create(conversation=conv, sender=self.provider_poster, body="Unread 2")
        Message.objects.create(conversation=conv, sender=self.applicant, body="Sent by applicant")

        # Unread count for applicant should be 2
        self.client.force_authenticate(user=self.applicant)
        res_app = self.client.get("/api/chat/unread-count/")
        self.assertEqual(res_app.status_code, status.HTTP_200_OK)
        self.assertEqual(res_app.data["unread_total"], 2)

        # Unread count for poster should be 1
        self.client.force_authenticate(user=self.provider_poster)
        res_poster = self.client.get("/api/chat/unread-count/")
        self.assertEqual(res_poster.status_code, status.HTTP_200_OK)
        self.assertEqual(res_poster.data["unread_total"], 1)

    # ---------------------------------------------------------
    # PRIVACY TESTS
    # ---------------------------------------------------------

    def test_privacy_no_email_phone_address_in_payloads(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )
        Message.objects.create(conversation=conv, sender=self.provider_poster, body="Hello privacy")

        self.client.force_authenticate(user=self.applicant)

        # Check conversations list
        res_conv = self.client.get("/api/chat/conversations/")
        self.assertEqual(res_conv.status_code, status.HTTP_200_OK)
        conv_json = json.dumps(res_conv.data)
        self.assertNotIn("email", conv_json)
        self.assertNotIn("phone", conv_json)
        self.assertNotIn("address", conv_json)
        self.assertNotIn("provider_poster@example.com", conv_json)

        # Check messages list
        res_msg = self.client.get(f"/api/chat/conversations/{conv.id}/messages/")
        self.assertEqual(res_msg.status_code, status.HTTP_200_OK)
        msg_json = json.dumps(res_msg.data)
        self.assertNotIn("email", msg_json)
        self.assertNotIn("phone", msg_json)
        self.assertNotIn("address", msg_json)
        self.assertNotIn("provider_poster@example.com", msg_json)

        # Check other participant structure
        results = res_conv.data.get("results", res_conv.data)
        other = results[0]["other_participant"]
        self.assertEqual(set(other.keys()), {"id", "full_name"})

    # ---------------------------------------------------------
    # FIRST-MESSAGE NOTIFICATION TESTS
    # ---------------------------------------------------------

    def test_first_message_notification_created_once_per_direction(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        self.client.force_authenticate(user=self.applicant)

        # Message 1 from applicant to poster -> notification created for poster
        res1 = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": "First msg"})
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.provider_poster,
                notification_type=Notification.NotificationType.NEW_CHAT_MESSAGE,
            ).count(),
            1,
        )
        notif = Notification.objects.get(
            recipient=self.provider_poster,
            notification_type=Notification.NotificationType.NEW_CHAT_MESSAGE,
        )
        self.assertEqual(notif.title, "New message")
        self.assertIn("Applicant Student", notif.message)
        self.assertIn("Backend Engineer Intern", notif.message)
        self.assertNotIn("First msg", notif.message)  # No message body in notification

        # Message 2 from applicant to poster -> NO new notification
        res2 = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": "Second msg"})
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.provider_poster,
                notification_type=Notification.NotificationType.NEW_CHAT_MESSAGE,
            ).count(),
            1,
        )

        # Message 1 from poster to applicant -> notification created for applicant
        self.client.force_authenticate(user=self.provider_poster)
        res3 = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": "Poster reply 1"})
        self.assertEqual(res3.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.applicant,
                notification_type=Notification.NotificationType.NEW_CHAT_MESSAGE,
            ).count(),
            1,
        )

        # Message 2 from poster to applicant -> NO new notification
        res4 = self.client.post(f"/api/chat/conversations/{conv.id}/messages/", {"body": "Poster reply 2"})
        self.assertEqual(res4.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Notification.objects.filter(
                recipient=self.applicant,
                notification_type=Notification.NotificationType.NEW_CHAT_MESSAGE,
            ).count(),
            1,
        )

    # ---------------------------------------------------------
    # BOUNDED QUERY COUNT (NO N+1)
    # ---------------------------------------------------------

    def test_list_endpoint_query_count_bounded_with_10_plus_conversations(self):
        # Create 12 conversations with other users
        for i in range(12):
            other_user = User.objects.create_user(
                email=f"bounded_other_{i}@example.com",
                password="Password123!",
                full_name=f"Bounded User {i}",
                role="student",
                is_verified=True,
            )
            opp = Opportunity.objects.create(
                poster=self.provider_poster,
                title=f"Opp {i}",
                description="Test",
                category=Opportunity.Category.INTERNSHIP,
                work_mode=Opportunity.WorkMode.REMOTE,
                pay_type=Opportunity.PayType.STIPEND,
                status=Opportunity.Status.OPEN,
                deadline=timezone.now().date() + timedelta(days=30),
            )
            app = Application.objects.create(
                applicant=other_user,
                opportunity=opp,
                status="applied",
            )
            conv = Conversation.objects.create(
                user_one=min(other_user, self.provider_poster, key=lambda u: u.id),
                user_two=max(other_user, self.provider_poster, key=lambda u: u.id),
                application=app,
                opportunity=opp,
            )
            Message.objects.create(conversation=conv, sender=other_user, body=f"Hello in {i}")

        self.client.force_authenticate(user=self.provider_poster)

        # Expect strictly 2 queries:
        # 1. COUNT for pagination
        # 2. SELECT conversations with JOIN on user_one, user_two, opportunity + annotations (unread_count, Subquery)
        with self.assertNumQueries(2):
            res = self.client.get("/api/chat/conversations/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            results = res.data.get("results", res.data)
            self.assertGreaterEqual(len(results), 12)

    def test_first_message_notification_has_no_email_in_api(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        # Applicant sends first message
        self.client.force_authenticate(user=self.applicant)
        res_msg = self.client.post(
            f"/api/chat/conversations/{conv.id}/messages/",
            {"body": "Hello provider, nice to meet you!"},
        )
        self.assertEqual(res_msg.status_code, status.HTTP_201_CREATED)

        # Recipient (provider poster) requests /api/notifications/
        self.client.force_authenticate(user=self.provider_poster)
        res_notif = self.client.get("/api/notifications/")
        self.assertEqual(res_notif.status_code, status.HTTP_200_OK)

        notif_json = json.dumps(res_notif.data)
        # Assert JSON contains no email address and no "@"
        self.assertNotIn("@", notif_json)
        self.assertNotIn(self.applicant.email, notif_json)
        self.assertNotIn(self.provider_poster.email, notif_json)

        results = res_notif.data.get("results", res_notif.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["notification_type"], "new_chat_message")
        self.assertIsNone(results[0]["actor"])

    def test_messages_ordering_desc_and_invalid_fallback(self):
        conv = Conversation.objects.create(
            user_one=min(self.applicant, self.provider_poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.provider_poster, key=lambda u: u.id),
            application=self.provider_app,
            opportunity=self.provider_opp,
        )

        m1 = Message.objects.create(conversation=conv, sender=self.applicant, body="First message")
        m2 = Message.objects.create(conversation=conv, sender=self.provider_poster, body="Second message")
        m3 = Message.objects.create(conversation=conv, sender=self.applicant, body="Third message")

        self.client.force_authenticate(user=self.applicant)

        # Default (ascending: oldest first)
        res_default = self.client.get(f"/api/chat/conversations/{conv.id}/messages/")
        self.assertEqual(res_default.status_code, status.HTTP_200_OK)
        ids_default = [m["id"] for m in res_default.data["results"]]
        self.assertEqual(ids_default, [m1.id, m2.id, m3.id])

        # order=desc (newest first)
        res_desc = self.client.get(f"/api/chat/conversations/{conv.id}/messages/?order=desc")
        self.assertEqual(res_desc.status_code, status.HTTP_200_OK)
        ids_desc = [m["id"] for m in res_desc.data["results"]]
        self.assertEqual(ids_desc, [m3.id, m2.id, m1.id])

        # Invalid order values fall back to ascending
        for invalid_val in ["asc", "invalid", "unknown", "123", "none"]:
            res_invalid = self.client.get(f"/api/chat/conversations/{conv.id}/messages/?order={invalid_val}")
            self.assertEqual(res_invalid.status_code, status.HTTP_200_OK)
            ids_invalid = [m["id"] for m in res_invalid.data["results"]]
            self.assertEqual(ids_invalid, [m1.id, m2.id, m3.id])

    def test_conversation_creation_race_integrity_error_simulated(self):
        self.client.force_authenticate(user=self.applicant)

        from django.db import IntegrityError

        orig_create = Conversation.objects.create

        def side_effect_create(*args, **kwargs):
            # Another concurrent request created the conversation just ahead of this one
            orig_create(*args, **kwargs)
            # Simulate DB IntegrityError on concurrent duplicate insert
            raise IntegrityError("duplicate key value violates unique constraint")

        with patch.object(Conversation.objects, "create", side_effect=side_effect_create):
            res = self.client.post("/api/chat/conversations/", {"application_id": self.provider_app.id})
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertIn("id", res.data)
            self.assertEqual(Conversation.objects.filter(application=self.provider_app).count(), 1)


@override_settings(
    ALLOWED_HOSTS=["localhost", "127.0.0.1", "testserver"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class ChatWebSocketTests(TransactionTestCase):
    """
    WebSocket and real-time push tests for chat messages.
    """

    def setUp(self):
        cache.clear()
        self.poster = User.objects.create_user(
            email="ws_poster@example.com",
            password="Password123!",
            full_name="WS Poster",
            role="provider",
            is_verified=True,
        )
        self.applicant = User.objects.create_user(
            email="ws_applicant@example.com",
            password="Password123!",
            full_name="WS Applicant",
            role="student",
            is_verified=True,
        )
        self.third_party = User.objects.create_user(
            email="ws_third@example.com",
            password="Password123!",
            full_name="WS Third Party",
            role="student",
            is_verified=True,
        )

        self.opp = Opportunity.objects.create(
            poster=self.poster,
            title="Realtime Opp",
            description="Realtime testing",
            category=Opportunity.Category.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.STIPEND,
            status=Opportunity.Status.OPEN,
            deadline=timezone.now().date() + timedelta(days=30),
        )
        self.app = Application.objects.create(
            applicant=self.applicant,
            opportunity=self.opp,
            status="applied",
        )
        self.conv = Conversation.objects.create(
            user_one=min(self.applicant, self.poster, key=lambda u: u.id),
            user_two=max(self.applicant, self.poster, key=lambda u: u.id),
            application=self.app,
            opportunity=self.opp,
        )

        self.token_poster = str(RefreshToken.for_user(self.poster).access_token)
        self.token_applicant = str(RefreshToken.for_user(self.applicant).access_token)
        self.token_third = str(RefreshToken.for_user(self.third_party).access_token)

    async def test_recipient_receives_chat_message_sender_and_third_party_do_not(self):
        # Connect applicant (recipient), poster (sender), and third party
        comm_applicant = WebsocketCommunicator(inner_application, f"/ws/notifications/?token={self.token_applicant}")
        comm_poster = WebsocketCommunicator(inner_application, f"/ws/notifications/?token={self.token_poster}")
        comm_third = WebsocketCommunicator(inner_application, f"/ws/notifications/?token={self.token_third}")

        self.assertTrue((await comm_applicant.connect())[0])
        self.assertTrue((await comm_poster.connect())[0])
        self.assertTrue((await comm_third.connect())[0])

        # Poster sends a message via HTTP POST
        def _post_message():
            from rest_framework.test import APIClient
            client = APIClient()
            client.force_authenticate(user=self.poster)
            return client.post(f"/api/chat/conversations/{self.conv.id}/messages/", {"body": "Realtime Hello"})

        res = await sync_to_async(_post_message)()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Applicant receives the chat_message event (may also receive notification event for first message)
        received_chat = None
        for _ in range(3):
            try:
                event = await comm_applicant.receive_json_from(timeout=1.0)
                if event.get("type") == "chat_message":
                    received_chat = event
                    break
            except Exception:
                break

        self.assertIsNotNone(received_chat, "Recipient did not receive chat_message event")
        self.assertEqual(received_chat["type"], "chat_message")
        msg_data = received_chat["message"]
        self.assertEqual(msg_data["conversation_id"], self.conv.id)
        self.assertEqual(msg_data["body"], "Realtime Hello")
        self.assertEqual(msg_data["sender"]["id"], self.poster.id)
        self.assertEqual(msg_data["sender"]["full_name"], "WS Poster")
        self.assertIs(msg_data.get("is_mine"), False)
        self.assertIs(msg_data.get("is_deleted"), False)

        # Verify privacy: no email, phone, or address in websocket payload
        ws_json = json.dumps(received_chat)
        self.assertNotIn("email", ws_json)
        self.assertNotIn("phone", ws_json)
        self.assertNotIn("address", ws_json)
        self.assertNotIn("ws_poster@example.com", ws_json)

        # Sender (poster) receives NOTHING on their socket
        self.assertTrue(await comm_poster.receive_nothing(timeout=0.5))

        # Third party receives NOTHING on their socket
        self.assertTrue(await comm_third.receive_nothing(timeout=0.5))

        await comm_applicant.disconnect()
        await comm_poster.disconnect()
        await comm_third.disconnect()

    async def test_websocket_new_chat_message_payload_fields_and_privacy(self):
        """
        Verify WebSocket payload for a NEW chat message has:
        - is_mine == False
        - is_deleted == False
        - Contains no email, phone, or address in any field
        """
        comm_applicant = WebsocketCommunicator(inner_application, f"/ws/notifications/?token={self.token_applicant}")
        connected, _ = await comm_applicant.connect()
        self.assertTrue(connected)

        def _post_message():
            from rest_framework.test import APIClient
            client = APIClient()
            client.force_authenticate(user=self.poster)
            return client.post(
                f"/api/chat/conversations/{self.conv.id}/messages/",
                {"body": "Hello payload test"},
            )

        res = await sync_to_async(_post_message)()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        received_chat = None
        for _ in range(3):
            try:
                event = await comm_applicant.receive_json_from(timeout=1.0)
                if event.get("type") == "chat_message":
                    received_chat = event
                    break
            except Exception:
                break

        self.assertIsNotNone(received_chat, "Recipient did not receive chat_message event")
        self.assertEqual(received_chat["type"], "chat_message")
        msg_data = received_chat["message"]
        self.assertIs(msg_data.get("is_mine"), False)
        self.assertIs(msg_data.get("is_deleted"), False)

        payload_str = json.dumps(received_chat).lower()
        self.assertNotIn("email", payload_str)
        self.assertNotIn("phone", payload_str)
        self.assertNotIn("address", payload_str)
        self.assertNotIn(self.poster.email.lower(), payload_str)

        await comm_applicant.disconnect()

    def test_channel_layer_failure_does_not_break_saving_or_response(self):
        with patch("apps.chat.views.get_channel_layer") as mock_layer:
            mock_layer.side_effect = Exception("Channel layer is down!")

            from rest_framework.test import APIClient
            client = APIClient()
            client.force_authenticate(user=self.applicant)
            res = client.post(f"/api/chat/conversations/{self.conv.id}/messages/", {"body": "Fault tolerant message"})
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            self.assertEqual(res.data["body"], "Fault tolerant message")
            self.assertTrue(Message.objects.filter(body="Fault tolerant message").exists())

    async def test_first_message_notification_ws_payload_has_no_email(self):
        comm_applicant = WebsocketCommunicator(inner_application, f"/ws/notifications/?token={self.token_applicant}")
        connected, _ = await comm_applicant.connect()
        self.assertTrue(connected)

        def _post_message():
            from rest_framework.test import APIClient
            client = APIClient()
            client.force_authenticate(user=self.poster)
            return client.post(
                f"/api/chat/conversations/{self.conv.id}/messages/",
                {"body": "First message for WS notification test"},
            )

        res = await sync_to_async(_post_message)()
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        received_notif = None
        for _ in range(3):
            try:
                event = await comm_applicant.receive_json_from(timeout=1.0)
                if event.get("type") == "notification":
                    received_notif = event
                    break
            except Exception:
                break

        self.assertIsNotNone(received_notif, "Recipient did not receive notification event over WebSocket")
        self.assertEqual(received_notif["type"], "notification")
        notif_data = received_notif["notification"]
        self.assertEqual(notif_data["notification_type"], "new_chat_message")
        self.assertIsNone(notif_data.get("actor"))

        # Assert no email address and no "@" in the entire notification event JSON
        ws_notif_json = json.dumps(received_notif)
        self.assertNotIn("email", ws_notif_json)
        self.assertNotIn("@", ws_notif_json)
        self.assertNotIn(self.poster.email, ws_notif_json)
        self.assertNotIn(self.applicant.email, ws_notif_json)

        await comm_applicant.disconnect()


class ChatPhase2ModelTests(TestCase):
    """
    Model tests for Conversation.is_direct, partial constraints, and delete behaviors.
    """

    def setUp(self):
        self.student_a = User.objects.create_user(
            email="phase2_a@example.com",
            password="Password123!",
            full_name="Student A",
            role="student",
            is_verified=True,
        )
        self.student_b = User.objects.create_user(
            email="phase2_b@example.com",
            password="Password123!",
            full_name="Student B",
            role="student",
            is_verified=True,
        )

    def test_is_direct_defaults_to_false(self):
        conv = Conversation.objects.create(
            user_one=self.student_a,
            user_two=self.student_b,
        )
        self.assertFalse(conv.is_direct)

    def test_unique_direct_conversation_per_pair_constraint(self):
        conv1 = Conversation.objects.create(
            user_one=self.student_a,
            user_two=self.student_b,
            is_direct=True,
        )
        self.assertTrue(conv1.is_direct)

        with self.assertRaises(IntegrityError):
            Conversation.objects.create(
                user_one=self.student_a,
                user_two=self.student_b,
                is_direct=True,
            )

    def test_delete_application_or_opportunity_with_two_conversations_does_not_raise(self):
        # Create 2 opportunities and 2 applications between student A and student B
        opp1 = Opportunity.objects.create(
            poster=self.student_a,
            title="Opp 1",
            description="Description 1",
        )
        app1 = Application.objects.create(
            opportunity=opp1,
            applicant=self.student_b,
            status=Application.Status.APPLIED,
        )
        conv1 = Conversation.objects.create(
            user_one=self.student_a,
            user_two=self.student_b,
            application=app1,
            opportunity=opp1,
            is_direct=False,
        )

        opp2 = Opportunity.objects.create(
            poster=self.student_a,
            title="Opp 2",
            description="Description 2",
        )
        app2 = Application.objects.create(
            opportunity=opp2,
            applicant=self.student_b,
            status=Application.Status.APPLIED,
        )
        conv2 = Conversation.objects.create(
            user_one=self.student_a,
            user_two=self.student_b,
            application=app2,
            opportunity=opp2,
            is_direct=False,
        )

        # Deleting applications sets application=NULL on both conversations without violating constraints
        app1.delete()
        app2.delete()

        conv1.refresh_from_db()
        conv2.refresh_from_db()
        self.assertIsNone(conv1.application)
        self.assertIsNone(conv2.application)
        self.assertFalse(conv1.is_direct)
        self.assertFalse(conv2.is_direct)

        # Deleting opportunities sets opportunity=NULL on both conversations
        opp1.delete()
        opp2.delete()

        conv1.refresh_from_db()
        conv2.refresh_from_db()
        self.assertIsNone(conv1.opportunity)
        self.assertIsNone(conv2.opportunity)

        # Creating a direct conversation between the same pair succeeds without error
        direct_conv = Conversation.objects.create(
            user_one=self.student_a,
            user_two=self.student_b,
            is_direct=True,
        )
        self.assertTrue(direct_conv.is_direct)

        # Pair now has 3 conversations total: 2 historical orphaned and 1 direct
        u1, u2 = (self.student_a, self.student_b) if self.student_a.id < self.student_b.id else (self.student_b, self.student_a)
        total_convs = Conversation.objects.filter(user_one=u1, user_two=u2).count()
        self.assertEqual(total_convs, 3)

    def test_duplicate_pending_message_request_raises_integrity_error(self):
        MessageRequest.objects.create(
            sender=self.student_a,
            receiver=self.student_b,
            status=MessageRequest.Status.PENDING,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            MessageRequest.objects.create(
                sender=self.student_a,
                receiver=self.student_b,
                status=MessageRequest.Status.PENDING,
            )


class ChatMessageRequestAPITests(APITestCase):
    """
    API tests for student-to-student message requests.
    """

    def setUp(self):
        cache.clear()

        # Sender student
        self.student1 = User.objects.create_user(
            email="s1_req@example.com",
            password="Password123!",
            full_name="Student One",
            role="student",
            is_verified=True,
        )
        StudentProfile.objects.create(user=self.student1, is_discoverable=True)

        # Receiver student
        self.student2 = User.objects.create_user(
            email="s2_req@example.com",
            password="Password123!",
            full_name="Student Two",
            role="student",
            is_verified=True,
        )
        StudentProfile.objects.create(user=self.student2, is_discoverable=True)

        # Third student
        self.student3 = User.objects.create_user(
            email="s3_req@example.com",
            password="Password123!",
            full_name="Student Three",
            role="student",
            is_verified=True,
        )
        StudentProfile.objects.create(user=self.student3, is_discoverable=True)

        # Hidden student (is_discoverable=False)
        self.hidden_student = User.objects.create_user(
            email="hidden_req@example.com",
            password="Password123!",
            full_name="Hidden Student",
            role="student",
            is_verified=True,
        )
        StudentProfile.objects.create(user=self.hidden_student, is_discoverable=False)

        # Unverified student
        self.unverified_student = User.objects.create_user(
            email="unverified_req@example.com",
            password="Password123!",
            full_name="Unverified Student",
            role="student",
            is_verified=False,
        )
        StudentProfile.objects.create(user=self.unverified_student, is_discoverable=True)

        # Inactive student
        self.inactive_student = User.objects.create_user(
            email="inactive_req@example.com",
            password="Password123!",
            full_name="Inactive Student",
            role="student",
            is_verified=True,
            is_active=False,
        )
        StudentProfile.objects.create(user=self.inactive_student, is_discoverable=True)

        # Provider user
        self.provider = User.objects.create_user(
            email="provider_req@example.com",
            password="Password123!",
            full_name="Provider User",
            role="provider",
            is_verified=True,
        )

        self.client.force_authenticate(user=self.student1)

    def test_create_request_success(self):
        res = self.client.post(
            "/api/chat/requests/",
            {"receiver_id": self.student2.id, "intro": "Hello there! Would love to connect."},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["receiver"]["id"], self.student2.id)
        self.assertEqual(res.data["receiver"]["full_name"], "Student Two")
        self.assertNotIn("email", res.data["receiver"])
        self.assertEqual(res.data["intro"], "Hello there! Would love to connect.")
        self.assertEqual(res.data["status"], "pending")
        self.assertNotIn("declined_at", res.data)

        # Verify DB
        req = MessageRequest.objects.get(id=res.data["id"])
        self.assertEqual(req.status, MessageRequest.Status.PENDING)
        self.assertEqual(req.sender, self.student1)
        self.assertEqual(req.receiver, self.student2)

        # Verify notification
        notif = Notification.objects.filter(
            recipient=self.student2,
            notification_type=Notification.NotificationType.CHAT_REQUEST_RECEIVED,
        ).first()
        self.assertIsNotNone(notif)
        self.assertIsNone(notif.actor)
        self.assertNotIn("connect", notif.message)
        self.assertIn("Student One", notif.message)

    def test_create_request_notification_failure_swallowed(self):
        with patch("apps.chat.views.create_notification", side_effect=Exception("Notification service failure")):
            res = self.client.post(
                "/api/chat/requests/",
                {"receiver_id": self.student3.id, "intro": "Resilient intro"},
            )
            self.assertEqual(res.status_code, status.HTTP_201_CREATED)
            self.assertTrue(
                MessageRequest.objects.filter(
                    sender=self.student1,
                    receiver=self.student3,
                    status=MessageRequest.Status.PENDING,
                ).exists()
            )

    def test_create_request_role_and_verification_checks(self):
        # Provider cannot send message request
        self.client.force_authenticate(user=self.provider)
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["detail"], "Only students can send message requests.")

        # Unverified student cannot send message request
        self.client.force_authenticate(user=self.unverified_student)
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(res.data["detail"], "You must verify your email to send message requests.")

    def test_create_request_receiver_lookup_first(self):
        # Hidden receiver returns 404
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.hidden_student.id})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["detail"], "User not found.")

        # Inactive receiver returns 404
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.inactive_student.id})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["detail"], "User not found.")

        # Unverified receiver returns 404
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.unverified_student.id})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["detail"], "User not found.")

        # Provider receiver returns 404
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.provider.id})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["detail"], "User not found.")

        # Non-existent receiver returns 404
        res = self.client.post("/api/chat/requests/", {"receiver_id": 999999})
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(res.data["detail"], "User not found.")

    def test_create_request_self_request_returns_400(self):
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student1.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["detail"], "You cannot send a message request to yourself.")

    def test_create_request_active_conversation_blocks(self):
        # 1. Direct conversation blocks
        direct_conv = Conversation.objects.create(
            user_one=self.student1,
            user_two=self.student2,
            is_direct=True,
        )
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["detail"], "You already have an active conversation with this user.")
        self.assertEqual(res.data["conversation_id"], direct_conv.id)
        direct_conv.delete()

        # 2. Application-based conversation blocks
        opp = Opportunity.objects.create(poster=self.student1, title="Test Opp", description="Desc")
        app = Application.objects.create(opportunity=opp, applicant=self.student2, status=Application.Status.APPLIED)
        app_conv = Conversation.objects.create(
            user_one=self.student1,
            user_two=self.student2,
            application=app,
            opportunity=opp,
            is_direct=False,
        )
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["conversation_id"], app_conv.id)

        # 3. Orphaned conversation blocks
        app.delete()
        app_conv.refresh_from_db()
        self.assertIsNone(app_conv.application)
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["conversation_id"], app_conv.id)
        app_conv.delete()

        # 4. Withdrawn application conversation does NOT block
        app_w = Application.objects.create(opportunity=opp, applicant=self.student2, status=Application.Status.WITHDRAWN)
        withdrawn_conv = Conversation.objects.create(
            user_one=self.student1,
            user_two=self.student2,
            application=app_w,
            opportunity=opp,
            is_direct=False,
        )
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_request_duplicate_pending_returns_400(self):
        res1 = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res2.data["detail"], "A pending request already exists for this user.")

    def test_create_request_duplicate_pending_integrity_error_handled(self):
        with patch.object(MessageRequest.objects, "create", side_effect=IntegrityError("duplicate pending")):
            res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(res.data["detail"], "A pending request already exists for this user.")

    def test_create_request_reverse_pending_returns_400_with_request_id(self):
        reverse_req = MessageRequest.objects.create(
            sender=self.student2,
            receiver=self.student1,
            status=MessageRequest.Status.PENDING,
        )
        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["detail"], "This user has already sent you a request.")
        self.assertEqual(res.data["request_id"], reverse_req.id)

    def test_create_request_daily_limit_counts_cancelled(self):
        # Create 10 requests in all statuses including cancelled
        for i in range(10):
            stat = MessageRequest.Status.CANCELLED if i % 2 == 0 else MessageRequest.Status.DECLINED
            MessageRequest.objects.create(
                sender=self.student1,
                receiver=self.student3,
                status=stat,
            )

        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["detail"], "Daily request limit reached. Please try again tomorrow.")

        # Move one request to 25 hours ago
        old_req = MessageRequest.objects.filter(sender=self.student1).first()
        old_req.created_at = timezone.now() - timedelta(hours=25)
        old_req.save(update_fields=["created_at"])

        res_ok = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

    def test_create_request_cooldown_after_decline(self):
        # Request declined 3 days ago (< 7 days)
        MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            status=MessageRequest.Status.DECLINED,
            declined_at=timezone.now() - timedelta(days=3),
        )

        res = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # Must return generic message without mentioning decline or dates
        self.assertEqual(res.data["detail"], "You can't send a request to this user right now.")
        self.assertNotIn("decline", res.data["detail"].lower())
        self.assertNotIn("day", res.data["detail"].lower())

        # Update decline to 8 days ago (> 7 days)
        MessageRequest.objects.filter(sender=self.student1, receiver=self.student2).update(
            declined_at=timezone.now() - timedelta(days=8)
        )
        res_ok = self.client.post("/api/chat/requests/", {"receiver_id": self.student2.id})
        self.assertEqual(res_ok.status_code, status.HTTP_201_CREATED)

    def test_no_declined_at_in_any_response(self):
        MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            status=MessageRequest.Status.DECLINED,
            declined_at=timezone.now() - timedelta(days=10),
        )

        # Outgoing list
        res_out = self.client.get("/api/chat/requests/outgoing/")
        self.assertEqual(res_out.status_code, status.HTTP_200_OK)
        results = res_out.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "declined")
        self.assertNotIn("declined_at", results[0])
        self.assertNotIn("declined_at", json.dumps(res_out.data))

        # Incoming list
        self.client.force_authenticate(user=self.student2)
        res_in = self.client.get("/api/chat/requests/incoming/")
        self.assertEqual(res_in.status_code, status.HTTP_200_OK)
        self.assertNotIn("declined_at", json.dumps(res_in.data))

    def test_incoming_list_shows_pending_only_and_hides_inactive_senders(self):
        # 1. Pending from active Student 1
        req1 = MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            intro="Active sender intro",
            status=MessageRequest.Status.PENDING,
        )
        # 2. Declined from Student 3
        MessageRequest.objects.create(
            sender=self.student3,
            receiver=self.student2,
            intro="Declined intro",
            status=MessageRequest.Status.DECLINED,
        )
        # 3. Pending from Inactive Student
        MessageRequest.objects.create(
            sender=self.inactive_student,
            receiver=self.student2,
            intro="Inactive sender intro",
            status=MessageRequest.Status.PENDING,
        )

        self.client.force_authenticate(user=self.student2)
        res = self.client.get("/api/chat/requests/incoming/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], req1.id)
        self.assertEqual(results[0]["intro"], "Active sender intro")
        self.assertEqual(results[0]["sender"]["id"], self.student1.id)
        self.assertEqual(results[0]["sender"]["full_name"], "Student One")
        self.assertNotIn("email", results[0]["sender"])

    def test_outgoing_list_shows_all_user_requests(self):
        MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            intro="Intro 1",
            status=MessageRequest.Status.PENDING,
        )
        MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student3,
            intro="Intro 2",
            status=MessageRequest.Status.CANCELLED,
        )

        res = self.client.get("/api/chat/requests/outgoing/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data["results"]
        self.assertEqual(len(results), 2)
        statuses = {r["status"] for r in results}
        self.assertEqual(statuses, {"pending", "cancelled"})

    def test_accept_request_success_and_closes_opposite(self):
        # Student 1 -> Student 2 pending
        req1 = MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            intro="Req 1",
            status=MessageRequest.Status.PENDING,
        )
        # Student 2 -> Student 1 pending (opposite direction)
        req2 = MessageRequest.objects.create(
            sender=self.student2,
            receiver=self.student1,
            intro="Req 2",
            status=MessageRequest.Status.PENDING,
        )

        self.client.force_authenticate(user=self.student2)
        res = self.client.post(f"/api/chat/requests/{req1.id}/accept/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["detail"], "Request accepted.")
        conv_id = res.data["conversation_id"]
        self.assertIsNotNone(conv_id)

        # Direct conversation created with is_direct=True
        conv = Conversation.objects.get(id=conv_id)
        self.assertTrue(conv.is_direct)

        # Both requests are marked accepted with the same conversation
        req1.refresh_from_db()
        req2.refresh_from_db()
        self.assertEqual(req1.status, MessageRequest.Status.ACCEPTED)
        self.assertEqual(req1.conversation, conv)
        self.assertEqual(req2.status, MessageRequest.Status.ACCEPTED)
        self.assertEqual(req2.conversation, conv)

        # Notification created for sender (student1)
        notif = Notification.objects.filter(
            recipient=self.student1,
            notification_type=Notification.NotificationType.CHAT_REQUEST_ACCEPTED,
        ).first()
        self.assertIsNotNone(notif)
        self.assertIsNone(notif.actor)
        self.assertIn("Student Two accepted", notif.message)

    def test_accept_request_idempotent(self):
        req = MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            status=MessageRequest.Status.PENDING,
        )
        self.client.force_authenticate(user=self.student2)
        res1 = self.client.post(f"/api/chat/requests/{req.id}/accept/")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        conv_id = res1.data["conversation_id"]

        # Call accept again
        res2 = self.client.post(f"/api/chat/requests/{req.id}/accept/")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["detail"], "Request already accepted.")
        self.assertEqual(res2.data["conversation_id"], conv_id)

    def test_accept_request_inactive_or_unverified_sender_returns_400(self):
        req = MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            status=MessageRequest.Status.PENDING,
        )
        # Deactivate sender
        self.student1.is_active = False
        self.student1.save(update_fields=["is_active"])

        self.client.force_authenticate(user=self.student2)
        res = self.client.post(f"/api/chat/requests/{req.id}/accept/")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.data["detail"], "Sender is no longer eligible for chat.")

    def test_accept_request_permissions_and_non_pending(self):
        req = MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            status=MessageRequest.Status.PENDING,
        )
        # Sender cannot accept
        res_sender = self.client.post(f"/api/chat/requests/{req.id}/accept/")
        self.assertEqual(res_sender.status_code, status.HTTP_404_NOT_FOUND)

        # Third party cannot accept
        self.client.force_authenticate(user=self.student3)
        res_third = self.client.post(f"/api/chat/requests/{req.id}/accept/")
        self.assertEqual(res_third.status_code, status.HTTP_404_NOT_FOUND)

        # Non-pending request cannot be accepted
        req.status = MessageRequest.Status.DECLINED
        req.save(update_fields=["status"])
        self.client.force_authenticate(user=self.student2)
        res_non_pending = self.client.post(f"/api/chat/requests/{req.id}/accept/")
        self.assertEqual(res_non_pending.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res_non_pending.data["detail"], "Only pending requests can be accepted.")

    def test_decline_request_success_idempotent_no_notification(self):
        req = MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            status=MessageRequest.Status.PENDING,
        )
        self.client.force_authenticate(user=self.student2)
        res = self.client.post(f"/api/chat/requests/{req.id}/decline/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["detail"], "Request declined.")

        req.refresh_from_db()
        self.assertEqual(req.status, MessageRequest.Status.DECLINED)
        self.assertIsNotNone(req.declined_at)

        # Idempotent decline
        res_idem = self.client.post(f"/api/chat/requests/{req.id}/decline/")
        self.assertEqual(res_idem.status_code, status.HTTP_200_OK)
        self.assertEqual(res_idem.data["detail"], "Request already declined.")

        # Decline sends NO notification
        notifs = Notification.objects.filter(recipient=self.student1)
        self.assertEqual(notifs.count(), 0)

        # Sender or third party cannot decline (404)
        self.client.force_authenticate(user=self.student1)
        res_wrong = self.client.post(f"/api/chat/requests/{req.id}/decline/")
        self.assertEqual(res_wrong.status_code, status.HTTP_404_NOT_FOUND)

    def test_cancel_request_success_idempotent(self):
        req = MessageRequest.objects.create(
            sender=self.student1,
            receiver=self.student2,
            status=MessageRequest.Status.PENDING,
        )
        res = self.client.post(f"/api/chat/requests/{req.id}/cancel/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["detail"], "Request cancelled.")

        req.refresh_from_db()
        self.assertEqual(req.status, MessageRequest.Status.CANCELLED)

        # Idempotent cancel
        res_idem = self.client.post(f"/api/chat/requests/{req.id}/cancel/")
        self.assertEqual(res_idem.status_code, status.HTTP_200_OK)
        self.assertEqual(res_idem.data["detail"], "Request already cancelled.")

        # Receiver cannot cancel (404)
        self.client.force_authenticate(user=self.student2)
        res_receiver = self.client.post(f"/api/chat/requests/{req.id}/cancel/")
        self.assertEqual(res_receiver.status_code, status.HTTP_404_NOT_FOUND)

    def test_throttle_scopes_and_settings(self):
        from apps.chat.views import (
            ChatRequestAcceptView,
            ChatRequestCancelView,
            ChatRequestCreateView,
            ChatRequestDeclineView,
            ChatRequestIncomingListView,
            ChatRequestOutgoingListView,
        )
        from django.conf import settings

        self.assertEqual(ChatRequestCreateView.throttle_scope, "chat_request_action")
        self.assertEqual(ChatRequestAcceptView.throttle_scope, "chat_request_action")
        self.assertEqual(ChatRequestDeclineView.throttle_scope, "chat_request_action")
        self.assertEqual(ChatRequestCancelView.throttle_scope, "chat_request_action")
        self.assertEqual(ChatRequestIncomingListView.throttle_scope, "chat_general")
        self.assertEqual(ChatRequestOutgoingListView.throttle_scope, "chat_general")

        self.assertIn("chat_request_action", settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"])
        self.assertEqual(settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["chat_request_action"], "30/hour")
        self.assertEqual(settings.CHAT_REQUEST_DAILY_LIMIT, 10)
        self.assertEqual(settings.CHAT_REQUEST_DECLINE_COOLDOWN_DAYS, 7)


import io
from django.core.management import call_command


class ChatOneConversationPerPairTests(APITestCase):
    """
    Tests for the one-conversation-per-pair cleanup round:
    - Single conversation per pair across multiple applications
    - Pair-level withdrawn messaging rule
    - Empty non-direct conversation hiding in list and detail view
    - Empty direct conversation listing
    - Request accept reuses existing conversation and sets is_direct
    - merge_duplicate_conversations management command
    - Concurrency / race handling
    """

    def setUp(self):
        cache.clear()

        self.student_a = User.objects.create_user(
            email="clean_student_a@example.com",
            password="Password123!",
            full_name="Student Alpha",
            role="student",
            is_verified=True,
        )
        StudentProfile.objects.create(user=self.student_a, is_discoverable=True)

        self.student_b = User.objects.create_user(
            email="clean_student_b@example.com",
            password="Password123!",
            full_name="Student Beta",
            role="student",
            is_verified=True,
        )
        StudentProfile.objects.create(user=self.student_b, is_discoverable=True)

        self.provider = User.objects.create_user(
            email="clean_provider@example.com",
            password="Password123!",
            full_name="Provider Gamma",
            role="provider",
            is_verified=True,
        )

        self.third_party = User.objects.create_user(
            email="clean_third_party@example.com",
            password="Password123!",
            full_name="Third Party",
            role="student",
            is_verified=True,
        )

        self.opp1 = Opportunity.objects.create(
            poster=self.provider,
            title="Clean Opp 1",
            description="Opportunity 1",
            category=Opportunity.Category.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.STIPEND,
            status=Opportunity.Status.OPEN,
            deadline=timezone.now().date() + timedelta(days=30),
        )

        self.opp2 = Opportunity.objects.create(
            poster=self.provider,
            title="Clean Opp 2",
            description="Opportunity 2",
            category=Opportunity.Category.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.STIPEND,
            status=Opportunity.Status.OPEN,
            deadline=timezone.now().date() + timedelta(days=30),
        )

        self.app1 = Application.objects.create(
            applicant=self.student_a,
            opportunity=self.opp1,
            status=Application.Status.APPLIED,
        )

        self.app2 = Application.objects.create(
            applicant=self.student_a,
            opportunity=self.opp2,
            status=Application.Status.APPLIED,
        )

    def test_second_application_same_pair_returns_same_conversation(self):
        # 1. Student A starts conversation via application 1
        self.client.force_authenticate(user=self.student_a)
        res1 = self.client.post("/api/chat/conversations/", {"application_id": self.app1.id})
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        conv1_id = res1.data["id"]

        # 2. Student A calls POST with application 2 -> returns the same conversation (200 OK)
        res2 = self.client.post("/api/chat/conversations/", {"application_id": self.app2.id})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["id"], conv1_id)

        # 3. Provider calls POST with application 2 -> returns the same conversation (200 OK)
        self.client.force_authenticate(user=self.provider)
        res3 = self.client.post("/api/chat/conversations/", {"application_id": self.app2.id})
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertEqual(res3.data["id"], conv1_id)

        # Provider calls POST with application 1 -> returns the same conversation (200 OK)
        res4 = self.client.post("/api/chat/conversations/", {"application_id": self.app1.id})
        self.assertEqual(res4.status_code, status.HTTP_200_OK)
        self.assertEqual(res4.data["id"], conv1_id)

        # Total conversations between this pair is strictly 1
        u1, u2 = (self.student_a, self.provider) if self.student_a.id < self.provider.id else (self.provider, self.student_a)
        self.assertEqual(Conversation.objects.filter(user_one=u1, user_two=u2).count(), 1)

    def test_withdrawn_first_application_with_active_second_allows_messaging(self):
        # Create conversation tied to app1
        u1, u2 = (self.student_a, self.provider) if self.student_a.id < self.provider.id else (self.provider, self.student_a)
        conv = Conversation.objects.create(
            user_one=u1,
            user_two=u2,
            application=self.app1,
            opportunity=self.opp1,
            is_direct=False,
        )

        # Mark app1 as withdrawn, but app2 remains active ('applied')
        self.app1.status = Application.Status.WITHDRAWN
        self.app1.save(update_fields=["status"])

        self.client.force_authenticate(user=self.student_a)
        res = self.client.post(
            f"/api/chat/conversations/{conv.id}/messages/",
            {"body": "Active message because second app exists"},
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_all_applications_withdrawn_blocks_sending(self):
        u1, u2 = (self.student_a, self.provider) if self.student_a.id < self.provider.id else (self.provider, self.student_a)
        conv = Conversation.objects.create(
            user_one=u1,
            user_two=u2,
            application=self.app1,
            opportunity=self.opp1,
            is_direct=False,
        )
        Message.objects.create(conversation=conv, sender=self.student_a, body="Initial message")

        # Withdraw all applications between the pair
        self.app1.status = Application.Status.WITHDRAWN
        self.app1.save(update_fields=["status"])
        self.app2.status = Application.Status.WITHDRAWN
        self.app2.save(update_fields=["status"])

        self.client.force_authenticate(user=self.student_a)

        # Sending is blocked
        res_send = self.client.post(
            f"/api/chat/conversations/{conv.id}/messages/",
            {"body": "Blocked message"},
        )
        self.assertEqual(res_send.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("withdrawn", res_send.data["detail"].lower())

        # History is still readable
        res_read = self.client.get(f"/api/chat/conversations/{conv.id}/messages/")
        self.assertEqual(res_read.status_code, status.HTTP_200_OK)

    def test_direct_and_orphaned_conversations_never_blocked(self):
        # 1. Direct conversation: all applications between pair withdrawn, sending still allowed
        u1, u2 = (self.student_a, self.student_b) if self.student_a.id < self.student_b.id else (self.student_b, self.student_a)
        direct_conv = Conversation.objects.create(
            user_one=u1,
            user_two=u2,
            is_direct=True,
        )
        student_opp = Opportunity.objects.create(poster=self.student_b, title="Student Opp", description="Desc")
        student_app = Application.objects.create(
            applicant=self.student_a,
            opportunity=student_opp,
            status=Application.Status.WITHDRAWN,
        )

        self.client.force_authenticate(user=self.student_a)
        res_direct = self.client.post(
            f"/api/chat/conversations/{direct_conv.id}/messages/",
            {"body": "Direct message allowed"},
        )
        self.assertEqual(res_direct.status_code, status.HTTP_201_CREATED)

        # 2. Orphaned conversation: 0 applications between pair, sending allowed
        student_app.delete()
        student_opp.delete()
        res_orphaned = self.client.post(
            f"/api/chat/conversations/{direct_conv.id}/messages/",
            {"body": "Orphaned message allowed"},
        )
        self.assertEqual(res_orphaned.status_code, status.HTTP_201_CREATED)

    def test_empty_non_direct_conversations_hidden_from_list_but_open_by_id(self):
        u1, u2 = (self.student_a, self.provider) if self.student_a.id < self.provider.id else (self.provider, self.student_a)
        empty_conv = Conversation.objects.create(
            user_one=u1,
            user_two=u2,
            application=self.app1,
            opportunity=self.opp1,
            is_direct=False,
        )

        self.client.force_authenticate(user=self.student_a)

        # GET /api/chat/conversations/ list does NOT include empty non-direct conversation
        res_list = self.client.get("/api/chat/conversations/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        results = res_list.data.get("results", res_list.data)
        self.assertEqual(len(results), 0)

        # GET /api/chat/conversations/<id>/ returns 200 with matching serializer fields
        res_detail = self.client.get(f"/api/chat/conversations/{empty_conv.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data["id"], empty_conv.id)
        self.assertEqual(res_detail.data["opportunity"]["id"], self.opp1.id)
        self.assertEqual(res_detail.data["unread_count"], 0)
        self.assertEqual(res_detail.data["last_message_preview"], "")

        # Detail endpoint returns 404 for non-participants
        self.client.force_authenticate(user=self.third_party)
        res_third = self.client.get(f"/api/chat/conversations/{empty_conv.id}/")
        self.assertEqual(res_third.status_code, status.HTTP_404_NOT_FOUND)

        # Detail endpoint returns 404 for non-existent conversation
        self.client.force_authenticate(user=self.student_a)
        res_nonexistent = self.client.get("/api/chat/conversations/999999/")
        self.assertEqual(res_nonexistent.status_code, status.HTTP_404_NOT_FOUND)

    def test_empty_direct_conversations_are_listed(self):
        u1, u2 = (self.student_a, self.student_b) if self.student_a.id < self.student_b.id else (self.student_b, self.student_a)
        direct_conv = Conversation.objects.create(
            user_one=u1,
            user_two=u2,
            is_direct=True,
        )

        self.client.force_authenticate(user=self.student_a)
        res_list = self.client.get("/api/chat/conversations/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        results = res_list.data.get("results", res_list.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], direct_conv.id)

    def test_accept_request_reuses_existing_withdrawn_app_conv_and_sets_is_direct(self):
        u1, u2 = (self.student_a, self.student_b) if self.student_a.id < self.student_b.id else (self.student_b, self.student_a)
        student_opp = Opportunity.objects.create(poster=self.student_b, title="Student Opp", description="Desc")
        student_app = Application.objects.create(
            applicant=self.student_a,
            opportunity=student_opp,
            status=Application.Status.WITHDRAWN,
        )
        existing_conv = Conversation.objects.create(
            user_one=u1,
            user_two=u2,
            application=student_app,
            opportunity=student_opp,
            is_direct=False,
        )

        # Student A sends message request to Student B
        self.client.force_authenticate(user=self.student_a)
        res_req = self.client.post("/api/chat/requests/", {"receiver_id": self.student_b.id})
        self.assertEqual(res_req.status_code, status.HTTP_201_CREATED)
        req_id = res_req.data["id"]

        # Student B accepts request
        self.client.force_authenticate(user=self.student_b)
        res_accept = self.client.post(f"/api/chat/requests/{req_id}/accept/")
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)
        self.assertEqual(res_accept.data["conversation_id"], existing_conv.id)

        # Conversation is reused and set to is_direct=True
        existing_conv.refresh_from_db()
        self.assertTrue(existing_conv.is_direct)
        self.assertEqual(Conversation.objects.filter(user_one=u1, user_two=u2).count(), 1)

    def test_request_creation_allowed_when_pair_messaging_blocked_and_blocked_when_active(self):
        u1, u2 = (self.student_a, self.student_b) if self.student_a.id < self.student_b.id else (self.student_b, self.student_a)
        student_opp = Opportunity.objects.create(poster=self.student_b, title="Student Opp", description="Desc")
        student_app = Application.objects.create(
            applicant=self.student_a,
            opportunity=student_opp,
            status=Application.Status.WITHDRAWN,
        )
        blocked_conv = Conversation.objects.create(
            user_one=u1,
            user_two=u2,
            application=student_app,
            opportunity=student_opp,
            is_direct=False,
        )

        self.client.force_authenticate(user=self.student_a)

        # When messaging is blocked by pair withdrawn rule, request creation is ALLOWED
        res1 = self.client.post("/api/chat/requests/", {"receiver_id": self.student_b.id})
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Cancel request
        self.client.post(f"/api/chat/requests/{res1.data['id']}/cancel/")

        # Make conversation direct (active)
        blocked_conv.is_direct = True
        blocked_conv.save(update_fields=["is_direct"])

        # When conversation is active (direct), request creation is BLOCKED
        res2 = self.client.post("/api/chat/requests/", {"receiver_id": self.student_b.id})
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res2.data["conversation_id"], blocked_conv.id)

    def test_merge_duplicate_conversations_command(self):
        u1, u2 = (self.student_a, self.student_b) if self.student_a.id < self.student_b.id else (self.student_b, self.student_a)

        # Create 3 duplicate conversations
        conv1 = Conversation.objects.create(user_one=u1, user_two=u2, is_direct=False)
        conv2 = Conversation.objects.create(user_one=u1, user_two=u2, is_direct=True)
        conv3 = Conversation.objects.create(user_one=u1, user_two=u2, is_direct=False)

        # Messages
        t1 = timezone.now() - timedelta(minutes=10)
        t2 = timezone.now() - timedelta(minutes=5)
        m1 = Message.objects.create(conversation=conv1, sender=self.student_a, body="Msg on conv 1", created_at=t1)
        m2 = Message.objects.create(conversation=conv2, sender=self.student_b, body="Msg on conv 2", created_at=t2)

        # Request pointing to conv3
        req = MessageRequest.objects.create(
            sender=self.student_a,
            receiver=self.student_b,
            status=MessageRequest.Status.ACCEPTED,
            conversation=conv3,
        )

        # 1. DRY-RUN test
        out_dry = io.StringIO()
        call_command("merge_duplicate_conversations", stdout=out_dry)
        output_dry = out_dry.getvalue()
        self.assertIn("DRY-RUN", output_dry)
        self.assertIn(f"Pair ({u1.id}, {u2.id})", output_dry)
        self.assertEqual(Conversation.objects.filter(user_one=u1, user_two=u2).count(), 3)

        # 2. APPLY test
        out_apply = io.StringIO()
        call_command("merge_duplicate_conversations", apply=True, stdout=out_apply)
        output_apply = out_apply.getvalue()
        self.assertIn("Merge completed", output_apply)

        # Verification
        self.assertEqual(Conversation.objects.filter(user_one=u1, user_two=u2).count(), 1)
        kept_conv = Conversation.objects.get(user_one=u1, user_two=u2)
        self.assertEqual(kept_conv.id, conv1.id)
        self.assertTrue(kept_conv.is_direct)  # direct flag preserved from conv2

        # All messages moved to kept_conv
        self.assertEqual(Message.objects.filter(conversation=kept_conv).count(), 2)
        m1.refresh_from_db()
        m2.refresh_from_db()
        self.assertEqual(m1.conversation_id, kept_conv.id)
        self.assertEqual(m2.conversation_id, kept_conv.id)

        # Request repointed to kept_conv
        req.refresh_from_db()
        self.assertEqual(req.conversation_id, kept_conv.id)

        # 3. IDEMPOTENT rerun test
        out_rerun = io.StringIO()
        call_command("merge_duplicate_conversations", apply=True, stdout=out_rerun)
        self.assertIn("No duplicate conversations found.", out_rerun.getvalue())
        self.assertEqual(Conversation.objects.filter(user_one=u1, user_two=u2).count(), 1)



