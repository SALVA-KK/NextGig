from django.conf import settings
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    """
    Model representing a direct conversation between two users.
    In Phase 1, each conversation is tied to an Application and its Opportunity.
    Participants are stored canonically ordered by user id (user_one.id < user_two.id).
    """

    user_one = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations_as_user_one",
    )
    user_two = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations_as_user_two",
    )
    application = models.ForeignKey(
        "opportunities.Application",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        unique=True,
        related_name="conversation",
    )
    opportunity = models.ForeignKey(
        "opportunities.Opportunity",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    is_direct = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "chat_conversations"
        ordering = ["-last_message_at"]
        indexes = [
            models.Index(fields=["-last_message_at"], name="chat_conv_last_msg_idx"),
            models.Index(fields=["user_one", "-last_message_at"], name="chat_conv_u1_last_msg_idx"),
            models.Index(fields=["user_two", "-last_message_at"], name="chat_conv_u2_last_msg_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(user_one=models.F("user_two")),
                name="chat_conversation_different_users",
            ),
            models.UniqueConstraint(
                fields=["user_one", "user_two"],
                condition=models.Q(is_direct=True),
                name="unique_direct_conversation_per_pair",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.user_one_id and self.user_two_id:
            if self.user_one_id == self.user_two_id:
                raise ValueError("A user cannot have a conversation with themselves.")
            if self.user_one_id > self.user_two_id:
                self.user_one_id, self.user_two_id = self.user_two_id, self.user_one_id
        super().save(*args, **kwargs)

    def get_other_participant(self, user):
        """Returns the participant other than the specified user."""
        if user.id == self.user_one_id:
            return self.user_two
        return self.user_one

    def is_participant(self, user):
        """Returns True if the user is user_one or user_two."""
        return user.id in (self.user_one_id, self.user_two_id)

    def __str__(self):
        return f"Conversation #{self.id} between {self.user_one_id} and {self.user_two_id}"


class Message(models.Model):
    """
    Model representing an individual chat message in a conversation.
    """

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_chat_messages",
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "chat_messages"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"], name="chat_msg_conv_created_idx"),
        ]

    def clean(self):
        super().clean()
        stripped = (self.body or "").strip()
        if not (1 <= len(stripped) <= 2000):
            from django.core.exceptions import ValidationError
            raise ValidationError("Message body must be between 1 and 2000 characters.")
        self.body = stripped

    def save(self, *args, **kwargs):
        self.body = (self.body or "").strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Message #{self.id} from {self.sender_id} in Conv #{self.conversation_id}"


class MessageRequest(models.Model):
    """
    Model representing a student-to-student direct message request.
    Receiver must accept before a direct conversation is created.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        CANCELLED = "cancelled", "Cancelled"

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_chat_requests",
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="received_chat_requests",
    )
    intro = models.CharField(max_length=300, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    declined_at = models.DateTimeField(null=True, blank=True)
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="message_requests",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "chat_message_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["receiver", "status", "-created_at"], name="chat_req_rcvr_stat_idx"),
            models.Index(fields=["sender", "-created_at"], name="chat_req_sndr_created_idx"),
            models.Index(fields=["sender", "receiver", "-created_at"], name="chat_req_pair_created_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(sender=models.F("receiver")),
                name="chat_request_different_users",
            ),
            models.UniqueConstraint(
                fields=["sender", "receiver"],
                condition=models.Q(status="pending"),
                name="unique_pending_request_per_sender_receiver",
            ),
        ]

    def clean(self):
        super().clean()
        if self.intro:
            self.intro = self.intro.strip()
            if len(self.intro) > 300:
                from django.core.exceptions import ValidationError
                raise ValidationError("Intro cannot exceed 300 characters.")

    def save(self, *args, **kwargs):
        if self.intro:
            self.intro = self.intro.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"MessageRequest #{self.id} from {self.sender_id} to {self.receiver_id} ({self.status})"

