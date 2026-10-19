import json
from datetime import timedelta
from unittest.mock import patch

from asgiref.sync import sync_to_async
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.routing import websocket_urlpatterns
from apps.opportunities.models import Application, Opportunity
from .models import Conversation, Message

User = get_user_model()
inner_application = URLRouter(websocket_urlpatterns)


class MessageDeleteAndIsMineAPITests(APITestCase):
    def setUp(self):
        cache.clear()

        self.sender = User.objects.create_user(
            email="msg_sender@example.com",
            password="Password123!",
            full_name="Message Sender",
            role="student",
            is_verified=True,
        )
        self.recipient = User.objects.create_user(
            email="msg_recipient@example.com",
            password="Password123!",
            full_name="Message Recipient",
            role="provider",
            is_verified=True,
        )
        self.third_party = User.objects.create_user(
            email="third_party_del@example.com",
            password="Password123!",
            full_name="Third Party Del",
            role="student",
            is_verified=True,
        )

        self.opp = Opportunity.objects.create(
            poster=self.recipient,
            title="Design Intern",
            description="UI/UX intern",
            category=Opportunity.Category.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.STIPEND,
            status=Opportunity.Status.OPEN,
            deadline=timezone.now().date() + timedelta(days=30),
        )
        self.app = Application.objects.create(
            applicant=self.sender,
            opportunity=self.opp,
            status="applied",
            cover_note="Excited to apply",
        )
        self.conv = Conversation.objects.create(
            user_one=min(self.sender, self.recipient, key=lambda u: u.id),
            user_two=max(self.sender, self.recipient, key=lambda u: u.id),
            application=self.app,
            opportunity=self.opp,
        )

    def test_is_mine_flag_in_messages_list_and_send_response(self):
        # 1. Sender posts a message
        self.client.force_authenticate(user=self.sender)
        res_post = self.client.post(
            f"/api/chat/conversations/{self.conv.id}/messages/",
            {"body": "Hello from sender!"},
        )
        self.assertEqual(res_post.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_post.data["is_mine"])
        self.assertFalse(res_post.data["is_deleted"])
        self.assertEqual(res_post.data["body"], "Hello from sender!")
        msg_id = res_post.data["id"]

        # 2. Sender checks messages list: is_mine must be True
        res_sender_list = self.client.get(f"/api/chat/conversations/{self.conv.id}/messages/")
        self.assertEqual(res_sender_list.status_code, status.HTTP_200_OK)
        sender_msgs = res_sender_list.data.get("results", res_sender_list.data)
        target = next(m for m in sender_msgs if m["id"] == msg_id)
        self.assertTrue(target["is_mine"])
        self.assertFalse(target["is_deleted"])

        # 3. Recipient checks messages list: is_mine must be False
        self.client.force_authenticate(user=self.recipient)
        res_rcpt_list = self.client.get(f"/api/chat/conversations/{self.conv.id}/messages/")
        self.assertEqual(res_rcpt_list.status_code, status.HTTP_200_OK)
        rcpt_msgs = res_rcpt_list.data.get("results", res_rcpt_list.data)
        rcpt_target = next(m for m in rcpt_msgs if m["id"] == msg_id)
        self.assertFalse(rcpt_target["is_mine"])
        self.assertFalse(rcpt_target["is_deleted"])

    def test_sender_can_delete_message_returns_200_and_tombstone(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.sender, body="Secret message")
        self.client.force_authenticate(user=self.sender)

        res = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_deleted"])
        self.assertEqual(res.data["body"], "")
        self.assertTrue(res.data["is_mine"])

        # Verify in database: deleted_at is set, body is erased
        msg.refresh_from_db()
        self.assertIsNotNone(msg.deleted_at)
        self.assertEqual(msg.body, "")

    def test_delete_is_idempotent(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.sender, body="Message to delete twice")
        self.client.force_authenticate(user=self.sender)

        # First delete
        res1 = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        first_deleted_at = Message.objects.get(id=msg.id).deleted_at

        # Second delete
        res2 = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertTrue(res2.data["is_deleted"])
        self.assertEqual(res2.data["body"], "")
        second_deleted_at = Message.objects.get(id=msg.id).deleted_at
        self.assertEqual(first_deleted_at, second_deleted_at)

    def test_other_participant_cannot_delete_message_returns_404(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.sender, body="Sender's message")
        self.client.force_authenticate(user=self.recipient)

        res = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

        # Ensure message text and deleted_at are unchanged in the database
        msg.refresh_from_db()
        self.assertIsNone(msg.deleted_at)
        self.assertEqual(msg.body, "Sender's message")

    def test_non_participant_cannot_delete_message_returns_404(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.sender, body="Sender's message")
        self.client.force_authenticate(user=self.third_party)

        res = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_wrong_message_conversation_pair_returns_404(self):
        # Create a second conversation between recipient and third party
        conv2 = Conversation.objects.create(
            user_one=min(self.recipient, self.third_party, key=lambda u: u.id),
            user_two=max(self.recipient, self.third_party, key=lambda u: u.id),
            is_direct=True,
        )
        msg_in_conv2 = Message.objects.create(conversation=conv2, sender=self.recipient, body="In conv2")

        self.client.force_authenticate(user=self.recipient)
        # Attempt to delete msg_in_conv2 through self.conv.id
        res = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg_in_conv2.id}/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_delete_returns_401(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.sender, body="Sender's message")
        res = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_allowed_when_application_withdrawn(self):
        self.app.status = "withdrawn"
        self.app.save()

        msg = Message.objects.create(conversation=self.conv, sender=self.sender, body="Withdrawn app message")
        self.client.force_authenticate(user=self.sender)

        # Deleting own message is allowed even when withdrawn
        res = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_deleted"])
        self.assertEqual(res.data["body"], "")

    def test_deleted_message_body_is_empty_in_list_and_later_serialization(self):
        msg = Message.objects.create(
            conversation=self.conv,
            sender=self.sender,
            body="",
            deleted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.recipient)
        res = self.client.get(f"/api/chat/conversations/{self.conv.id}/messages/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get("results", res.data)
        deleted_item = next(m for m in results if m["id"] == msg.id)
        self.assertEqual(deleted_item["body"], "")
        self.assertTrue(deleted_item["is_deleted"])

    def test_conversation_list_preview_shows_tombstone_when_latest_deleted(self):
        m1 = Message.objects.create(conversation=self.conv, sender=self.sender, body="First valid message")
        m2 = Message.objects.create(
            conversation=self.conv,
            sender=self.recipient,
            body="",
            deleted_at=timezone.now(),
        )

        self.client.force_authenticate(user=self.sender)
        res = self.client.get("/api/chat/conversations/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.data.get("results", res.data)
        conv_item = next(c for c in results if c["id"] == self.conv.id)
        self.assertEqual(conv_item["last_message_preview"], "This message was deleted")

    def test_deleting_unread_message_lowers_other_participant_unread_count(self):
        # Sender sends an unread message
        msg = Message.objects.create(conversation=self.conv, sender=self.sender, body="Unread alert message")

        # Recipient sees unread_count == 1 in list and endpoint
        self.client.force_authenticate(user=self.recipient)
        res_unread1 = self.client.get("/api/chat/unread-count/")
        self.assertEqual(res_unread1.data["unread_total"], 1)

        res_list1 = self.client.get("/api/chat/conversations/")
        conv1 = next(c for c in res_list1.data.get("results", res_list1.data) if c["id"] == self.conv.id)
        self.assertEqual(conv1["unread_count"], 1)

        # Sender deletes their own message
        self.client.force_authenticate(user=self.sender)
        res_del = self.client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
        self.assertEqual(res_del.status_code, status.HTTP_200_OK)

        # Recipient's unread_count drops to 0 across list, unread endpoint, and mark-read endpoint
        self.client.force_authenticate(user=self.recipient)
        res_unread2 = self.client.get("/api/chat/unread-count/")
        self.assertEqual(res_unread2.data["unread_total"], 0)

        res_list2 = self.client.get("/api/chat/conversations/")
        conv2 = next(c for c in res_list2.data.get("results", res_list2.data) if c["id"] == self.conv.id)
        self.assertEqual(conv2["unread_count"], 0)

        res_mark = self.client.post(f"/api/chat/conversations/{self.conv.id}/read/")
        self.assertEqual(res_mark.data["unread_total"], 0)


@override_settings(
    ALLOWED_HOSTS=["localhost", "127.0.0.1", "testserver"],
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
)
class MessageDeleteWebSocketTests(TransactionTestCase):
    def setUp(self):
        cache.clear()
        self.sender = User.objects.create_user(
            email="ws_del_sender@example.com",
            password="Password123!",
            full_name="WS Del Sender",
            role="student",
            is_verified=True,
        )
        self.recipient = User.objects.create_user(
            email="ws_del_rcpt@example.com",
            password="Password123!",
            full_name="WS Del Rcpt",
            role="provider",
            is_verified=True,
        )
        self.third_party = User.objects.create_user(
            email="ws_del_third@example.com",
            password="Password123!",
            full_name="WS Del Third",
            role="student",
            is_verified=True,
        )

        self.conv = Conversation.objects.create(
            user_one=min(self.sender, self.recipient, key=lambda u: u.id),
            user_two=max(self.sender, self.recipient, key=lambda u: u.id),
            is_direct=True,
        )

        self.token_sender = str(RefreshToken.for_user(self.sender).access_token)
        self.token_rcpt = str(RefreshToken.for_user(self.recipient).access_token)
        self.token_third = str(RefreshToken.for_user(self.third_party).access_token)

    async def test_websocket_chat_message_deleted_event_dispatch(self):
        msg = await sync_to_async(Message.objects.create)(
            conversation=self.conv,
            sender=self.sender,
            body="Message to be deleted realtime",
        )

        comm_rcpt = WebsocketCommunicator(inner_application, f"/ws/notifications/?token={self.token_rcpt}")
        comm_sender = WebsocketCommunicator(inner_application, f"/ws/notifications/?token={self.token_sender}")
        comm_third = WebsocketCommunicator(inner_application, f"/ws/notifications/?token={self.token_third}")

        self.assertTrue((await comm_rcpt.connect())[0])
        self.assertTrue((await comm_sender.connect())[0])
        self.assertTrue((await comm_third.connect())[0])

        def _delete_message():
            from rest_framework.test import APIClient
            client = APIClient()
            client.force_authenticate(user=self.sender)
            return client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")

        res = await sync_to_async(_delete_message)()
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Recipient receives chat_message_deleted event
        received_event = None
        for _ in range(3):
            try:
                event = await comm_rcpt.receive_json_from(timeout=1.0)
                if event.get("type") == "chat_message_deleted":
                    received_event = event
                    break
            except Exception:
                break

        self.assertIsNotNone(received_event, "Recipient did not receive chat_message_deleted event")
        self.assertEqual(received_event["type"], "chat_message_deleted")
        self.assertEqual(received_event["message"]["id"], msg.id)
        self.assertEqual(received_event["message"]["conversation_id"], self.conv.id)

        # Verify privacy: no email or phone in websocket event
        ws_json = json.dumps(received_event)
        self.assertNotIn("email", ws_json)
        self.assertNotIn("phone", ws_json)
        self.assertNotIn(self.sender.email, ws_json)

        # Sender receives NOTHING on their socket
        self.assertTrue(await comm_sender.receive_nothing(timeout=0.5))

        # Third party receives NOTHING on their socket
        self.assertTrue(await comm_third.receive_nothing(timeout=0.5))

        await comm_rcpt.disconnect()
        await comm_sender.disconnect()
        await comm_third.disconnect()

    def test_channel_layer_failure_does_not_break_delete_or_response(self):
        msg = Message.objects.create(conversation=self.conv, sender=self.sender, body="Fault tolerant delete")

        with patch("apps.chat.views.get_channel_layer") as mock_layer:
            mock_layer.side_effect = Exception("Channel layer down during delete!")

            from rest_framework.test import APIClient
            client = APIClient()
            client.force_authenticate(user=self.sender)
            res = client.delete(f"/api/chat/conversations/{self.conv.id}/messages/{msg.id}/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertTrue(res.data["is_deleted"])
            msg.refresh_from_db()
            self.assertIsNotNone(msg.deleted_at)
