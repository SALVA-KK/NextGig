import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, models, transaction
from django.db.models import Case, Count, Exists, F, OuterRef, Q, Subquery, Value, When
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

from .models import Conversation, Message, MessageRequest
from .serializers import (
    ConversationListSerializer,
    MessageRequestIncomingSerializer,
    MessageRequestOutgoingSerializer,
    MessageSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class ChatPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ChatMessagePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


def is_pair_messaging_blocked(user_a, user_b, conversation=None):
    """
    Pair-level withdrawn rule:
    Messaging is blocked ONLY if:
    1. The conversation is not direct, AND
    2. The pair has at least one application between them (either direction, through opportunity poster), AND
    3. Every one of those applications is withdrawn.
    Direct conversations and pairs with no applications are never blocked.
    """
    if conversation and conversation.is_direct:
        return False

    u1_id = min(user_a.id, user_b.id)
    u2_id = max(user_a.id, user_b.id)

    pair_apps = Application.objects.filter(
        Q(applicant_id=u1_id, opportunity__poster_id=u2_id)
        | Q(applicant_id=u2_id, opportunity__poster_id=u1_id)
    )

    if not pair_apps.exists():
        return False

    return not pair_apps.exclude(status="withdrawn").exists()


def get_or_create_pair_conversation(user_a, user_b, application=None, set_direct=False):
    """
    Finds or creates the single canonical conversation for a pair of users.
    Uses transaction-level Postgres advisory lock (pg_advisory_xact_lock) on the ordered pair (u1, u2)
    to guarantee race-safety without creating duplicate conversations.
    """
    u1 = min(user_a, user_b, key=lambda u: u.id)
    u2 = max(user_a, user_b, key=lambda u: u.id)

    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s);", [u1.id, u2.id])

    # 1. If an application is given, check if a conversation is already attached to this exact application
    if application:
        conv = Conversation.objects.filter(application=application).first()
        if conv:
            if set_direct and not conv.is_direct:
                conv.is_direct = True
                conv.save(update_fields=["is_direct"])
            return conv, False

    # 2. Check if ANY conversation already exists for the pair (lowest id)
    conv = Conversation.objects.filter(user_one=u1, user_two=u2).order_by("id").first()
    if conv:
        if set_direct and not conv.is_direct:
            conv.is_direct = True
            conv.save(update_fields=["is_direct"])
        return conv, False

    # 3. None exists, create a new conversation
    opp = application.opportunity if application else None
    try:
        conv = Conversation.objects.create(
            user_one=u1,
            user_two=u2,
            application=application,
            opportunity=opp,
            is_direct=set_direct,
            last_message_at=timezone.now(),
        )
        return conv, True
    except IntegrityError:
        # Fallback if another concurrent process committed just ahead
        conv = Conversation.objects.filter(user_one=u1, user_two=u2).order_by("id").first()
        if conv:
            if set_direct and not conv.is_direct:
                conv.is_direct = True
                conv.save(update_fields=["is_direct"])
            return conv, False
        raise


class ConversationListCreateView(APIView):
    """
    GET: List my conversations, newest activity first.
    POST: Create or return existing conversation for an application.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_general"

    def get(self, request, *args, **kwargs):
        last_msg_subquery = (
            Message.objects.filter(conversation=OuterRef("pk"))
            .order_by("-created_at", "-id")
            .annotate(
                preview_text=Case(
                    When(deleted_at__isnull=False, then=Value("This message was deleted")),
                    default=F("body"),
                    output_field=models.TextField(),
                )
            )
            .values("preview_text")[:1]
        )

        has_messages = Exists(Message.objects.filter(conversation=OuterRef("pk")))

        queryset = (
            Conversation.objects.filter(
                Q(user_one=request.user) | Q(user_two=request.user)
            )
            .filter(Q(is_direct=True) | has_messages)
            .select_related("user_one", "user_two", "opportunity")
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(messages__read_at__isnull=True)
                    & Q(messages__deleted_at__isnull=True)
                    & ~Q(messages__sender=request.user),
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

        other_user = poster if request.user == applicant else applicant

        with transaction.atomic():
            # If a legacy conversation is already attached to this exact application, return that one
            exact_app_conv = Conversation.objects.filter(application=application).first()
            if exact_app_conv:
                serializer = ConversationListSerializer(exact_app_conv, context={"request": request})
                return Response(serializer.data, status=status.HTTP_200_OK)

            # Check pair withdrawn rule:
            # withdrawn application returns 400 only when the application given is withdrawn and no other pair application is active
            if application.status == "withdrawn" and is_pair_messaging_blocked(request.user, other_user):
                return Response(
                    {"detail": "Cannot start a conversation for a withdrawn application."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            conv, created = get_or_create_pair_conversation(
                request.user, other_user, application=application, set_direct=False
            )

        serializer = ConversationListSerializer(conv, context={"request": request})
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationDetailView(APIView):
    """
    GET: Retrieve details of a single conversation for its participants.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_general"

    def get(self, request, conversation_id, *args, **kwargs):
        last_msg_subquery = (
            Message.objects.filter(conversation=OuterRef("pk"))
            .order_by("-created_at", "-id")
            .annotate(
                preview_text=Case(
                    When(deleted_at__isnull=False, then=Value("This message was deleted")),
                    default=F("body"),
                    output_field=models.TextField(),
                )
            )
            .values("preview_text")[:1]
        )

        conversation = (
            Conversation.objects.filter(
                id=conversation_id,
            )
            .filter(Q(user_one=request.user) | Q(user_two=request.user))
            .select_related("user_one", "user_two", "opportunity")
            .annotate(
                unread_count=Count(
                    "messages",
                    filter=Q(messages__read_at__isnull=True)
                    & Q(messages__deleted_at__isnull=True)
                    & ~Q(messages__sender=request.user),
                    distinct=True,
                ),
                last_message_body=Subquery(last_msg_subquery),
            )
            .first()
        )
        if not conversation:
            raise Http404("Conversation not found.")

        serializer = ConversationListSerializer(conversation, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


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
            serializer = MessageSerializer(page, many=True, context={"request": request})
            return paginator.get_paginated_response(serializer.data)

        serializer = MessageSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request, conversation_id, *args, **kwargs):
        conversation = self._get_conversation(conversation_id, request.user)
        recipient = conversation.get_other_participant(request.user)

        # Block sending if pair messaging is blocked (pair-level withdrawn rule)
        if is_pair_messaging_blocked(request.user, recipient, conversation=conversation):
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
            sender_name = request.user.full_name or "A user"
            if conversation.opportunity:
                notif_msg = f"{sender_name} sent you a message about {conversation.opportunity.title}"
            else:
                notif_msg = f"{sender_name} sent you a message."
            event_key = f"first_chat:{conversation.id}:{recipient.id}"
            try:
                create_notification(
                    recipient=recipient,
                    notification_type=Notification.NotificationType.NEW_CHAT_MESSAGE,
                    title="New message",
                    message=notif_msg,
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
            "is_mine": False,
            "is_deleted": False,
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

        serializer = MessageSerializer(message, context={"request": request})
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
            deleted_at__isnull=True,
        ).exclude(sender=request.user).update(read_at=now)

        new_unread_total = (
            Message.objects.filter(
                conversation__in=Conversation.objects.filter(
                    Q(user_one=request.user) | Q(user_two=request.user)
                ),
                read_at__isnull=True,
                deleted_at__isnull=True,
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


class MessageDeleteView(APIView):
    """
    DELETE: Allows the sender of a message to delete it (tombstone).
    Sets deleted_at = now and body = "" (erased from database).
    Idempotent: deleting an already deleted message returns 200 with is_deleted=True.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_general"

    def delete(self, request, conversation_id, message_id, *args, **kwargs):
        conversation = (
            Conversation.objects.filter(id=conversation_id)
            .filter(Q(user_one=request.user) | Q(user_two=request.user))
            .first()
        )
        if not conversation:
            raise Http404("Conversation not found.")

        message = Message.objects.filter(id=message_id, conversation=conversation).first()
        if not message or message.sender_id != request.user.id:
            raise Http404("Message not found.")

        recipient = conversation.get_other_participant(request.user)

        with transaction.atomic():
            if message.deleted_at is None:
                message.deleted_at = timezone.now()
                message.body = ""
                message.save(update_fields=["deleted_at", "body"])

        def _push_deleted_message():
            try:
                channel_layer = get_channel_layer()
                if channel_layer is not None:
                    async_to_sync(channel_layer.group_send)(
                        f"user_notifications_{recipient.id}",
                        {
                            "type": "chat.message_deleted",
                            "message": {
                                "id": message.id,
                                "conversation_id": conversation.id,
                            },
                        },
                    )
            except Exception:
                logger.warning("Failed to push chat message deleted event over channel layer")

        transaction.on_commit(_push_deleted_message)

        serializer = MessageSerializer(message, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


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
                deleted_at__isnull=True,
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


class ChatRequestCreateView(APIView):
    """
    POST: Send a message request from authenticated student to another discoverable student.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_request_action"

    def post(self, request, *args, **kwargs):
        if request.user.role != "student":
            return Response(
                {"detail": "Only students can send message requests."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not request.user.is_verified:
            return Response(
                {"detail": "You must verify your email to send message requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        receiver_id = request.data.get("receiver_id")
        if not receiver_id:
            return Response(
                {"detail": "receiver_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Receiver lookup stays FIRST so no other error reveals a hidden user
        try:
            receiver = User.objects.select_related("student_profile").get(id=receiver_id)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if not (
            receiver.is_active
            and receiver.is_verified
            and receiver.role == "student"
            and not receiver.is_staff
            and not receiver.is_superuser
            and hasattr(receiver, "student_profile")
            and receiver.student_profile.is_discoverable
        ):
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        if receiver.id == request.user.id:
            return Response(
                {"detail": "You cannot send a message request to yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Active conversation check: conversation is active unless blocked by pair-level withdrawn rule
            u1, u2 = (request.user, receiver) if request.user.id < receiver.id else (receiver, request.user)
            pair_conv = Conversation.objects.filter(user_one=u1, user_two=u2).order_by("id").first()
            if pair_conv and not is_pair_messaging_blocked(request.user, receiver, conversation=pair_conv):
                return Response(
                    {
                        "detail": "You already have an active conversation with this user.",
                        "conversation_id": pair_conv.id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Reverse pending request check
            reverse_req = MessageRequest.objects.filter(
                sender=receiver,
                receiver=request.user,
                status=MessageRequest.Status.PENDING,
            ).first()
            if reverse_req:
                return Response(
                    {
                        "detail": "This user has already sent you a request.",
                        "request_id": reverse_req.id,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Cooldown after decline: generic 400 message without mentioning decline or date
            cooldown_days = getattr(settings, "CHAT_REQUEST_DECLINE_COOLDOWN_DAYS", 7)
            cooldown_cutoff = timezone.now() - timedelta(days=cooldown_days)
            has_recent_decline = MessageRequest.objects.filter(
                sender=request.user,
                receiver=receiver,
                status=MessageRequest.Status.DECLINED,
                declined_at__gte=cooldown_cutoff,
            ).exists()
            if has_recent_decline:
                return Response(
                    {"detail": "You can't send a request to this user right now."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Daily limit: counts requests in ALL statuses including cancelled
            daily_limit = getattr(settings, "CHAT_REQUEST_DAILY_LIMIT", 10)
            cutoff_24h = timezone.now() - timedelta(hours=24)
            daily_count = MessageRequest.objects.filter(
                sender=request.user,
                created_at__gte=cutoff_24h,
            ).count()
            if daily_count >= daily_limit:
                return Response(
                    {"detail": "Daily request limit reached. Please try again tomorrow."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check duplicate pending request
            if MessageRequest.objects.filter(
                sender=request.user,
                receiver=receiver,
                status=MessageRequest.Status.PENDING,
            ).exists():
                return Response(
                    {"detail": "A pending request already exists for this user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            raw_intro = request.data.get("intro", "")
            if not isinstance(raw_intro, str):
                return Response(
                    {"detail": "Intro must be a string."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if len(raw_intro) > 300:
                return Response(
                    {"detail": "Intro cannot exceed 300 characters."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            clean_intro = raw_intro.strip()

            try:
                req_obj = MessageRequest.objects.create(
                    sender=request.user,
                    receiver=receiver,
                    intro=clean_intro,
                    status=MessageRequest.Status.PENDING,
                )
            except IntegrityError:
                return Response(
                    {"detail": "A pending request already exists for this user."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                with transaction.atomic():
                    sender_name = request.user.full_name or "A student"
                    create_notification(
                        recipient=receiver,
                        notification_type=Notification.NotificationType.CHAT_REQUEST_RECEIVED,
                        title="New message request",
                        message=f"{sender_name} sent you a message request.",
                        actor=None,
                        event_key=f"chat_request_received:{req_obj.id}",
                    )
            except Exception:
                logger.warning("Failed to create chat request received notification", exc_info=True)

            return Response(
                MessageRequestOutgoingSerializer(req_obj).data,
                status=status.HTTP_201_CREATED,
            )


class ChatRequestIncomingListView(APIView):
    """
    GET: List incoming message requests (pending only; hides inactive/unverified senders).
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_general"

    def get(self, request, *args, **kwargs):
        if request.user.role != "student":
            return Response(
                {"detail": "Only students can view message requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = (
            MessageRequest.objects.filter(
                receiver=request.user,
                status=MessageRequest.Status.PENDING,
                sender__is_active=True,
                sender__is_verified=True,
                sender__role="student",
                sender__is_staff=False,
                sender__is_superuser=False,
            )
            .select_related("sender")
            .order_by("-created_at")
        )

        paginator = ChatPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = MessageRequestIncomingSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = MessageRequestIncomingSerializer(queryset, many=True)
        return Response(serializer.data)


class ChatRequestOutgoingListView(APIView):
    """
    GET: List outgoing message requests sent by the authenticated student.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_general"

    def get(self, request, *args, **kwargs):
        if request.user.role != "student":
            return Response(
                {"detail": "Only students can view message requests."},
                status=status.HTTP_403_FORBIDDEN,
            )

        queryset = (
            MessageRequest.objects.filter(sender=request.user)
            .select_related("receiver")
            .order_by("-created_at")
        )

        paginator = ChatPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = MessageRequestOutgoingSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = MessageRequestOutgoingSerializer(queryset, many=True)
        return Response(serializer.data)


class ChatRequestAcceptView(APIView):
    """
    POST: Accept a message request, creating a direct conversation.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_request_action"

    def post(self, request, pk, *args, **kwargs):
        with transaction.atomic():
            req = (
                MessageRequest.objects.select_for_update(of=("self",))
                .filter(id=pk, receiver=request.user)
                .first()
            )
            if not req:
                return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

            if req.status == MessageRequest.Status.ACCEPTED:
                return Response(
                    {
                        "detail": "Request already accepted.",
                        "conversation_id": req.conversation_id,
                    },
                    status=status.HTTP_200_OK,
                )

            if req.status != MessageRequest.Status.PENDING:
                return Response(
                    {"detail": "Only pending requests can be accepted."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sender = req.sender
            if not (
                sender.is_active
                and sender.is_verified
                and sender.role == "student"
                and not sender.is_staff
                and not sender.is_superuser
            ):
                return Response(
                    {"detail": "Sender is no longer eligible for chat."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            conv, _ = get_or_create_pair_conversation(
                request.user, sender, application=None, set_direct=True
            )

            # Mark opposite pending request accepted if one exists
            reverse_req = (
                MessageRequest.objects.select_for_update(of=("self",))
                .filter(sender=request.user, receiver=sender, status=MessageRequest.Status.PENDING)
                .first()
            )
            if reverse_req:
                reverse_req.status = MessageRequest.Status.ACCEPTED
                reverse_req.conversation = conv
                reverse_req.save(update_fields=["status", "conversation", "updated_at"])

            req.status = MessageRequest.Status.ACCEPTED
            req.conversation = conv
            req.save(update_fields=["status", "conversation", "updated_at"])

            try:
                with transaction.atomic():
                    receiver_name = request.user.full_name or "A student"
                    create_notification(
                        recipient=sender,
                        notification_type=Notification.NotificationType.CHAT_REQUEST_ACCEPTED,
                        title="Chat request accepted",
                        message=f"{receiver_name} accepted your message request.",
                        actor=None,
                        event_key=f"chat_request_accepted:{req.id}",
                    )
            except Exception:
                logger.warning("Failed to create notification on request accepted", exc_info=True)

            return Response(
                {
                    "detail": "Request accepted.",
                    "conversation_id": conv.id,
                },
                status=status.HTTP_200_OK,
            )


class ChatRequestDeclineView(APIView):
    """
    POST: Decline a pending message request.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_request_action"

    def post(self, request, pk, *args, **kwargs):
        with transaction.atomic():
            req = (
                MessageRequest.objects.select_for_update(of=("self",))
                .filter(id=pk, receiver=request.user)
                .first()
            )
            if not req:
                return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

            if req.status == MessageRequest.Status.DECLINED:
                return Response({"detail": "Request already declined."}, status=status.HTTP_200_OK)

            if req.status != MessageRequest.Status.PENDING:
                return Response(
                    {"detail": "Only pending requests can be declined."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            req.status = MessageRequest.Status.DECLINED
            req.declined_at = timezone.now()
            req.save(update_fields=["status", "declined_at", "updated_at"])

            return Response({"detail": "Request declined."}, status=status.HTTP_200_OK)


class ChatRequestCancelView(APIView):
    """
    POST: Cancel a pending outgoing message request.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat_request_action"

    def post(self, request, pk, *args, **kwargs):
        with transaction.atomic():
            req = (
                MessageRequest.objects.select_for_update(of=("self",))
                .filter(id=pk, sender=request.user)
                .first()
            )
            if not req:
                return Response({"detail": "Request not found."}, status=status.HTTP_404_NOT_FOUND)

            if req.status == MessageRequest.Status.CANCELLED:
                return Response({"detail": "Request already cancelled."}, status=status.HTTP_200_OK)

            if req.status != MessageRequest.Status.PENDING:
                return Response(
                    {"detail": "Only pending requests can be cancelled."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            req.status = MessageRequest.Status.CANCELLED
            req.save(update_fields=["status", "updated_at"])

            return Response({"detail": "Request cancelled."}, status=status.HTTP_200_OK)

