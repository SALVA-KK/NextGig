import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.db.models import Count, OuterRef, Q, Subquery
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.opportunities.models import Application

from .models import Conversation, Message
from .serializers import (
    ConversationListSerializer,
    MessageSerializer,
)

logger = logging.getLogger(__name__)


class ChatPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ChatMessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


class ConversationListCreateView(APIView):
    """
    GET: List my conversations, newest activity first.
    POST: Create or return existing conversation for an application.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_general"

    def get(self, request, *args, **kwargs):
        last_msg_subquery = Message.objects.filter(
            conversation=OuterRef("pk")
        ).order_by("-created_at", "-id").values("body")[:1]

        queryset = (
            Conversation.objects.filter(
                Q(user_one=request.user) | Q(user_two=request.user)
            )
            .select_related("user_one", "user_two", "opportunity")
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(messages__read_at__isnull=True) & ~Q(messages__sender=request.user),
                    distinct=True,
                ),
                last_message_body=Subquery(last_msg_subquery),
            )
            .order_by("-last_message_at", "-id")
        )

        paginator = ChatPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = ConversationListSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)

        serializer = ConversationListSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        application_id = request.data.get("application_id")
        if not application_id:
            return Response(
                {"application_id": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            application = (
                Application.objects.select_related("applicant", "opportunity__poster")
                .get(id=application_id)
            )
        except (Application.DoesNotExist, ValueError, TypeError):
            raise Http404("Application not found.")

        poster = application.opportunity.poster
        applicant = application.applicant

        # Only applicant or poster can access/create a conversation
        if request.user != applicant and request.user != poster:
            raise Http404("Application not found.")

        # Self-application cannot create a conversation
        if applicant.id == poster.id:
            return Response(
                {"detail": "Self-application cannot create a conversation."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Return existing conversation if present
        existing = Conversation.objects.filter(application=application).first()
        if existing:
            serializer = ConversationListSerializer(existing, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Cannot create a conversation for a withdrawn application
        if application.status == "withdrawn":
            return Response(
                {"detail": "Cannot start a conversation for a withdrawn application."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_one = min(applicant, poster, key=lambda u: u.id)
        user_two = max(applicant, poster, key=lambda u: u.id)

        try:
            conversation = Conversation.objects.create(
                user_one=user_one,
                user_two=user_two,
                application=application,
                opportunity=application.opportunity,
                last_message_at=timezone.now(),
            )
        except IntegrityError:
            existing = Conversation.objects.filter(application=application).first()
            if existing:
                serializer = ConversationListSerializer(existing, context={"request": request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            raise

        serializer = ConversationListSerializer(conversation, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MessageListCreateView(APIView):
    """
    GET: List messages in a conversation (supports ?order=desc for newest-first, default oldest-first).
    POST: Send a new message to the conversation.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]

    def get_throttles(self):
        if self.request.method.upper() == "POST":
            self.throttle_scope = "chat_message_send"
        else:
            self.throttle_scope = "chat_general"
        return super().get_throttles()

    def _get_conversation(self, conversation_id, user):
        conversation = (
            Conversation.objects.filter(id=conversation_id)
            .filter(Q(user_one=user) | Q(user_two=user))
            .select_related("user_one", "user_two", "opportunity", "application")
            .first()
        )
        if not conversation:
            raise Http404("Conversation not found.")
        return conversation

    def get(self, request, conversation_id, *args, **kwargs):
        conversation = self._get_conversation(conversation_id, request.user)

        order_param = (request.query_params.get("order") or "").strip().lower()
        if order_param == "desc":
            ordering = ("-created_at", "-id")
        else:
            ordering = ("created_at", "id")

        queryset = conversation.messages.select_related("sender").order_by(*ordering)

        paginator = ChatMessagePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = MessageSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = MessageSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, conversation_id, *args, **kwargs):
        conversation = self._get_conversation(conversation_id, request.user)

        # Block sending if application is withdrawn
        if conversation.application and conversation.application.status == "withdrawn":
            return Response(
                {"detail": "Cannot send messages because this application has been withdrawn."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = request.data.get("body")
        if body is None or not isinstance(body, str):
            return Response(
                {"body": ["This field must be a valid text string."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        body = body.strip()
        if not (1 <= len(body) <= 2000):
            return Response(
                {"body": ["Message body must be between 1 and 2000 characters."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recipient = conversation.get_other_participant(request.user)

        with transaction.atomic():
            message = Message.objects.create(
                conversation=conversation,
                sender=request.user,
                body=body,
            )

            conversation.last_message_at = message.created_at
            conversation.save(update_fields=["last_message_at"])

        # First-message notification (exactly once per direction; actor omitted for privacy)
        prior_messages_from_sender = (
            Message.objects.filter(
                conversation=conversation,
                sender=request.user,
            )
            .exclude(id=message.id)
            .exists()
        )

        if not prior_messages_from_sender:
            opp_title = conversation.opportunity.title if conversation.opportunity else "an opportunity"
            sender_name = request.user.full_name or "A user"
            event_key = f"first_chat:{conversation.id}:{recipient.id}"
            try:
                create_notification(
                    recipient=recipient,
                    notification_type=Notification.NotificationType.NEW_CHAT_MESSAGE,
                    title="New message",
                    message=f"{sender_name} sent you a message about {opp_title}",
                    opportunity=conversation.opportunity,
                    application=conversation.application,
                    event_key=event_key,
                )
            except Exception:
                logger.warning("Failed to create first-message notification", exc_info=True)

        # Push to recipient via WebSocket
        msg_payload = {
            "id": message.id,
            "conversation_id": conversation.id,
            "sender": {
                "id": request.user.id,
                "full_name": request.user.full_name or "",
            },
            "body": message.body,
            "created_at": message.created_at.isoformat(),
        }

        def _push_chat_message():
            try:
                channel_layer = get_channel_layer()
                if channel_layer is not None:
                    async_to_sync(channel_layer.group_send)(
                        f"user_notifications_{recipient.id}",
                        {
                            "type": "chat.message",
                            "message": msg_payload,
                        },
                    )
            except Exception:
                logger.warning("Failed to push chat message over channel layer")

        transaction.on_commit(_push_chat_message)

        serializer = MessageSerializer(message)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConversationMarkReadView(APIView):
    """
    POST: Marks the other participant's unread messages in this conversation as read.
    Returns the new total unread messages count across all conversations.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_general"

    def post(self, request, conversation_id, *args, **kwargs):
        conversation = (
            Conversation.objects.filter(id=conversation_id)
            .filter(Q(user_one=request.user) | Q(user_two=request.user))
            .first()
        )
        if not conversation:
            raise Http404("Conversation not found.")

        now = timezone.now()
        Message.objects.filter(
            conversation=conversation,
            read_at__isnull=True,
        ).exclude(sender=request.user).update(read_at=now)

        new_unread_total = (
            Message.objects.filter(
                conversation__in=Conversation.objects.filter(
                    Q(user_one=request.user) | Q(user_two=request.user)
                ),
                read_at__isnull=True,
            )
            .exclude(sender=request.user)
            .count()
        )

        return Response(
            {
                "unread_total": new_unread_total,
                "count": new_unread_total,
            },
            status=status.HTTP_200_OK,
        )


class UnreadChatCountView(APIView):
    """
    GET: Returns the total unread messages count for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_general"

    def get(self, request, *args, **kwargs):
        total_unread = (
            Message.objects.filter(
                conversation__in=Conversation.objects.filter(
                    Q(user_one=request.user) | Q(user_two=request.user)
                ),
                read_at__isnull=True,
            )
            .exclude(sender=request.user)
            .count()
        )

        return Response(
            {
                "unread_total": total_unread,
                "count": total_unread,
            },
            status=status.HTTP_200_OK,
        )
