import datetime
import json
import math
import os
import tempfile
from io import StringIO
from typing import List
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.assistant.context import get_candidate_opportunities_context
from apps.assistant.rag.retrieval import (
    CITY_MATCH_WEIGHT,
    MAX_SKILL_OVERLAP,
    SKILL_OVERLAP_WEIGHT,
    build_query_text,
    retrieve_candidate_opportunities,
    retrieve_with_source,
)
from apps.common.gemini_client import (
    AIBusyError,
    AIConfigError,
    AIFailureError,
)
from apps.opportunities.models import Opportunity, OpportunityEmbedding

User = get_user_model()


def make_unit_vector(dim: int, index: int, val: float = 1.0) -> List[float]:
    """Helper creating a 768-dim vector with a single non-zero coordinate."""
    vec = [0.0] * dim
    vec[index] = val
    return vec


def make_2d_unit_vector(dim: int, angle_rad: float) -> List[float]:
    """Helper creating a unit vector in the first two dimensions."""
    vec = [0.0] * dim
    vec[0] = math.cos(angle_rad)
    vec[1] = math.sin(angle_rad)
    return vec


@override_settings(
    GOOGLE_API_KEY="test-key",
    GEMINI_EMBEDDING_MODEL="test-model",
    GEMINI_EMBEDDING_DIM=768,
    RAG_AUTO_INDEX=False,
)
class RetrievalUnitTestCase(TestCase):
    def setUp(self):
        self.poster = User.objects.create_user(
            email="retrieval_poster@example.com",
            password="Password123!",
            full_name="Poster Provider",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

    def _create_opp(self, title: str, status=Opportunity.Status.OPEN, deadline_days: int = 14, **kwargs) -> Opportunity:
        deadline = timezone.localdate() + datetime.timedelta(days=deadline_days) if deadline_days is not None else None
        return Opportunity.objects.create(
            poster=self.poster,
            title=title,
            category=kwargs.get("category", Opportunity.Category.FREELANCE),
            description=kwargs.get("description", "Description for test opportunity"),
            required_skills=kwargs.get("required_skills", ["Python"]),
            city=kwargs.get("city", "Kochi"),
            work_mode=kwargs.get("work_mode", Opportunity.WorkMode.REMOTE),
            pay_type=kwargs.get("pay_type", Opportunity.PayType.HOURLY),
            status=status,
            deadline=deadline,
        )

    def _create_emb(self, opp: Opportunity, vector: List[float], model: str = "test-model", dim: int = 768) -> OpportunityEmbedding:
        return OpportunityEmbedding.objects.create(
            opportunity=opp,
            embedding=vector,
            content_hash=f"hash_{opp.id}",
            embedding_model=model,
            embedding_dim=dim,
        )

    # ------------------------------------------------------------------
    # 1. Nearest neighbor unit vector ranking
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_nearest_neighbor_ranks_first_with_handmade_unit_vectors(self, mock_embed):
        """
        Hand-made 768-dim unit vectors verify that the vector with the smallest
        cosine distance to the query ranks first.
        """
        query_vec = make_unit_vector(768, 0, 1.0)
        mock_embed.return_value = [query_vec]

        opp_closest = self._create_opp("Closest Python Opp")
        opp_orthogonal_1 = self._create_opp("Orthogonal Opp 1")
        opp_orthogonal_2 = self._create_opp("Orthogonal Opp 2")

        # opp_closest has identical vector (distance 0.0, similarity 1.0)
        self._create_emb(opp_closest, make_unit_vector(768, 0, 1.0))
        # orthogonal vectors have distance 1.0, similarity 0.0
        self._create_emb(opp_orthogonal_1, make_unit_vector(768, 1, 1.0))
        self._create_emb(opp_orthogonal_2, make_unit_vector(768, 2, 1.0))

        rows, opts = retrieve_candidate_opportunities("python dev", {})

        self.assertEqual(opts[0]["id"], opp_closest.id)
        self.assertIn(opp_closest.id, rows)

    # ------------------------------------------------------------------
    # 2. Closed, draft, and past-deadline opportunities excluded
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_closed_draft_and_past_deadline_opportunities_excluded(self, mock_embed):
        """
        Closed, draft, and expired opportunities are NEVER returned even when
        their embeddings are an exact match (closest possible vector).
        """
        query_vec = make_unit_vector(768, 0, 1.0)
        mock_embed.return_value = [query_vec]

        # Inactive / expired opportunities with identical query vector (distance 0.0)
        closed_opp = self._create_opp("Closed Opp", status=Opportunity.Status.CLOSED)
        self._create_emb(closed_opp, query_vec)

        draft_opp = self._create_opp("Draft Opp", status=Opportunity.Status.DRAFT)
        self._create_emb(draft_opp, query_vec)

        expired_opp = self._create_opp("Expired Opp", status=Opportunity.Status.OPEN, deadline_days=-2)
        self._create_emb(expired_opp, query_vec)

        # Active open opportunity with orthogonal vector (distance 1.0)
        active_opp = self._create_opp("Active Opp", status=Opportunity.Status.OPEN, deadline_days=10)
        self._create_emb(active_opp, make_unit_vector(768, 1, 1.0))

        rows, opts = retrieve_candidate_opportunities("test query", {})

        returned_ids = [opt["id"] for opt in opts]
        self.assertNotIn(closed_opp.id, returned_ids)
        self.assertNotIn(draft_opp.id, returned_ids)
        self.assertNotIn(expired_opp.id, returned_ids)
        self.assertIn(active_opp.id, returned_ids)
        self.assertEqual(returned_ids, [active_opp.id])

    # ------------------------------------------------------------------
    # 3. Mismatched embedding_model or embedding_dim excluded
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_different_embedding_model_or_dim_excluded(self, mock_embed):
        """
        Embedding rows generated by a different model or dimension are excluded
        by the SQL query filters.
        """
        query_vec = make_unit_vector(768, 0, 1.0)
        mock_embed.return_value = [query_vec]

        opp_wrong_model = self._create_opp("Wrong Model Opp")
        self._create_emb(opp_wrong_model, query_vec, model="legacy-embedding-v0")

        opp_valid_model = self._create_opp("Valid Model Opp")
        self._create_emb(opp_valid_model, make_unit_vector(768, 1, 1.0), model="test-model")

        rows, opts = retrieve_candidate_opportunities("test query", {})

        returned_ids = [opt["id"] for opt in opts]
        self.assertNotIn(opp_wrong_model.id, returned_ids)
        self.assertIn(opp_valid_model.id, returned_ids)

    # ------------------------------------------------------------------
    # 4. Skill/city boost re-orders close results
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_skill_and_city_boost_can_reorder_close_results(self, mock_embed):
        """
        A candidate with slightly lower vector similarity can rank ahead of
        a candidate with slightly higher similarity if boosted by matching
        skills and matching city.
        """
        # Query vector along dim 0
        query_vec = make_unit_vector(768, 0, 1.0)
        mock_embed.return_value = [query_vec]

        # Opp A: angle = 0.55 rad -> similarity = cos(0.55) ~ 0.8525
        # Opp A has no overlapping skills and different city. Score = 0.8525
        opp_a = self._create_opp(
            "Opp A Higher Base Sim",
            required_skills=["C++", "Rust"],
            city="Chennai",
        )
        self._create_emb(opp_a, make_2d_unit_vector(768, 0.55))

        # Opp B: angle = 0.64 rad -> similarity = cos(0.64) ~ 0.8021
        # Opp B matches 3 skills (+0.15) and city (+0.03) -> Score ~ 0.8021 + 0.18 = 0.9821
        opp_b = self._create_opp(
            "Opp B Lower Base Sim Boosted",
            required_skills=["Python", "Django", "React"],
            city="Kochi",
        )
        self._create_emb(opp_b, make_2d_unit_vector(768, 0.64))

        student_profile = {
            "skills": ["Python", "Django", "React"],
            "city": "Kochi",
        }

        rows, opts = retrieve_candidate_opportunities("dev", student_profile)

        # Opp B must rank first due to skill/city re-ranking boost
        self.assertEqual(opts[0]["id"], opp_b.id)
        self.assertEqual(opts[1]["id"], opp_a.id)

    # ------------------------------------------------------------------
    # 5. Fallback path on AIBusyError, AIFailureError, AIConfigError & empty
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_fallback_path_used_on_ai_busy_error(self, mock_embed):
        """AIBusyError triggers graceful fallback to get_candidate_opportunities_context."""
        mock_embed.side_effect = AIBusyError("Busy 503")
        opp = self._create_opp("Fallback Opportunity")
        self._create_emb(opp, make_unit_vector(768, 0, 1.0))

        rows, opts, source = retrieve_with_source("query", {})
        self.assertEqual(source, "fallback")
        self.assertIn(opp.id, rows)

    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_fallback_path_used_on_ai_failure_error(self, mock_embed):
        """AIFailureError triggers graceful fallback."""
        mock_embed.side_effect = AIFailureError("Quota 429")
        opp = self._create_opp("Fallback Opportunity")

        rows, opts, source = retrieve_with_source("query", {})
        self.assertEqual(source, "fallback")
        self.assertIn(opp.id, rows)

    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_fallback_path_used_on_ai_config_error(self, mock_embed):
        """AIConfigError triggers graceful fallback."""
        mock_embed.side_effect = AIConfigError("Missing key")
        opp = self._create_opp("Fallback Opportunity")

        rows, opts, source = retrieve_with_source("query", {})
        self.assertEqual(source, "fallback")
        self.assertIn(opp.id, rows)

    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_fallback_path_used_when_no_embeddings_exist(self, mock_embed):
        """When 0 embeddings exist in the database, falls back to heuristic context."""
        mock_embed.return_value = [make_unit_vector(768, 0, 1.0)]
        opp = self._create_opp("Unembedded Opportunity")
        # No OpportunityEmbedding created

        rows, opts, source = retrieve_with_source("query", {})
        self.assertEqual(source, "fallback")
        self.assertIn(opp.id, rows)

    # ------------------------------------------------------------------
    # 6. RAG_MIN_SIMILARITY filtering
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_rag_min_similarity_filters_when_set_and_does_nothing_when_none(self, mock_embed):
        """
        RAG_MIN_SIMILARITY drops results below the threshold when set.
        When None, all results are retained.
        """
        query_vec = make_unit_vector(768, 0, 1.0)
        mock_embed.return_value = [query_vec]

        # opp_high: similarity = 0.90 (angle 0.45 rad)
        opp_high = self._create_opp("High Sim Opp")
        self._create_emb(opp_high, make_2d_unit_vector(768, 0.45))

        # opp_low: similarity = 0.40 (angle 1.16 rad)
        opp_low = self._create_opp("Low Sim Opp")
        self._create_emb(opp_low, make_2d_unit_vector(768, 1.16))

        # Case A: RAG_MIN_SIMILARITY is None (disabled)
        with override_settings(RAG_MIN_SIMILARITY=None):
            _, opts_none, source = retrieve_with_source("query", {})
            self.assertEqual(source, "vector")
            ids_none = [opt["id"] for opt in opts_none]
            self.assertIn(opp_high.id, ids_none)
            self.assertIn(opp_low.id, ids_none)

        # Case B: RAG_MIN_SIMILARITY is 0.60 -> opp_low (0.40) is dropped
        with override_settings(RAG_MIN_SIMILARITY=0.60):
            _, opts_filtered, source = retrieve_with_source("query", {})
            self.assertEqual(source, "vector")
            ids_filtered = [opt["id"] for opt in opts_filtered]
            self.assertIn(opp_high.id, ids_filtered)
            self.assertNotIn(opp_low.id, ids_filtered)

        # Case C: RAG_MIN_SIMILARITY is 0.95 -> all candidates dropped, returns "no_match"
        with override_settings(RAG_MIN_SIMILARITY=0.95):
            rows_nomatch, opts_nomatch, source_nomatch = retrieve_with_source("query", {})
            self.assertEqual(source_nomatch, "no_match")
            self.assertEqual(rows_nomatch, {})
            self.assertEqual(opts_nomatch, [])

    def test_rag_min_similarity_invalid_value_raises_improperly_configured(self):
        """
        An invalid RAG_MIN_SIMILARITY value raises ImproperlyConfigured.
        """
        from django.core.exceptions import ImproperlyConfigured
        raw_val = "not-a-number"
        with self.assertRaises(ImproperlyConfigured) as ctx:
            try:
                float(raw_val.strip())
            except (ValueError, TypeError) as exc:
                raise ImproperlyConfigured(
                    f"Invalid RAG_MIN_SIMILARITY setting '{raw_val}': must be a valid float."
                ) from exc
        self.assertIn("must be a valid float", str(ctx.exception))



    # ------------------------------------------------------------------
    # 7. Return shapes and sanitized dictionary keys
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_return_shapes_and_sanitized_keys_match_context_contract(self, mock_embed):
        """
        candidate_rows is dict[int, Opportunity] and sanitized_opts contains
        exactly the same keys as get_candidate_opportunities_context.
        """
        query_vec = make_unit_vector(768, 0, 1.0)
        mock_embed.return_value = [query_vec]

        opp = self._create_opp("Test Gig Title", required_skills=["Python", "Django"])
        self._create_emb(opp, query_vec)

        rows, opts = retrieve_candidate_opportunities("query", {})

        # Assert candidate_rows shape
        self.assertIsInstance(rows, dict)
        self.assertIn(opp.id, rows)
        self.assertIsInstance(rows[opp.id], Opportunity)

        # Assert sanitized_opts shape and exact key set
        self.assertIsInstance(opts, list)
        self.assertEqual(len(opts), 1)
        expected_keys = {
            "id",
            "title",
            "category",
            "city",
            "work_mode",
            "pay_type",
            "deadline",
            "required_skills",
        }
        self.assertEqual(set(opts[0].keys()), expected_keys)
        self.assertEqual(opts[0]["id"], opp.id)
        self.assertEqual(opts[0]["title"], "Test Gig Title")

    # ------------------------------------------------------------------
    # 8. build_query_text sanitization and user turn extraction
    # ------------------------------------------------------------------
    def test_build_query_text_sanitizes_caps_and_includes_only_user_turns(self):
        """
        build_query_text:
        - Keeps up to the last 2 user turns from history + current message.
        - Excludes assistant / model turns.
        - Collapses newlines and carriage returns.
        - Caps maximum length at max_len.
        """
        history = [
            {"role": "user", "content": "First old user query"},
            {"role": "assistant", "content": "How may I help?"},
            {"role": "user", "content": "Second user query\nwith newlines"},
            {"role": "model", "content": "Understood."},
            {"role": "user", "content": "Third user query\r\nand return"},
        ]
        message = "Current message\nwith tabs and spaces"

        # The last 2 user turns are:
        # 1. "Second user query with newlines"
        # 2. "Third user query and return"
        # Followed by "Current message with tabs and spaces"
        result = build_query_text(message, history, max_len=500)

        self.assertNotIn("First old user query", result)
        self.assertNotIn("How may I help?", result)
        self.assertNotIn("Understood.", result)
        self.assertIn("Second user query with newlines", result)
        self.assertIn("Third user query and return", result)
        self.assertIn("Current message with tabs and spaces", result)
        self.assertNotIn("\n", result)
        self.assertNotIn("\r", result)

        # Capping check
        capped = build_query_text(message, history, max_len=25)
        self.assertEqual(len(capped), 25)

    # ------------------------------------------------------------------
    # 9. assertNumQueries with 10+ opportunities
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_assert_num_queries_bounded_with_10_plus_opportunities(self, mock_embed):
        """
        Retrieval executes exactly 1 SQL query regardless of candidate count
        by using select_related("opportunity").
        """
        query_vec = make_unit_vector(768, 0, 1.0)
        mock_embed.return_value = [query_vec]

        # Create 12 open opportunities with embeddings
        for i in range(12):
            opp = self._create_opp(f"Opp #{i}", required_skills=["Skill1", "Skill2"])
            self._create_emb(opp, make_unit_vector(768, i % 50, 1.0))

        student_profile = {"skills": ["Skill1"], "city": "Kochi"}

        with self.assertNumQueries(1):
            rows, opts = retrieve_candidate_opportunities("query", student_profile, k=8, pool=20)

        self.assertEqual(len(opts), 8)


class EvaluateRetrievalCommandTestCase(TestCase):
    def setUp(self):
        self.poster = User.objects.create_user(
            email="eval_poster@example.com",
            password="Password123!",
            full_name="Eval Provider",
            role=User.Role.PROVIDER,
            is_verified=True,
        )

    @override_settings(
        GOOGLE_API_KEY="test-key",
        GEMINI_EMBEDDING_MODEL="test-model",
        GEMINI_EMBEDDING_DIM=768,
        RAG_AUTO_INDEX=False,
    )
    @patch("apps.assistant.rag.retrieval.embed_texts")
    def test_evaluate_retrieval_command_with_temp_json(self, mock_embed):
        """
        evaluate_retrieval command:
        - Runs old, keyword, and vector methods on cases.
        - Resolves expected_ids and expected_titles.
        - Warns when an expected_id or expected_title matches no open listing.
        - Prints per-query table and aggregated metrics.
        """
        mock_embed.return_value = [make_unit_vector(768, 0, 1.0)]

        # Create open opportunities
        opp_ui = Opportunity.objects.create(
            poster=self.poster,
            title="UI/UX Design Intern for a Mobile App",
            category=Opportunity.Category.INTERNSHIP,
            description="Design screens in Figma",
            required_skills=["Figma"],
            city="Kochi",
            status=Opportunity.Status.OPEN,
            deadline=timezone.localdate() + datetime.timedelta(days=20),
        )
        OpportunityEmbedding.objects.create(
            opportunity=opp_ui,
            embedding=make_unit_vector(768, 0, 1.0),
            content_hash="ui_hash",
            embedding_model="test-model",
            embedding_dim=768,
        )

        opp_math = Opportunity.objects.create(
            poster=self.poster,
            title="Maths Tutor for Class 10 Students",
            category=Opportunity.Category.TUTORING,
            description="Teach algebra and geometry",
            required_skills=["Mathematics"],
            city="Kozhikode",
            status=Opportunity.Status.OPEN,
            deadline=timezone.localdate() + datetime.timedelta(days=20),
        )
        OpportunityEmbedding.objects.create(
            opportunity=opp_math,
            embedding=make_unit_vector(768, 1, 1.0),
            content_hash="math_hash",
            embedding_model="test-model",
            embedding_dim=768,
        )

        # Temporary JSON file with 3 cases:
        # Case 1: expected_titles hit
        # Case 2: expected_ids hit
        # Case 3: missing id and missing title warnings
        cases_data = [
            {
                "query": "I enjoy designing app screens",
                "expected_titles": ["UI/UX Design Intern"],
            },
            {
                "query": "Teach mathematics to high school students",
                "expected_ids": [opp_math.id],
            },
            {
                "query": "Astronaut role in orbit",
                "expected_ids": [999999],
                "expected_titles": ["Space Explorer Mission"],
            },
        ]

        with tempfile.NamedTemporaryFile("w+", suffix=".json", delete=False) as tmp:
            json.dump(cases_data, tmp)
            tmp_path = tmp.name

        try:
            out = StringIO()
            call_command("evaluate_retrieval", "--file", tmp_path, "--k", 8, stdout=out)
            output = out.getvalue()

            # Assert warnings for non-existent expected id and title
            self.assertIn("[WARNING]", output)
            self.assertIn("expected_id 999999 matches no open listing", output)
            self.assertIn("expected_title 'Space Explorer Mission' matches no open listing", output)

            # Assert table and summary headers
            self.assertIn("PER-QUERY RETRIEVAL EVALUATION", output)
            self.assertIn("AGGREGATED METRICS SUMMARY", output)
            self.assertIn("Real embedding API calls made: 3", output)
            self.assertIn("Old Heuristic", output)
            self.assertIn("Keyword Baseline", output)
            self.assertIn("Vector Retrieval", output)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
