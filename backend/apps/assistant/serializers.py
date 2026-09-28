from rest_framework import serializers


class ChatHistoryItemSerializer(serializers.Serializer):
    role = serializers.CharField(required=True)
    content = serializers.CharField(required=True)

    def validate_role(self, value):
        if value not in ("user", "assistant"):
            raise serializers.ValidationError("Role must be 'user' or 'assistant'.")
        return value

    def validate_content(self, value):
        stripped = value.strip() if value else ""
        if not stripped or len(stripped) > 1000:
            raise serializers.ValidationError("Content must be 1-1000 characters after stripping.")
        return stripped


class AssistantChatSerializer(serializers.Serializer):
    message = serializers.CharField(required=True)
    history = serializers.ListField(
        child=ChatHistoryItemSerializer(),
        required=False,
        allow_empty=True,
        default=list,
        max_length=50,
    )

    def validate_message(self, value):
        stripped = value.strip() if value else ""
        if not stripped or len(stripped) > 500:
            raise serializers.ValidationError("Message must be 1-500 characters after stripping.")
        return stripped

    def validate_history(self, value):
        if not value:
            return []
        if len(value) > 10:
            value = value[-10:]
        return value
