import datetime
import json
from unittest.mock import MagicMock, patch
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import CustomUser, StudentProfile
from apps.assistant.constants import SYSTEM_INSTRUCTION_BASE
from apps.assistant.rag.langchain_chain import (
    AssistantOutputParsingError,
    GeminiChatModel,
    build_system_instruction,
    conversation_to_messages,
    create_assistant_chain,
    messages_to_gemini_contents,
    parse_assistant_output,
)
from apps.assistant.rag.langchain_retriever import OpportunityRetriever
from apps.common.gemini_client import AIBusyError, AIConfigError, AIFailureError
from apps.opportunities.models import Opportunity
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

User = get_user_model()


class LangChainUnitTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.provider = CustomUser.objects.create_user(
            email="provider_lc@example.com",
            password="Password123!",
            full_name="Provider LC",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )
        self.opp1 = Opportunity.objects.create(
            poster=self.provider,
            title="Opp 1",
            status=Opportunity.Status.OPEN,
        )
        self.opp2 = Opportunity.objects.create(
            poster=self.provider,
            title="Opp 2",
            status=Opportunity.Status.OPEN,
        )
        self.opp3 = Opportunity.objects.create(
            poster=self.provider,
            title="Opp 3",
            status=Opportunity.Status.OPEN,
        )
        self.opp4 = Opportunity.objects.create(
            poster=self.provider,
            title="Opp 4",
            status=Opportunity.Status.OPEN,
        )

    # ------------------------------------------------------------------
    # 1. OpportunityRetriever Unit Tests
    # ------------------------------------------------------------------
    @patch("apps.assistant.rag.langchain_retriever.retrieve_with_source")
    def test_retriever_per_request_instance_calls_retrieve_with_source(self, mock_retrieve):
        mock_retrieve.return_value = (
            {self.opp1.id: self.opp1},
            [{"id": self.opp1.id, "title": self.opp1.title, "category": "Dev"}],
            "vector",
        )
        profile_data = {"skills": ["Python", "Django"], "city": "Kochi"}
        retriever = OpportunityRetriever(student_profile_data=profile_data)

        docs = retriever.invoke("python roles")

        mock_retrieve.assert_called_once_with(
            query_text="python roles",
            student_profile_data=profile_data,
        )
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].metadata["id"], self.opp1.id)
        self.assertEqual(retriever.source, "vector")
        self.assertIn(self.opp1.id, retriever.candidate_dict)
        self.assertEqual(len(retriever.candidate_opportunities), 1)

    # ------------------------------------------------------------------
    # 2. Prompt Building Unit Tests
    # ------------------------------------------------------------------
    def test_build_system_instruction_byte_identical_sections(self):
        profile = {"skills": ["Python"], "city": "Kochi"}
        opps = [{"id": 1, "title": "Test Opp"}]

        # Normal vector source
        inst_vector = build_system_instruction(profile, opps, "vector")
        self.assertIn("--- STUDENT PROFILE DATA ---", inst_vector)
        self.assertIn("--- PLATFORM FACT SHEET ---", inst_vector)
        self.assertIn("--- CANDIDATE OPPORTUNITIES DATA ---", inst_vector)
        self.assertNotIn("If the candidate list is empty", inst_vector)

        # no_match source
        inst_no_match = build_system_instruction(profile, [], "no_match")
        self.assertIn(
            "If the candidate list is empty, say that no listing matches and suggest browsing the Opportunities page.",
            inst_no_match,
        )

    def test_conversation_to_messages_and_back_roundtrip(self):
        turns = [
            {"role": "user", "text": "Hello"},
            {"role": "model", "text": "Hi there!"},
            {"role": "user", "text": "Find gigs"},
        ]
        msgs = [SystemMessage(content="SYS_INSTRUCTION")] + conversation_to_messages(turns)

        self.assertEqual(len(msgs), 4)
        self.assertIsInstance(msgs[0], SystemMessage)
        self.assertIsInstance(msgs[1], HumanMessage)
        self.assertIsInstance(msgs[2], AIMessage)
        self.assertIsInstance(msgs[3], HumanMessage)

        sys_extracted, turns_extracted = messages_to_gemini_contents(msgs)
        self.assertEqual(sys_extracted, "SYS_INSTRUCTION")
        self.assertEqual(turns_extracted, turns)

    # ------------------------------------------------------------------
    # 3. Output Parser Unit Tests
    # ------------------------------------------------------------------
    def test_parse_assistant_output_strips_code_fences(self):
        candidate_dict = {self.opp1.id: self.opp1}
        raw_output = f"```json\n{{\"reply\": \"Found one\", \"opportunity_ids\": [{self.opp1.id}]}}\n```"

        reply, opps = parse_assistant_output(raw_output, candidate_dict)
        self.assertEqual(reply, "Found one")
        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0].id, self.opp1.id)

    def test_parse_assistant_output_invalid_json_fallback(self):
        candidate_dict = {self.opp1.id: self.opp1}
        raw_output = "I cannot find any specific role right now, but feel free to browse!"

        reply, opps = parse_assistant_output(raw_output, candidate_dict)
        self.assertEqual(reply, raw_output)
        self.assertEqual(opps, [])

    def test_parse_assistant_output_missing_reply_raises_error(self):
        candidate_dict = {self.opp1.id: self.opp1}
        raw_output = f"{{\"opportunity_ids\": [{self.opp1.id}]}}"

        with self.assertRaises(AssistantOutputParsingError):
            parse_assistant_output(raw_output, candidate_dict)

    def test_parse_assistant_output_validates_candidates_deduplicates_and_caps_at_3(self):
        candidate_dict = {
            self.opp1.id: self.opp1,
            self.opp2.id: self.opp2,
            self.opp3.id: self.opp3,
            self.opp4.id: self.opp4,
        }
        # Model returns opp1, opp2, duplicate opp1, foreign id 9999, opp3, opp4
        raw_output = json.dumps({
            "reply": "Here are recommendations:",
            "opportunity_ids": [self.opp1.id, self.opp2.id, self.opp1.id, 9999, self.opp3.id, self.opp4.id],
        })

        reply, opps = parse_assistant_output(raw_output, candidate_dict)
        self.assertEqual(reply, "Here are recommendations:")
        self.assertEqual(len(opps), 3)
        self.assertEqual([o.id for o in opps], [self.opp1.id, self.opp2.id, self.opp3.id])


@override_settings(ALLOWED_HOSTS=["*"])
class AssistantLangChainIntegrationTestCase(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.chat_url = "/api/assistant/chat/"

        self.student = CustomUser.objects.create_user(
            email="student_lc_test@example.com",
            password="Password123!",
            full_name="Student LC",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.profile, _ = StudentProfile.objects.get_or_create(user=self.student)
        self.profile.skills = ["Python", "Django", "PostgreSQL"]
        self.profile.city = "Kochi"
        self.profile.save()

        self.student_b = CustomUser.objects.create_user(
            email="student_b_private@example.com",
            password="Password123!",
            full_name="Student B Private",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.profile_b, _ = StudentProfile.objects.get_or_create(user=self.student_b)
        self.profile_b.skills = ["Rust", "Kubernetes"]
        self.profile_b.city = "Munich"
        self.profile_b.save()

        self.provider = CustomUser.objects.create_user(
            email="provider_lc_test@example.com",
            password="Password123!",
            full_name="Provider LC Test",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )
        self.opp1 = Opportunity.objects.create(
            poster=self.provider,
            title="Backend Python Developer",
            status=Opportunity.Status.OPEN,
            contact_info="SECRET_PHONE_99999",
            deadline=timezone.localdate() + datetime.timedelta(days=10),
        )

    # ------------------------------------------------------------------
    # 4. PARITY TEST: Identical arguments to generate_text on & off
    # ------------------------------------------------------------------
    @patch("apps.assistant.views.generate_text")
    def test_parity_generate_text_arguments_identical_with_flag_on_and_off(self, mock_generate):
        mock_generate.return_value = json.dumps({
            "reply": "Identical response",
            "opportunity_ids": [self.opp1.id],
        })
        self.client.force_authenticate(user=self.student)

        history = [
            {"role": "user", "content": "I like Python development"},
            {"role": "assistant", "content": "What roles are you seeking?"},
            {"role": "user", "content": "Junior backend roles"},
        ]
        payload = {"message": "Any openings in Kochi?", "history": history}

        # Run 1: Legacy path (ASSISTANT_USE_LANGCHAIN = False)
        with override_settings(ASSISTANT_USE_LANGCHAIN=False, ASSISTANT_USE_RAG=False):
            res_legacy = self.client.post(self.chat_url, data=payload, format="json")
            self.assertEqual(res_legacy.status_code, status.HTTP_200_OK)
            call_legacy = mock_generate.call_args.kwargs.copy()

        mock_generate.reset_mock()

        # Run 2: LangChain path (ASSISTANT_USE_LANGCHAIN = True)
        with override_settings(ASSISTANT_USE_LANGCHAIN=True, ASSISTANT_USE_RAG=False):
            res_langchain = self.client.post(self.chat_url, data=payload, format="json")
            self.assertEqual(res_langchain.status_code, status.HTTP_200_OK)
            call_langchain = mock_generate.call_args.kwargs.copy()

        # Compare generate_text arguments
        self.assertEqual(
            call_legacy["contents"],
            call_langchain["contents"],
            "Conversation contents passed to generate_text must be identical",
        )
        self.assertEqual(
            call_legacy["system_instruction"],
            call_langchain["system_instruction"],
            "System instruction passed to generate_text must be byte-identical",
        )
        self.assertEqual(
            call_legacy["max_output_tokens"],
            call_langchain["max_output_tokens"],
            "max_output_tokens must be identical",
        )

        # Compare endpoint response bodies
        self.assertEqual(res_legacy.json(), res_langchain.json())

    # ------------------------------------------------------------------
    # 5. Endpoint Tests with ASSISTANT_USE_LANGCHAIN = True
    # ------------------------------------------------------------------
    @override_settings(ASSISTANT_USE_LANGCHAIN=True, ASSISTANT_USE_RAG=False)
    @patch("apps.assistant.views.generate_text")
    def test_langchain_flag_on_error_mapping_503_and_502(self, mock_generate):
        self.client.force_authenticate(user=self.student)

        # AIConfigError -> 503
        mock_generate.side_effect = AIConfigError("Missing key details")
        res1 = self.client.post(self.chat_url, data={"message": "Hi"}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(res1.json()["detail"], "The assistant is not available right now.")

        # AIBusyError -> 503
        mock_generate.side_effect = AIBusyError("Busy details")
        res2 = self.client.post(self.chat_url, data={"message": "Hi"}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(res2.json()["detail"], "The assistant is busy right now. Please try again in a minute.")

        # AIFailureError -> 502
        mock_generate.side_effect = AIFailureError("Upstream failure")
        res3 = self.client.post(self.chat_url, data={"message": "Hi"}, format="json")
        self.assertEqual(res3.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(res3.json()["detail"], "The assistant couldn't answer right now. Please try again.")

        # Output parser error: JSON missing 'reply' string key -> 502
        mock_generate.side_effect = None
        mock_generate.return_value = '{"opportunity_ids": [1]}'
        res4 = self.client.post(self.chat_url, data={"message": "Hi"}, format="json")
        self.assertEqual(res4.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(res4.json()["detail"], "The assistant couldn't answer right now. Please try again.")

    @override_settings(ASSISTANT_USE_LANGCHAIN=True, ASSISTANT_USE_RAG=True)
    @patch("apps.assistant.views.generate_text")
    @patch("apps.assistant.views.retrieve_with_source")
    def test_langchain_flag_on_source_no_match_instruction(self, mock_retrieve, mock_generate):
        mock_retrieve.return_value = ({}, [], "no_match")
        mock_generate.return_value = json.dumps({
            "reply": "No matching gigs found.",
            "opportunity_ids": [],
        })
        self.client.force_authenticate(user=self.student)

        res = self.client.post(self.chat_url, data={"message": "Exotic quantum gig"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["opportunities"], [])

        sys_inst = mock_generate.call_args.kwargs["system_instruction"]
        self.assertIn(
            "If the candidate list is empty, say that no listing matches and suggest browsing the Opportunities page.",
            sys_inst,
        )

    @override_settings(ASSISTANT_USE_LANGCHAIN=True, ASSISTANT_USE_RAG=True)
    @patch("apps.assistant.views.generate_text")
    @patch("apps.assistant.views.retrieve_with_source")
    def test_langchain_flag_on_privacy_isolation(self, mock_retrieve, mock_generate):
        mock_retrieve.return_value = ({self.opp1.id: self.opp1}, [{"id": self.opp1.id, "title": self.opp1.title}], "vector")
        mock_generate.return_value = json.dumps({"reply": "Privacy ok", "opportunity_ids": []})
        self.client.force_authenticate(user=self.student)

        res = self.client.post(self.chat_url, data={"message": "Find python work"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Inspect query_text passed to retriever
        query_text = mock_retrieve.call_args.kwargs["query_text"]
        self.assertNotIn(self.student_b.email, query_text)
        self.assertNotIn("Rust", query_text)

        # Inspect system_instruction and contents passed to Gemini
        sys_inst = mock_generate.call_args.kwargs["system_instruction"]
        contents = str(mock_generate.call_args.kwargs["contents"])
        self.assertNotIn(self.student_b.email, sys_inst)
        self.assertNotIn(self.student.email, sys_inst)  # Own email is private
        self.assertNotIn("SECRET_PHONE_99999", sys_inst)  # Provider contact_info private
        self.assertNotIn(self.student_b.email, contents)

    @override_settings(ASSISTANT_USE_LANGCHAIN=True, ASSISTANT_USE_RAG=True, TESTING=False)
    @patch("apps.assistant.views.generate_text")
    @patch("apps.assistant.views.retrieve_with_source", return_value=({}, [], "vector"))
    def test_langchain_flag_on_throttling_applies(self, mock_retrieve, mock_generate):
        cache.clear()
        mock_generate.return_value = '{"reply": "OK", "opportunity_ids": []}'
        self.client.force_authenticate(user=self.student)

        for i in range(5):
            res = self.client.post(self.chat_url, data={"message": f"Ping {i}"}, format="json")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        res6 = self.client.post(self.chat_url, data={"message": "Ping 6"}, format="json")
        self.assertEqual(res6.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @override_settings(ASSISTANT_USE_LANGCHAIN=True, ASSISTANT_USE_RAG=True)
    @patch("apps.assistant.views.generate_text")
    @patch("apps.assistant.views.retrieve_with_source", side_effect=RuntimeError("Vector index crashed"))
    @patch("apps.assistant.views.get_candidate_opportunities_context")
    def test_langchain_flag_on_unexpected_retrieval_exception_falls_back(
        self, mock_get_context, mock_retrieve, mock_generate
    ):

        mock_get_context.return_value = ({self.opp1.id: self.opp1}, [{"id": self.opp1.id, "title": self.opp1.title}])
        mock_generate.return_value = json.dumps({
            "reply": "Fallback worked",
            "opportunity_ids": [self.opp1.id],
        })
        self.client.force_authenticate(user=self.student)

        res = self.client.post(self.chat_url, data={"message": "Help"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        mock_get_context.assert_called_once()
        self.assertEqual(res.json()["reply"], "Fallback worked")
        self.assertEqual(res.json()["opportunities"][0]["id"], self.opp1.id)
