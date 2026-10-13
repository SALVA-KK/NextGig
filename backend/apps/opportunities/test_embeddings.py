import datetime
import math
from io import StringIO
from unittest.mock import MagicMock, patch

from celery.exceptions import Retry
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import DatabaseError, DataError, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.common.gemini_client import (
    AIConfigError,
    AIBusyError,
    AIFailureError,
    embed_texts,
)
from apps.opportunities.embeddings import (
    OpportunityEmbedding,
    build_opportunity_document,
    compute_content_hash,
    index_opportunity,
)
from apps.opportunities.models import Opportunity
from apps.opportunities.tasks import index_opportunity_task

User = get_user_model()


@override_settings(
    GOOGLE_API_KEY="test-key",
    GEMINI_EMBEDDING_MODEL="test-model",
    GEMINI_EMBEDDING_DIM=768,
    RAG_AUTO_INDEX=False,
)
class OpportunityEmbeddingUnitTestCase(TestCase):
    def setUp(self):
        self.poster = User.objects.create_user(
            email="super_secret_poster_123@example.com",
            password="Password123!",
            full_name="Super Secret Poster Name",
            role=User.Role.PROVIDER,
            is_verified=True,
        )
        self.opportunity = Opportunity.objects.create(
            poster=self.poster,
            title="Senior Backend Python Engineer",
            category=Opportunity.Category.FULL_TIME,
            description="We are looking for a skilled Django backend engineer.",
            required_skills=["Python", "Django", "PostgreSQL"],
            city="Kochi",
            work_mode=Opportunity.WorkMode.REMOTE,
            location_text="Infopark Phase 2",
            duration="Permanent",
            working_hours="40 hours per week",
            pay_type=Opportunity.PayType.MONTHLY,
            pay_amount=150000.00,
            vacancies=2,
            deadline=timezone.localdate() + datetime.timedelta(days=14),
            contact_info="SECRET_PHONE_9876543210",
            status=Opportunity.Status.OPEN,
        )

    # ---------------------------------------------------------
    # Document Builder & Content Hash Tests
    # ---------------------------------------------------------

    def test_document_never_contains_contact_info_poster_details_or_pay(self):
        """
        Document must never contain contact_info, poster details, or pay_amount.
        """
        doc = build_opportunity_document(self.opportunity)

        # Assert private/confidential values are NEVER included
        self.assertNotIn("SECRET_PHONE_9876543210", doc)
        self.assertNotIn("super_secret_poster_123@example.com", doc)
        self.assertNotIn("Super Secret Poster Name", doc)
        self.assertNotIn("150000", doc)

        # Assert public opportunity descriptors are included
        self.assertIn("Senior Backend Python Engineer", doc)
        self.assertIn("Django backend engineer", doc)
        self.assertIn("Python, Django, PostgreSQL", doc)
        self.assertIn("Kochi", doc)
        self.assertIn("Remote", doc)
        self.assertIn("Infopark Phase 2", doc)
        self.assertIn("Permanent", doc)
        self.assertIn("40 hours per week", doc)

    def test_content_hash_consistency_and_status_deadline_independence(self):
        """
        Same content produces identical hash.
        Changing only status or deadline produces identical hash.
        Changing core text content (e.g. description) produces a different hash.
        """
        doc1 = build_opportunity_document(self.opportunity)
        hash1 = compute_content_hash(doc1)
        self.assertEqual(len(hash1), 64)

        # Same content -> same hash
        doc2 = build_opportunity_document(self.opportunity)
        hash2 = compute_content_hash(doc2)
        self.assertEqual(hash1, hash2)

        # Changing only status and deadline -> same hash
        self.opportunity.status = Opportunity.Status.CLOSED
        self.opportunity.deadline = timezone.localdate() + datetime.timedelta(days=60)
        self.opportunity.save()
        doc3 = build_opportunity_document(self.opportunity)
        hash3 = compute_content_hash(doc3)
        self.assertEqual(hash1, hash3)

        # Changing description -> different hash
        self.opportunity.description = "Completely rewritten job description text."
        self.opportunity.save()
        doc4 = build_opportunity_document(self.opportunity)
        hash4 = compute_content_hash(doc4)
        self.assertNotEqual(hash1, hash4)

    # ---------------------------------------------------------
    # embed_texts Hermetic Tests & SDK Parameter Assertions
    # ---------------------------------------------------------

    @patch("apps.common.gemini_client.genai.Client")
    def test_embed_texts_batching_and_config_parameters(self, mock_client_cls):
        """
        embed_texts chunks batches within limit (50 per batch).
        125 texts should result in 3 API calls (50, 50, 25).
        Asserts task_type and output_dimensionality are passed accurately.
        """
        mock_client = mock_client_cls.return_value

        def mock_embed(model, contents, config):
            resp = MagicMock()
            embs = []
            for _ in contents:
                emb = MagicMock()
                emb.values = [1.0] * 768
                embs.append(emb)
            resp.embeddings = embs
            return resp

        mock_client.models.embed_content.side_effect = mock_embed

        texts = [f"Text item {i}" for i in range(125)]
        results = embed_texts(texts, task_type="RETRIEVAL_DOCUMENT")

        self.assertEqual(len(results), 125)
        self.assertEqual(mock_client.models.embed_content.call_count, 3)

        # Assert task_type and output_dimensionality=768 in call config
        first_call_config = mock_client.models.embed_content.call_args_list[0].kwargs["config"]
        self.assertEqual(first_call_config.task_type, "RETRIEVAL_DOCUMENT")
        self.assertEqual(first_call_config.output_dimensionality, 768)

    @patch("apps.common.gemini_client.genai.Client")
    def test_embed_texts_l2_normalization_zero_vector_and_query_task_type(self, mock_client_cls):
        """
        embed_texts normalizes vectors to unit L2 length (~1.0).
        Zero vectors are handled safely without division by zero.
        Asserts RETRIEVAL_QUERY task_type is accurately passed.
        """
        mock_client = mock_client_cls.return_value

        emb1 = MagicMock()
        emb1.values = [3.0, 4.0] + [0.0] * 764  # norm = 5.0

        emb2 = MagicMock()
        emb2.values = [0.0] * 768  # zero vector

        resp = MagicMock()
        resp.embeddings = [emb1, emb2]
        mock_client.models.embed_content.return_value = resp

        results = embed_texts(["vec1", "vec2"], task_type="RETRIEVAL_QUERY")
        self.assertEqual(len(results), 2)

        # Assert RETRIEVAL_QUERY task_type in config
        call_config = mock_client.models.embed_content.call_args_list[0].kwargs["config"]
        self.assertEqual(call_config.task_type, "RETRIEVAL_QUERY")
        self.assertEqual(call_config.output_dimensionality, 768)

        # Check vector 1 norm is ~1.0
        norm1 = math.sqrt(sum(x * x for x in results[0]))
        self.assertTrue(math.isclose(norm1, 1.0, rel_tol=1e-5))
        self.assertAlmostEqual(results[0][0], 0.6)
        self.assertAlmostEqual(results[0][1], 0.8)

        # Check zero vector returns zeros safely
        self.assertEqual(results[1], [0.0] * 768)

    @patch("apps.common.gemini_client.genai.Client")
    def test_embed_texts_error_mapping(self, mock_client_cls):
        """
        Busy errors map to AIBusyError, failure errors map to AIFailureError.
        """
        mock_client = mock_client_cls.return_value

        # 1. 503 Busy error -> AIBusyError
        busy_exc = Exception("503 Service Unavailable")
        setattr(busy_exc, "code", 503)
        mock_client.models.embed_content.side_effect = busy_exc
        with self.assertRaises(AIBusyError):
            embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")

        # 2. 400 Bad Request -> AIFailureError
        fail_exc = Exception("400 Bad Request")
        setattr(fail_exc, "code", 400)
        mock_client.models.embed_content.side_effect = fail_exc
        with self.assertRaises(AIFailureError):
            embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")

        # 3. Incomplete response -> AIFailureError
        empty_resp = MagicMock()
        empty_resp.embeddings = []
        mock_client.models.embed_content.side_effect = None
        mock_client.models.embed_content.return_value = empty_resp
        with self.assertRaises(AIFailureError):
            embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")

    @patch("apps.common.gemini_client.genai.Client")
    def test_embed_texts_timeout_parameter_and_default(self, mock_client_cls):
        """
        embed_texts passes timeout in milliseconds to HttpOptions.
        When timeout is omitted, defaults to 20000ms (20s).
        When custom timeout is passed, uses timeout * 1000ms.
        Non-positive timeout raises ValueError.
        """
        mock_client = mock_client_cls.return_value
        resp = MagicMock()
        emb = MagicMock()
        emb.values = [1.0] * 768
        resp.embeddings = [emb]
        mock_client.models.embed_content.return_value = resp

        # Default timeout
        embed_texts(["item"], task_type="RETRIEVAL_DOCUMENT")
        default_config = mock_client.models.embed_content.call_args.kwargs["config"]
        self.assertEqual(default_config.http_options.timeout, 20000)

        # Custom timeout
        mock_client.models.embed_content.reset_mock()
        embed_texts(["item"], task_type="RETRIEVAL_DOCUMENT", timeout=5)
        custom_config = mock_client.models.embed_content.call_args.kwargs["config"]
        self.assertEqual(custom_config.http_options.timeout, 5000)

        # Non-positive timeout raises ValueError
        with self.assertRaises(ValueError):
            embed_texts(["item"], task_type="RETRIEVAL_DOCUMENT", timeout=0)
        with self.assertRaises(ValueError):
            embed_texts(["item"], task_type="RETRIEVAL_DOCUMENT", timeout=-2)

    @patch("apps.common.gemini_client.genai.Client")
    def test_embed_texts_timeout_exception_surfaces_as_ai_busy_error(self, mock_client_cls):
        """
        A timeout exception raised by the underlying transport surfaces as AIBusyError.
        """
        import httpx
        mock_client = mock_client_cls.return_value
        mock_client.models.embed_content.side_effect = httpx.ReadTimeout("Connection timed out")

        with self.assertRaises(AIBusyError):
            embed_texts(["item"], task_type="RETRIEVAL_QUERY", timeout=5)

        mock_client.models.embed_content.side_effect = TimeoutError("Deadline exceeded")
        with self.assertRaises(AIBusyError):
            embed_texts(["item"], task_type="RETRIEVAL_QUERY", timeout=5)


    def test_missing_gemini_embedding_model_or_dim_raises_clear_error(self):
        """
        Missing GEMINI_EMBEDDING_MODEL or GEMINI_EMBEDDING_DIM raises AIConfigError.
        """
        with override_settings(GEMINI_EMBEDDING_MODEL=None):
            with self.assertRaises(AIConfigError) as ctx:
                embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")
            self.assertIn("model", str(ctx.exception).lower())

        with override_settings(GEMINI_EMBEDDING_MODEL=""):
            with self.assertRaises(AIConfigError):
                embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")

        with override_settings(GEMINI_EMBEDDING_DIM=None):
            with self.assertRaises(AIConfigError) as ctx:
                embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")
            self.assertIn("dimension", str(ctx.exception).lower())

        with override_settings(GEMINI_EMBEDDING_DIM="invalid"):
            with self.assertRaises(AIConfigError):
                embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")

        with override_settings(GOOGLE_API_KEY=""):
            with self.assertRaises(AIConfigError) as ctx:
                embed_texts(["hello"], task_type="RETRIEVAL_DOCUMENT")
            self.assertIn("key", str(ctx.exception).lower())

    # ---------------------------------------------------------
    # OpportunityEmbedding Model & DB Tests
    # ---------------------------------------------------------

    def test_opportunity_embedding_model_db_storage_and_cascade_delete(self):
        """
        Saving a 768-dim vector works.
        Saving a vector with wrong dimensions fails at the DB level.
        Deleting the Opportunity deletes its embedding row.
        """
        vec_768 = [0.001] * 768
        content_hash = compute_content_hash(build_opportunity_document(self.opportunity))

        embedding_record = OpportunityEmbedding.objects.create(
            opportunity=self.opportunity,
            embedding=vec_768,
            content_hash=content_hash,
            embedding_model="test-model",
            embedding_dim=768,
        )

        reloaded = OpportunityEmbedding.objects.get(id=embedding_record.id)
        self.assertEqual(len(reloaded.embedding), 768)
        self.assertEqual(self.opportunity.embedding.id, embedding_record.id)

        # Saving wrong dimension fails at the DB level
        opp2 = Opportunity.objects.create(
            poster=self.poster,
            title="Second Opportunity",
            category=Opportunity.Category.INTERNSHIP,
            description="Testing wrong dimension",
            pay_type=Opportunity.PayType.UNPAID,
            work_mode=Opportunity.WorkMode.REMOTE,
        )

        with transaction.atomic():
            with self.assertRaises((DataError, DatabaseError)):
                OpportunityEmbedding.objects.create(
                    opportunity=opp2,
                    embedding=[0.1, 0.2, 0.3],  # 3 dimensions instead of 768
                    content_hash="somehash",
                    embedding_model="test-model",
                    embedding_dim=768,
                )

        # Deleting the Opportunity cascades and deletes the OpportunityEmbedding record
        opp_id = self.opportunity.id
        self.opportunity.delete()
        self.assertFalse(OpportunityEmbedding.objects.filter(opportunity_id=opp_id).exists())

    # ---------------------------------------------------------
    # Core Function: index_opportunity Tests
    # ---------------------------------------------------------

    @patch("apps.opportunities.embeddings.embed_texts", return_value=[[0.05] * 768])
    def test_index_opportunity_embeds_new_open_opportunity(self, mock_embed):
        """
        index_opportunity embeds an open opportunity that does not have an embedding.
        """
        res = index_opportunity(self.opportunity)
        self.assertEqual(res, "embedded")
        self.assertEqual(mock_embed.call_count, 1)

        embedding = OpportunityEmbedding.objects.get(opportunity=self.opportunity)
        self.assertEqual(len(embedding.embedding), 768)
        self.assertEqual(embedding.embedding_model, "test-model")
        self.assertEqual(embedding.embedding_dim, 768)

    @patch("apps.opportunities.embeddings.embed_texts", return_value=[[0.05] * 768])
    def test_indexing_path_uses_default_timeout(self, mock_embed):
        """
        index_opportunity calls embed_texts without specifying a custom timeout,
        preserving the default (longer) timeout.
        """
        res = index_opportunity(self.opportunity)
        self.assertEqual(res, "embedded")
        mock_embed.assert_called_once()
        self.assertNotIn("timeout", mock_embed.call_args.kwargs)

    @patch("apps.opportunities.embeddings.embed_texts", return_value=[[0.05] * 768])

    def test_index_opportunity_returns_unchanged_when_hash_matches(self, mock_embed):
        """
        When content hash, model, and dim match, returns 'unchanged' without calling embed_texts.
        """
        # First call embeds
        index_opportunity(self.opportunity)
        mock_embed.reset_mock()

        # Second call returns unchanged without calling API
        res = index_opportunity(self.opportunity)
        self.assertEqual(res, "unchanged")
        mock_embed.assert_not_called()

    @patch("apps.opportunities.embeddings.embed_texts", return_value=[[0.05] * 768])
    def test_index_opportunity_reembeds_when_description_changes_one_row(self, mock_embed):
        """
        When description changes, content hash differs -> re-embeds, maintaining exactly 1 row.
        """
        index_opportunity(self.opportunity)
        self.assertEqual(OpportunityEmbedding.objects.filter(opportunity=self.opportunity).count(), 1)

        # Change description
        self.opportunity.description = "Updated engineering role description."
        self.opportunity.save()

        mock_embed.reset_mock()
        res = index_opportunity(self.opportunity)
        self.assertEqual(res, "embedded")
        self.assertEqual(mock_embed.call_count, 1)
        self.assertEqual(OpportunityEmbedding.objects.filter(opportunity=self.opportunity).count(), 1)

    @patch("apps.opportunities.embeddings.embed_texts")
    def test_index_opportunity_skips_draft_and_closed(self, mock_embed):
        """
        Draft and closed opportunities are skipped without calling embed_texts.
        """
        self.opportunity.status = Opportunity.Status.DRAFT
        self.opportunity.save()
        res_draft = index_opportunity(self.opportunity)
        self.assertEqual(res_draft, "skipped")

        self.opportunity.status = Opportunity.Status.CLOSED
        self.opportunity.save()
        res_closed = index_opportunity(self.opportunity)
        self.assertEqual(res_closed, "skipped")

        mock_embed.assert_not_called()

    @patch("apps.opportunities.embeddings.embed_texts", return_value=[[0.05] * 768])
    def test_index_opportunity_reembeds_when_model_differs(self, mock_embed):
        """
        When the stored embedding_model differs from settings, it re-embeds.
        """
        index_opportunity(self.opportunity)
        mock_embed.reset_mock()

        with override_settings(GEMINI_EMBEDDING_MODEL="new-v2-model"):
            res = index_opportunity(self.opportunity)
            self.assertEqual(res, "embedded")
            self.assertEqual(mock_embed.call_count, 1)
            emb = OpportunityEmbedding.objects.get(opportunity=self.opportunity)
            self.assertEqual(emb.embedding_model, "new-v2-model")

    def test_index_opportunity_dimension_guard_raises_ai_config_error(self):
        """
        If GEMINI_EMBEDDING_DIM does not match VectorField's 768 dimensions, raises AIConfigError.
        """
        with override_settings(GEMINI_EMBEDDING_DIM=1536):
            with self.assertRaises(AIConfigError) as ctx:
                index_opportunity(self.opportunity)
            self.assertIn("dimensions", str(ctx.exception).lower())

    # ---------------------------------------------------------
    # Celery Task: index_opportunity_task Tests
    # ---------------------------------------------------------

    @patch.object(index_opportunity_task, "retry", side_effect=Retry())
    @patch("apps.opportunities.tasks.index_opportunity", side_effect=AIBusyError("Service busy"))
    def test_task_retries_on_ai_busy_error(self, mock_index, mock_retry):
        """
        Task retries with exponential backoff ONLY on AIBusyError.
        """
        with self.assertRaises(Retry):
            index_opportunity_task(self.opportunity.id)
        self.assertTrue(mock_retry.called)
        self.assertEqual(mock_retry.call_args.kwargs["countdown"], 5)

    @patch("apps.opportunities.tasks.index_opportunity", side_effect=AIConfigError("Invalid model"))
    def test_task_does_not_retry_on_ai_config_error(self, mock_index):
        """
        Task does NOT retry on AIConfigError; logs and finishes with 'failed'.
        """
        res = index_opportunity_task(self.opportunity.id)
        self.assertEqual(res, "failed")

    @patch("apps.opportunities.tasks.index_opportunity", side_effect=AIFailureError("Malformed response"))
    def test_task_does_not_retry_on_ai_failure_error(self, mock_index):
        """
        Task does NOT retry on AIFailureError; logs and finishes with 'failed'.
        """
        res = index_opportunity_task(self.opportunity.id)
        self.assertEqual(res, "failed")

    def test_task_handles_deleted_opportunity_quietly(self):
        """
        Task handles a non-existent/deleted opportunity ID quietly without raising exceptions.
        """
        res = index_opportunity_task(9999999)
        self.assertEqual(res, "not_found")

    # ---------------------------------------------------------
    # Signal Tests (post_save on Opportunity)
    # ---------------------------------------------------------

    @override_settings(RAG_AUTO_INDEX=True)
    @patch("apps.opportunities.tasks.index_opportunity_task.delay")
    def test_signal_enqueues_on_create_and_edit_of_open_opportunity(self, mock_delay):
        """
        Signal enqueues on create and on edit of an open opportunity via transaction.on_commit.
        """
        with self.captureOnCommitCallbacks(execute=True):
            new_opp = Opportunity.objects.create(
                poster=self.poster,
                title="Newly Posted Open Gig",
                category=Opportunity.Category.FREELANCE,
                pay_type=Opportunity.PayType.HOURLY,
                status=Opportunity.Status.OPEN,
            )
        mock_delay.assert_called_with(new_opp.id)

        mock_delay.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            new_opp.title = "Updated Title"
            new_opp.save()
        mock_delay.assert_called_with(new_opp.id)

    @override_settings(RAG_AUTO_INDEX=True)
    @patch("apps.opportunities.tasks.index_opportunity_task.delay")
    def test_signal_does_not_enqueue_for_draft(self, mock_delay):
        """
        Signal does not enqueue indexing for draft opportunities.
        """
        with self.captureOnCommitCallbacks(execute=True):
            Opportunity.objects.create(
                poster=self.poster,
                title="Draft Opportunity",
                category=Opportunity.Category.FREELANCE,
                pay_type=Opportunity.PayType.HOURLY,
                status=Opportunity.Status.DRAFT,
            )
        mock_delay.assert_not_called()

    @override_settings(RAG_AUTO_INDEX=True)
    @patch("apps.opportunities.tasks.index_opportunity_task.delay", side_effect=Exception("Redis connection error"))
    def test_signal_failing_delay_does_not_break_saving(self, mock_delay):
        """
        A broker or Redis failure when calling .delay never prevents saving the Opportunity.
        """
        with self.captureOnCommitCallbacks(execute=True):
            saved_opp = Opportunity.objects.create(
                poster=self.poster,
                title="Resilient Opportunity",
                category=Opportunity.Category.FULL_TIME,
                pay_type=Opportunity.PayType.MONTHLY,
                status=Opportunity.Status.OPEN,
            )
        self.assertIsNotNone(saved_opp.id)
        self.assertTrue(Opportunity.objects.filter(id=saved_opp.id).exists())

    @override_settings(RAG_AUTO_INDEX=True)
    @patch("apps.opportunities.tasks.index_opportunity_task.delay")
    def test_signal_ignores_raw_true_saves(self, mock_delay):
        """
        Signal handler immediately returns without enqueuing when raw=True (e.g. loaddata).
        """
        from apps.opportunities.signals import opportunity_post_save_rag_indexing

        with self.captureOnCommitCallbacks(execute=True):
            opportunity_post_save_rag_indexing(
                sender=Opportunity,
                instance=self.opportunity,
                raw=True,
            )
        mock_delay.assert_not_called()

    # ---------------------------------------------------------
    # Backfill Command: index_opportunities Tests
    # ---------------------------------------------------------

    @patch("apps.opportunities.management.commands.index_opportunities.embed_texts")
    def test_backfill_command_dry_run_makes_no_api_calls(self, mock_embed):
        """
        --dry-run simulates the indexing without calling the Gemini API.
        """
        out = StringIO()
        call_command("index_opportunities", "--dry-run", stdout=out)
        mock_embed.assert_not_called()
        self.assertIn("[DRY-RUN]", out.getvalue())
        self.assertIn("Would embed: 1", out.getvalue())

    @patch(
        "apps.opportunities.management.commands.index_opportunities.embed_texts",
        return_value=[[0.05] * 768],
    )
    def test_backfill_command_embeds_and_second_run_embeds_zero(self, mock_embed):
        """
        First run embeds open opportunities; second run embeds 0 (all unchanged).
        """
        out1 = StringIO()
        call_command("index_opportunities", stdout=out1)
        self.assertIn("Embedded: 1", out1.getvalue())
        self.assertEqual(mock_embed.call_count, 1)

        # Second run
        mock_embed.reset_mock()
        out2 = StringIO()
        call_command("index_opportunities", stdout=out2)
        self.assertIn("Embedded: 0", out2.getvalue())
        self.assertIn("Unchanged: 1", out2.getvalue())
        mock_embed.assert_not_called()

    @patch(
        "apps.opportunities.management.commands.index_opportunities.embed_texts",
        return_value=[[0.05] * 768],
    )
    def test_backfill_command_force_reembeds(self, mock_embed):
        """
        --force re-embeds open opportunities even if content hash matches.
        """
        # Populate first
        call_command("index_opportunities", stdout=StringIO())

        mock_embed.reset_mock()
        out = StringIO()
        call_command("index_opportunities", "--force", stdout=out)
        self.assertIn("Embedded: 1", out.getvalue())
        self.assertEqual(mock_embed.call_count, 1)

    @patch("apps.opportunities.management.commands.index_opportunities.embed_texts")
    def test_backfill_command_batch_failure_reported_and_continues(self, mock_embed):
        """
        Batch failure is reported in summary and execution continues.
        """
        mock_embed.side_effect = AIFailureError("Model quota exceeded")
        out = StringIO()
        err = StringIO()
        call_command("index_opportunities", stdout=out, stderr=err)
        self.assertIn("Failed: 1", out.getvalue())
        self.assertIn("Batch failed", err.getvalue())
