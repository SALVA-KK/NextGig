from django.urls import path

from .views import (
    ChatRequestAcceptView,
    ChatRequestCancelView,
    ChatRequestCreateView,
    ChatRequestDeclineView,
    ChatRequestIncomingListView,
    ChatRequestOutgoingListView,
    ConversationDetailView,
    ConversationListCreateView,
    ConversationMarkReadView,
    MessageDeleteView,
    MessageListCreateView,
    UnreadChatCountView,
)

app_name = "chat"

urlpatterns = [
    path("conversations/", ConversationListCreateView.as_view(), name="conversation-list-create"),
    path("conversations/<int:conversation_id>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("conversations/<int:conversation_id>/messages/", MessageListCreateView.as_view(), name="conversation-messages"),
    path("conversations/<int:conversation_id>/messages/<int:message_id>/", MessageDeleteView.as_view(), name="conversation-message-delete"),
    path("conversations/<int:conversation_id>/read/", ConversationMarkReadView.as_view(), name="conversation-mark-read"),
    path("unread-count/", UnreadChatCountView.as_view(), name="chat-unread-count"),
    path("requests/", ChatRequestCreateView.as_view(), name="request-create"),
    path("requests/incoming/", ChatRequestIncomingListView.as_view(), name="request-incoming-list"),
    path("requests/outgoing/", ChatRequestOutgoingListView.as_view(), name="request-outgoing-list"),
    path("requests/<int:pk>/accept/", ChatRequestAcceptView.as_view(), name="request-accept"),
    path("requests/<int:pk>/decline/", ChatRequestDeclineView.as_view(), name="request-decline"),
    path("requests/<int:pk>/cancel/", ChatRequestCancelView.as_view(), name="request-cancel"),
]
