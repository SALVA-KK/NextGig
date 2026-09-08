from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notification

User = get_user_model()


class ActorPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "full_name", "email")
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    actor = ActorPublicSerializer(read_only=True)
    opportunity_id = serializers.PrimaryKeyRelatedField(read_only=True)
    application_id = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Notification
        fields = (
            "id",
            "notification_type",
            "title",
            "message",
            "is_read",
            "read_at",
            "created_at",
            "actor",
            "opportunity_id",
            "application_id",
        )
        read_only_fields = fields
