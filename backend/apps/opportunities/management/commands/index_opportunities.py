import logging
import time
from typing import List, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.common.gemini_client import (
    AIBusyError,
    AIConfigError,
    AIFailureError,
    embed_texts,
)
from apps.opportunities.embeddings import (
    OpportunityEmbedding,
    build_opportunity_document,
    compute_content_hash,
)
from apps.opportunities.models import Opportunity

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


class Command(BaseCommand):
    help = "Backfill vector embeddings for open opportunities into PostgreSQL pgvector."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-embedding of all open opportunities, ignoring cached content hashes.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate the indexing process and report statistics without calling the Gemini API or writing to the database.",
        )

    def handle(self, *args, **options):
        force = options.get("force", False)
        dry_run = options.get("dry_run", False)

        # 1. Validate configuration
        model_setting = getattr(settings, "GEMINI_EMBEDDING_MODEL", None)
        if not model_setting or not str(model_setting).strip():
            raise CommandError("GEMINI_EMBEDDING_MODEL is not configured in settings.")

        dim_setting = getattr(settings, "GEMINI_EMBEDDING_DIM", None)
        if dim_setting is None:
            raise CommandError("GEMINI_EMBEDDING_DIM is not configured in settings.")

        vector_field_dim = OpportunityEmbedding._meta.get_field("embedding").dimensions
        if dim_setting != vector_field_dim:
            raise CommandError(
                f"Configured GEMINI_EMBEDDING_DIM ({dim_setting}) does not match "
                f"OpportunityEmbedding VectorField dimensions ({vector_field_dim})."
            )

        # 2. Query open opportunities
        open_opps = list(
            Opportunity.objects.filter(status=Opportunity.Status.OPEN)
            .select_related("embedding")
            .order_by("id")
        )
        total_open = len(open_opps)
        skipped_count = Opportunity.objects.exclude(status=Opportunity.Status.OPEN).count()

        unchanged_count = 0
        to_embed: List[Tuple[Opportunity, str, str]] = []

        for opp in open_opps:
            doc = build_opportunity_document(opp)
            content_hash = compute_content_hash(doc)

            existing = getattr(opp, "embedding", None)
            if (
                not force
                and existing is not None
                and existing.content_hash == content_hash
                and existing.embedding_model == model_setting
                and existing.embedding_dim == dim_setting
            ):
                unchanged_count += 1
            else:
                to_embed.append((opp, doc, content_hash))

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"[DRY-RUN] Total open: {total_open}, Would embed: {len(to_embed)}, "
                    f"Unchanged: {unchanged_count}, Skipped (draft/closed): {skipped_count}, Failed: 0"
                )
            )
            return

        embedded_count = 0
        failed_count = 0

        # 3. Process batches of 50
        for i in range(0, len(to_embed), BATCH_SIZE):
            batch = to_embed[i : i + BATCH_SIZE]
            batch_docs = [item[1] for item in batch]

            vectors = None
            max_retries = 3
            for attempt in range(max_retries + 1):
                try:
                    vectors = embed_texts(batch_docs, task_type="RETRIEVAL_DOCUMENT")
                    break
                except AIBusyError as exc:
                    if attempt < max_retries:
                        backoff = 2 * (attempt + 1)
                        self.stdout.write(
                            self.style.WARNING(
                                f"Gemini API busy (attempt {attempt + 1}/{max_retries}). "
                                f"Retrying in {backoff}s..."
                            )
                        )
                        time.sleep(backoff)
                    else:
                        logger.error("Batch failed after retries due to AIBusyError: %s", type(exc).__name__)
                        self.stderr.write(
                            self.style.ERROR(f"Batch failed after {max_retries} retries: {type(exc).__name__}")
                        )
                except AIConfigError as exc:
                    self.stderr.write(self.style.ERROR(f"Configuration error: {type(exc).__name__}"))
                    raise CommandError(f"Embedding configuration error: {exc}")
                except AIFailureError as exc:
                    logger.error("Batch failed with AIFailureError: %s", type(exc).__name__)
                    self.stderr.write(self.style.ERROR(f"Batch failed: {type(exc).__name__}"))
                    break
                except Exception as exc:
                    logger.error("Batch failed with unexpected error: %s", type(exc).__name__)
                    self.stderr.write(self.style.ERROR(f"Batch failed: {type(exc).__name__}"))
                    break

            if vectors is None or len(vectors) != len(batch):
                failed_count += len(batch)
                continue

            for (opp, doc, content_hash), vector in zip(batch, vectors):
                OpportunityEmbedding.objects.update_or_create(
                    opportunity=opp,
                    defaults={
                        "embedding": vector,
                        "content_hash": content_hash,
                        "embedding_model": model_setting,
                        "embedding_dim": dim_setting,
                    },
                )
                embedded_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Summary: Total open: {total_open}, Embedded: {embedded_count}, "
                f"Unchanged: {unchanged_count}, Skipped: {skipped_count}, Failed: {failed_count}"
            )
        )
