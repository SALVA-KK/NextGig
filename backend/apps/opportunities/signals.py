import logging
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.opportunities.models import Opportunity

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Opportunity)
def opportunity_post_save_rag_indexing(sender, instance, **kwargs):
    """
    Enqueues asynchronous vector embedding indexing whenever an open opportunity is saved.
    - Operates only when RAG_AUTO_INDEX setting is True (automatically disabled during tests).
    - Only open opportunities are enqueued.
    - Uses transaction.on_commit to guarantee the DB transaction has committed.
    - Wraps enqueue in try/except so broker/network failures never prevent saving the Opportunity.
    """
    if kwargs.get("raw", False):
        return

    if not getattr(settings, "RAG_AUTO_INDEX", True):
        return

    if instance.status != Opportunity.Status.OPEN:
        return

    opportunity_id = instance.id

    def _enqueue():
        try:
            from apps.opportunities.tasks import index_opportunity_task
            index_opportunity_task.delay(opportunity_id)
        except Exception as exc:
            logger.error(
                "Failed to enqueue index_opportunity_task for opportunity %s: %s",
                opportunity_id,
                type(exc).__name__,
            )

    transaction.on_commit(_enqueue)
