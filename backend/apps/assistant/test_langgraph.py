import json
import sys
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser, StudentProfile
from apps.assistant.context import get_student_profile_context
from apps.assistant.rag.langgraph_agent import (
    GraphError,
    get_my_profile,
    retrieve_opportunities,
    run_langgraph_agent,
)
from apps.common.gemini_client import AIBusyError, AIConfigError, AIFailureError
from apps.opportunities.models import Opportunity

User = get_user_model()


class LangGraphAssistantTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.chat_url = "/api/assistant/chat/"

        self.provider = CustomUser.objects.create_user(
            email="provider_lg@example.com",
            password="Password123!",
            full_name="Provider LG",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )
        self.student = CustomUser.objects.create_user(
            email="student_lg@example.com",
            password="Password123!",
            full_name="Student LG",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            skills=["Python", "Django", "React"],
            city="Kochi",
            qualification_type="BTech",
            qualification_name="Computer Science",
            institution="Model Engineering College",
            availability="immediate",
            languages=["English", "Malayalam"],
        )

        self.student_other = CustomUser.objects.create_user(
            email="other_student@example.com",
            password="Password123!",
            full_name="Other Student",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.other_profile = StudentProfile.objects.create(
            user=self.student_other,
            skills=["Rust", "Go"],
            city="Bengaluru",
        )

        self.opp1 = Opportunity.objects.create(
            poster=self.provider,
            title="Backend Python Developer",
            category="Software Development",
            city="Kochi",
            work_mode="hybrid",
            pay_type="fixed",
            status=Opportunity.Status.OPEN,
        )
        self.opp2 = Opportunity.objects.create(
            poster=self.provider,
            title="Full Stack Django React",
            category="Web Development",
            city="Kochi",
            work_mode="remote",
            pay_type="fixed",
            status=Opportunity.Status.OPEN,
        )
        self.opp3 = Opportunity.objects.create(
            poster=self.provider,
            title="Data Science Intern",
            category="Data Science",
            city="Thiruvananthapuram",
            work_mode="onsite",
            pay_type="hourly",
            status=Opportunity.Status.OPEN,
        )

        self.client.force_authenticate(user=self.student)

    # ------------------------------------------------------------------
    # 1. Happy Path: Model retrieves, gets candidates, returns reply + opps
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGGRAPH=True)
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_happy_path_retrieve_and_reply(self, mock_generate, mock_retrieve):
        mock_retrieve.return_value = (
            {self.opp1.id: self.opp1, self.opp2.id: self.opp2},
            [
                {"id": self.opp1.id, "title": self.opp1.title, "category": self.opp1.category},
                {"id": self.opp2.id, "title": self.opp2.title, "category": self.opp2.category},
            ],
            "vector",
        )
        mock_generate.side_effect = [
            '{"action": "retrieve", "query": "python developer"}',
            json.dumps({
                "reply": "Here are 2 Python opportunities in Kochi.",
                "opportunity_ids": [self.opp1.id, self.opp2.id],
            }),
        ]

        response = self.client.post(
            self.chat_url,
            data={"message": "Any python openings in Kochi?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["reply"], "Here are 2 Python opportunities in Kochi.")
        self.assertEqual(len(data["opportunities"]), 2)
        self.assertEqual(data["opportunities"][0]["id"], self.opp1.id)
        self.assertEqual(data["opportunities"][1]["id"], self.opp2.id)

        self.assertEqual(mock_generate.call_count, 2)
        self.assertEqual(mock_retrieve.call_count, 1)
        mock_retrieve.assert_called_once_with(
            query_text="python developer",
            student_profile_data=get_student_profile_context(self.student),
        )

    # ------------------------------------------------------------------
    # 2. Direct Answer Without Tools: Platform question, retrieval NOT called
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGGRAPH=True)
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_direct_answer_without_tools_retrieval_not_called(self, mock_generate, mock_retrieve):
        mock_generate.return_value = json.dumps({
            "reply": "Students can upload one resume (PDF or DOCX, max 5 MB).",
            "opportunity_ids": [],
        })

        response = self.client.post(
            self.chat_url,
            data={"message": "Can I upload my resume to NextGig?"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["reply"], "Students can upload one resume (PDF or DOCX, max 5 MB).")
        self.assertEqual(data["opportunities"], [])
        self.assertEqual(mock_generate.call_count, 1)
        mock_retrieve.assert_not_called()

    # ------------------------------------------------------------------
    # 3. Step Cap: Model that keeps asking for tools ends after 2 model calls
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGGRAPH=True)
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_step_cap_ends_after_two_model_calls_with_graceful_reply(self, mock_generate, mock_retrieve):
        mock_retrieve.return_value = (
            {self.opp1.id: self.opp1},
            [{"id": self.opp1.id, "title": self.opp1.title, "category": self.opp1.category}],
            "vector",
        )
        mock_generate.side_effect = [
            '{"action": "retrieve", "query": "python developer"}',
            '{"action": "retrieve", "query": "more python developer"}',
        ]

        response = self.client.post(
            self.chat_url,
            data={"message": "Find me all python gigs"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(mock_generate.call_count, 2)
        self.assertTrue(len(data["reply"]) > 0)
        self.assertEqual(len(data["opportunities"]), 1)
        self.assertEqual(data["opportunities"][0]["id"], self.opp1.id)

    # ------------------------------------------------------------------
    # 4. AIBusyError: Returns 503 and does NOT fall back
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGGRAPH=True)
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_ai_busy_error_returns_503_and_does_not_fall_back(self, mock_generate, mock_retrieve):
        mock_generate.side_effect = AIBusyError("Rate limit exceeded")

        response = self.client.post(
            self.chat_url,
            data={"message": "Hello assistant"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(
            response.json()["detail"],
            "The assistant is busy right now. Please try again in a minute.",
        )
        mock_retrieve.assert_not_called()

    # ------------------------------------------------------------------
    # 5. Graph Error: Falls back to the chain and returns 200
    # ------------------------------------------------------------------
    @override_settings(
        ASSISTANT_USE_LANGGRAPH=True,
        ASSISTANT_USE_LANGCHAIN=True,
        ASSISTANT_USE_RAG=True,
    )
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_graph_error_falls_back_to_chain_and_returns_200(self, mock_generate, mock_retrieve):
        mock_retrieve.return_value = (
            {self.opp1.id: self.opp1},
            [{"id": self.opp1.id, "title": self.opp1.title, "category": self.opp1.category}],
            "vector",
        )
        # Call 1 (in LangGraph agent): malformed JSON output triggering GraphError
        # Call 2 (in fallback chain): valid assistant answer
        mock_generate.side_effect = [
            "{ 'invalid': unquoted_json_loop",
            json.dumps({
                "reply": "Fallback chain successfully answered.",
                "opportunity_ids": [self.opp1.id],
            }),
        ]

        with self.assertLogs("apps.assistant.views", level="WARNING") as cm:
            response = self.client.post(
                self.chat_url,
                data={"message": "Any python work?"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["reply"], "Fallback chain successfully answered.")
        self.assertEqual(len(data["opportunities"]), 1)
        self.assertEqual(data["opportunities"][0]["id"], self.opp1.id)

        # Confirm warning log contains exception name and NO user text
        warning_logged = any("Assistant LangGraph error" in log for log in cm.output)
        self.assertTrue(warning_logged)
        for log in cm.output:
            self.assertNotIn("Any python work?", log)

    # ------------------------------------------------------------------
    # 6. Privacy: Requesting student's sanitized fields only on every call
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGGRAPH=True)
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_privacy_profile_sanitization_and_no_user_choice(self, mock_generate, mock_retrieve):
        mock_retrieve.return_value = (
            {self.opp1.id: self.opp1},
            [{"id": self.opp1.id, "title": self.opp1.title, "category": self.opp1.category}],
            "vector",
        )
        mock_generate.side_effect = [
            '{"action": "retrieve", "query": "python developer"}',
            json.dumps({
                "reply": "Here are opportunities for you in Kochi.",
                "opportunity_ids": [self.opp1.id],
            }),
        ]

        response = self.client.post(
            self.chat_url,
            data={"message": "What jobs match my profile?"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(mock_generate.call_count, 1)

        # Reads the system_instruction and contents passed to the mocked generate_text on EVERY call
        for call_args in mock_generate.call_args_list:
            sys_inst = str(call_args.kwargs.get("system_instruction") or "")
            contents_text = str(call_args.kwargs.get("contents") or "")
            combined_text = sys_inst + "\n" + contents_text

            # Asserts the combined text:
            # - contains the requesting student's city "Kochi"
            self.assertIn("Kochi", combined_text)
            # - does NOT contain the student's email, the other student's email, "Bengaluru", "Rust", "phone", or "address"
            self.assertNotIn(self.student.email, combined_text)
            self.assertNotIn(self.student_other.email, combined_text)
            self.assertNotIn("Bengaluru", combined_text)
            self.assertNotIn("Rust", combined_text)
            self.assertNotIn("phone", combined_text)
            self.assertNotIn("address", combined_text)

        # Signature and parameter isolation checks
        import inspect
        sig = inspect.signature(retrieve_opportunities)
        param_names = list(sig.parameters.keys())
        self.assertEqual(param_names[0], "query")
        self.assertNotIn("user", param_names[:1])
        self.assertNotIn("user_id", param_names)

        sig_prof = inspect.signature(get_my_profile)
        self.assertNotIn("user_id", sig_prof.parameters)

    # ------------------------------------------------------------------
    # 6b. First model call instruction: contains "retrieve" and the MUST rule
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGGRAPH=True)
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_first_model_call_system_instruction_contains_retrieve_and_must_rule(
        self, mock_generate, mock_retrieve
    ):
        mock_generate.return_value = json.dumps({
            "reply": "Hello! How can I help you with NextGig today?",
            "opportunity_ids": [],
        })

        response = self.client.post(
            self.chat_url,
            data={"message": "Hi there"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(mock_generate.call_count, 1)

        first_call_sys_inst = mock_generate.call_args_list[0].kwargs.get("system_instruction") or ""
        self.assertIn("retrieve", first_call_sys_inst)
        self.assertIn(
            "If the student asks about opportunities, internships, jobs, gigs, events, or what to apply for, you MUST reply with the retrieve action first. Answer directly only for platform questions or greetings.",
            first_call_sys_inst,
        )

    # ------------------------------------------------------------------
    # 7. Flag Off: Old path used, langgraph not imported
    # ------------------------------------------------------------------
    @override_settings(
        ASSISTANT_USE_LANGGRAPH=False,
        ASSISTANT_USE_LANGCHAIN=False,
        ASSISTANT_USE_RAG=False,
    )
    @patch("apps.assistant.views.generate_text")
    def test_flag_off_old_path_used_langgraph_not_imported(self, mock_generate):
        mock_generate.return_value = json.dumps({
            "reply": "Legacy path response.",
            "opportunity_ids": [],
        })

        # Evict langgraph_agent from sys.modules if already imported
        mod_key = "apps.assistant.rag.langgraph_agent"
        saved_mod = sys.modules.pop(mod_key, None)

        try:
            response = self.client.post(
                self.chat_url,
                data={"message": "Hello"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.json()["reply"], "Legacy path response.")
            self.assertNotIn(mod_key, sys.modules)
        finally:
            if saved_mod is not None:
                sys.modules[mod_key] = saved_mod

    # ------------------------------------------------------------------
    # 8. Invalid Opportunity IDs from model are dropped
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGGRAPH=True)
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_invalid_opportunity_ids_from_model_are_dropped(self, mock_generate, mock_retrieve):
        mock_retrieve.return_value = (
            {self.opp1.id: self.opp1, self.opp2.id: self.opp2},
            [
                {"id": self.opp1.id, "title": self.opp1.title, "category": self.opp1.category},
                {"id": self.opp2.id, "title": self.opp2.title, "category": self.opp2.category},
            ],
            "vector",
        )
        mock_generate.side_effect = [
            '{"action": "retrieve", "query": "python"}',
            json.dumps({
                "reply": "Here are the jobs.",
                # 99999 is nonexistent, "bogus_id" is non-int, opp1 is repeated
                "opportunity_ids": [self.opp1.id, 99999, "bogus_id", self.opp2.id, self.opp1.id],
            }),
        ]

        response = self.client.post(
            self.chat_url,
            data={"message": "Python jobs"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        opp_ids = [o["id"] for o in data["opportunities"]]
        self.assertEqual(opp_ids, [self.opp1.id, self.opp2.id])
        self.assertNotIn(99999, opp_ids)

    # ------------------------------------------------------------------
    # 9. Extra Check: If model never retrieved, opportunities are empty
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGGRAPH=True)
    @patch("apps.assistant.views.retrieve_with_source")
    @patch("apps.assistant.views.generate_text")
    def test_never_retrieved_opportunities_are_empty(self, mock_generate, mock_retrieve):
        # Model returns opportunity_ids without ever calling "retrieve"
        mock_generate.return_value = json.dumps({
            "reply": "Direct response without retrieval.",
            "opportunity_ids": [self.opp1.id, self.opp2.id],
        })

        response = self.client.post(
            self.chat_url,
            data={"message": "Tell me about NextGig"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["reply"], "Direct response without retrieval.")
        self.assertEqual(data["opportunities"], [])
        mock_retrieve.assert_not_called()
