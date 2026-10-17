from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

from apps.chat.models import Conversation, Message, MessageRequest


class Command(BaseCommand):
    help = "Merge duplicate conversations between the same pair of users into a single conversation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            default=False,
            help="Apply changes to the database. By default, command runs in dry-run mode.",
        )

    def handle(self, *args, **options):
        apply = options["apply"]

        dup_pairs = (
            Conversation.objects.values("user_one_id", "user_two_id")
            .annotate(cnt=Count("id"))
            .filter(cnt__gt=1)
        )

        total_pairs = dup_pairs.count()
        if total_pairs == 0:
            self.stdout.write("No duplicate conversations found.")
            return

        mode_label = "APPLY" if apply else "DRY-RUN"
        self.stdout.write(f"Found {total_pairs} pair(s) with duplicate conversations. Running in {mode_label} mode.")

        total_merged_conversations = 0
        total_moved_messages = 0
        total_repointed_requests = 0

        for pair in dup_pairs:
            u1_id = pair["user_one_id"]
            u2_id = pair["user_two_id"]

            with transaction.atomic():
                convs = list(
                    Conversation.objects.filter(user_one_id=u1_id, user_two_id=u2_id).order_by("id")
                )
                if len(convs) <= 1:
                    continue

                kept = convs[0]
                dupes = convs[1:]
                dupe_ids = [d.id for d in dupes]
                any_direct = any(c.is_direct for c in convs)

                msg_count = Message.objects.filter(conversation_id__in=dupe_ids).count()
                req_count = MessageRequest.objects.filter(conversation_id__in=dupe_ids).count()

                if apply:
                    # 1. Repoint messages, preserving each message's created_at and read_at
                    Message.objects.filter(conversation_id__in=dupe_ids).update(conversation=kept)

                    # 2. Repoint message requests
                    MessageRequest.objects.filter(conversation_id__in=dupe_ids).update(conversation=kept)

                    # 3. Find latest message time for kept conversation
                    latest_msg = (
                        Message.objects.filter(conversation=kept).order_by("-created_at", "-id").first()
                    )
                    latest_time = latest_msg.created_at if latest_msg else kept.created_at

                    # 4. Delete duplicate conversations FIRST so partial unique constraint is never violated
                    Conversation.objects.filter(id__in=dupe_ids).delete()

                    # 5. Update kept conversation
                    update_fields = ["last_message_at"]
                    kept.last_message_at = latest_time
                    if any_direct and not kept.is_direct:
                        kept.is_direct = True
                        update_fields.append("is_direct")
                    kept.save(update_fields=update_fields)
                else:
                    transaction.set_rollback(True)

                total_merged_conversations += len(dupes)
                total_moved_messages += msg_count
                total_repointed_requests += req_count

                self.stdout.write(
                    f"Pair ({u1_id}, {u2_id}): kept conversation {kept.id}, merged {len(dupes)} duplicate(s) ({dupe_ids}), "
                    f"moved {msg_count} message(s), repointed {req_count} request(s)"
                    f"{' [DRY-RUN]' if not apply else ''}"
                )

        if apply:
            self.stdout.write(
                f"Merge completed: processed {total_pairs} pair(s), removed {total_merged_conversations} duplicate conversation(s), "
                f"moved {total_moved_messages} message(s), repointed {total_repointed_requests} request(s)."
            )
        else:
            self.stdout.write(
                f"DRY-RUN completed: {total_pairs} pair(s) would be merged, {total_merged_conversations} duplicate conversation(s) would be removed. "
                "No changes were committed. Run with --apply to apply changes."
            )
