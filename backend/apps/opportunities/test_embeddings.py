import datetime
import math
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.db import DatabaseError, DataError
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
)
from apps.opportunities.models import Opportunity

User = get_user_model()


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

    @patch("apps.common.gemini_client.genai.Client")
    def test_embed_texts_batching(self, mock_client_cls):
        """
        embed_texts chunks batches within limit (50 per batch).
        125 texts should result in 3 API calls (50, 50, 25).
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

    @patch("apps.common.gemini_client.genai.Client")
    def test_embed_texts_l2_normalization_and_zero_vector(self, mock_client_cls):
        """
        embed_texts normalizes vectors to unit L2 length (~1.0).
        Zero vectors are handled safely without division by zero.
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

    def test_opportunity_embedding_model_db_storage_and_cascade_delete(self):
        """
        Saving a 768-dim vector works.
        Saving a vector with wrong dimensions fails.
        Deleting the Opportunity deletes its embedding row.
        """
        from django.db import transaction

        vec_768 = [0.001] * 768
        content_hash = compute_content_hash(build_opportunity_document(self.opportunity))

        embedding_record = OpportunityEmbedding.objects.create(
            opportunity=self.opportunity,
            embedding=vec_768,
            content_hash=content_hash,
            embedding_model="gemini-embedding-001",
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
                    embedding_model="gemini-embedding-001",
                    embedding_dim=768,
                )

        # Deleting the Opportunity cascades and deletes the OpportunityEmbedding record
        opp_id = self.opportunity.id
        self.opportunity.delete()
        self.assertFalse(OpportunityEmbedding.objects.filter(opportunity_id=opp_id).exists())
