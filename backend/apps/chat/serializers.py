from rest_framework import serializers

from .models import Conversation, Message, MessageRequest


class ChatParticipantSerializer(serializers.Serializer):
    """
    Public participant serializer for chat.
    Strictly limited to id and full_name for privacy (no email, phone, or address).
    """
    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)


class ChatOpportunitySerializer(serializers.Serializer):
    """
    Minimal opportunity summary for chat conversations.
    """
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(read_only=True)


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for chat messages.
    """
    conversation_id = serializers.IntegerField(source="conversation.id", read_only=True)
    sender = ChatParticipantSerializer(read_only=True)

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation_id",
            "sender",
            "body",
            "created_at",
            "read_at",
        ]
        read_only_fields = ["id", "conversation_id", "sender", "created_at", "read_at"]


class ConversationListSerializer(serializers.ModelSerializer):
    """
    Serializer for listing conversations of the authenticated user.
    Exposes id, other_participant (id, full_name only), opportunity {id, title} or null,
    last_message_preview (truncated), unread_count, and last_message_at.
    """
    other_participant = serializers.SerializerMethodField()
    opportunity = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "other_participant",
            "opportunity",
            "last_message_preview",
            "unread_count",
            "last_message_at",
            "created_at",
        ]

    def get_other_participant(self, obj):
        request = self.context.get("request")
        user = request.user if request else None
        if user and obj.user_one_id == user.id:
            other = obj.user_two
        else:
            other = obj.user_one
        return {
            "id": other.id,
            "full_name": other.full_name or "",
        }

    def get_opportunity(self, obj):
        if not obj.opportunity:
            return None
        return {
            "id": obj.opportunity.id,
            "title": obj.opportunity.title,
        }

    def get_last_message_preview(self, obj):
        body = getattr(obj, "last_message_body", None)
        if body is None:
            last_msg = obj.messages.order_by("-created_at", "-id").first()
            body = last_msg.body if last_msg else ""
        if not body:
            return ""
        return (body[:100] + "...") if len(body) > 100 else body


class MessageRequestIncomingSerializer(serializers.ModelSerializer):
    """
    Serializer for incoming message requests received by the authenticated student.
    Strictly excludes declined_at. Sender contains only id and full_name.
    """
    sender = ChatParticipantSerializer(read_only=True)

    class Meta:
        model = MessageRequest
        fields = [
            "id",
            "sender",
            "intro",
            "created_at",
        ]
        read_only_fields = fields


class MessageRequestOutgoingSerializer(serializers.ModelSerializer):
    """
    Serializer for outgoing message requests sent by the authenticated student.
    Strictly excludes declined_at. Receiver contains only id and full_name.
    """
    receiver = ChatParticipantSerializer(read_only=True)

    class Meta:
        model = MessageRequest
        fields = [
            "id",
            "receiver",
            "intro",
            "status",
            "created_at",
        ]
        read_only_fields = fields

