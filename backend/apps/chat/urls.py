from django.urls import path

from .views import (
    ConversationListCreateView,
    ConversationMarkReadView,
    MessageListCreateView,
    UnreadChatCountView,
)

app_name = "chat"

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list-create"),
    path("conversations/<int:conversation_id>/messages/", MessageListCreateView.as_view(), name="conversation-messages"),
    path("conversations/<int:conversation_id>/read/", ConversationMarkReadView.as_view(), name="conversation-mark-read"),
    path("unread-count/", UnreadChatCountView.as_view(), name="chat-unread-count"),
]
