import logging
import urllib.parse

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user_from_access_token(token_str: str):
    """
    Validates a simplejwt access token and retrieves the corresponding active user.
    Returns None if the token is invalid, expired, or the user is not found/inactive.
    """
    try:
        token = AccessToken(token_str)
        user_id = token.get("user_id")
        if not user_id:
            return None
        return User.objects.filter(id=user_id, is_active=True).first()
    except (InvalidToken, TokenError, Exception):
        return None


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time notification push to authenticated users.
    - Path: ws/notifications/?token=<simplejwt_access_token>
    - Closes with code 4401 on missing, invalid, or expired tokens.
    - Each user joins only their own isolated notifications group (user_notifications_<user_id>).
    - Ignores inbound client messages (strictly a server-to-client push).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.group_name = None

    async def connect(self):
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        parsed_qs = urllib.parse.parse_qs(query_string)
        tokens = parsed_qs.get("token")

        if not tokens or not tokens[0]:
            logger.warning("Notification WebSocket rejected: missing token.")
            await self.close(code=4401)
            return

        raw_token = tokens[0]
        user = await get_user_from_access_token(raw_token)

        if not user:
            logger.warning("Notification WebSocket rejected: invalid or expired token.")
            await self.close(code=4401)
            return

        self.user = user
        self.group_name = f"user_notifications_{user.id}"

        # Join the user's isolated notification group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Inbound messages from clients are ignored; this channel is strictly server-to-client push.
        pass

    async def notification_message(self, event):
        """
        Handler invoked when an event is sent to the user's notification group.
        Sends a JSON event with shape: {"type": "notification", "notification": <data>}
        where <data> matches NotificationSerializer.
        """
        notification_data = event.get("notification")
        if notification_data is not None:
            await self.send_json({
                "type": "notification",
                "notification": notification_data,
            })
