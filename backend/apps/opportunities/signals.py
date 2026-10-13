import logging
from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.opportunities.models import Opportunity

logger = logging.getLogger(__name__)

OPPORTUNITY_LIST_CACHE_VERSION_KEY = "opportunity_list_cache_version"


def get_opportunity_list_cache_version() -> int:
    """
    Returns the current integer version for the public opportunity list cache.
    Initializes to 1 if not present.
    """
    try:
        from django.core.cache import cache
        version = cache.get(OPPORTUNITY_LIST_CACHE_VERSION_KEY)
        if version is None:
            version = 1
            cache.set(OPPORTUNITY_LIST_CACHE_VERSION_KEY, version, timeout=None)
        return int(version)
    except Exception as exc:
        logger.warning("Failed to get opportunity list cache version: %s", exc)
        return 1


def bump_opportunity_list_cache_version():
    """
    Increments the version key for the public opportunity list cache.
    Any cached opportunity lists with previous versions are immediately bypassed.
    """
    try:
        from django.core.cache import cache
        try:
            cache.incr(OPPORTUNITY_LIST_CACHE_VERSION_KEY)
        except ValueError:
            cache.set(OPPORTUNITY_LIST_CACHE_VERSION_KEY, 2, timeout=None)
    except Exception as exc:
        logger.warning("Failed to bump opportunity list cache version: %s", exc)


@receiver(post_save, sender=Opportunity)
def opportunity_post_save_cache_invalidation(sender, instance, **kwargs):
    """
    Invalidates the public opportunity list cache when an Opportunity is saved.
    Keeps raw=True guard for fixtures/loaddata.
    """
    if kwargs.get("raw", False):
        return
    bump_opportunity_list_cache_version()


@receiver(post_delete, sender=Opportunity)
def opportunity_post_delete_cache_invalidation(sender, instance, **kwargs):
    """
    Invalidates the public opportunity list cache when an Opportunity is deleted.
    Keeps raw=True guard for fixtures/loaddata.
    """
    if kwargs.get("raw", False):
        return
    bump_opportunity_list_cache_version()


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
