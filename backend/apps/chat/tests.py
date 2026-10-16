import json
from datetime import timedelta
from unittest.mock import patch

from asgiref.sync import sync_to_async
from channels.layers import get_channel_layer
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.models import Notification
from apps.notifications.routing import websocket_urlpatterns
from apps.opportunities.models import Application, Opportunity
from .models import Conversation, Message

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

        # Verify privacy: no email or phone in websocket payload
        ws_json = json.dumps(received_chat)
        self.assertNotIn("email", ws_json)
        self.assertNotIn("phone", ws_json)
        self.assertNotIn("ws_poster@example.com", ws_json)

        # Sender (poster) receives NOTHING on their socket
        self.assertTrue(await comm_poster.receive_nothing(timeout=0.5))

        # Third party receives NOTHING on their socket
        self.assertTrue(await comm_third.receive_nothing(timeout=0.5))

        await comm_applicant.disconnect()
        await comm_poster.disconnect()
        await comm_third.disconnect()

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

