"""
LangChain chain, prompt construction, chat model, and output parser for NextGig Assistant.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    ChatMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough

from apps.assistant.constants import PLATFORM_FACT_SHEET, SYSTEM_INSTRUCTION_BASE
from apps.assistant.views import build_conversation
from apps.common.gemini_client import generate_text

logger = logging.getLogger(__name__)


class AssistantOutputParsingError(Exception):
    """Raised when JSON parsed successfully but lacks valid 'reply' string key (maps to 502)."""
    pass


def build_system_instruction(
    profile_data: Dict[str, Any],
    candidate_opportunities: List[Dict[str, Any]],
    source: str,
) -> str:
    """
    Constructs the system instruction string byte-identical to the legacy path.
    """
    base_instruction = SYSTEM_INSTRUCTION_BASE
    if source == "no_match":
        base_instruction = (
            f"{base_instruction}\n"
            "If the candidate list is empty, say that no listing matches and suggest browsing the Opportunities page."
        )

    system_instruction = (
        f"{base_instruction}\n\n"
        "DATA BLOCKS:\n\n"
        "--- STUDENT PROFILE DATA ---\n"
        f"{json.dumps(profile_data, indent=2)}\n\n"
        "--- PLATFORM FACT SHEET ---\n"
        f"{PLATFORM_FACT_SHEET}\n\n"
        "--- CANDIDATE OPPORTUNITIES DATA ---\n"
        f"{json.dumps(candidate_opportunities, indent=2)}"
    )
    return system_instruction


def conversation_to_messages(conversation_items: List[Dict[str, str]]) -> List[BaseMessage]:
    """
    Converts build_conversation dictionary turns to LangChain messages.
    """
    messages: List[BaseMessage] = []
    for turn in conversation_items:
        role = turn.get("role")
        text = turn.get("text", "")
        if role == "user":
            messages.append(HumanMessage(content=text))
        elif role == "model":
            messages.append(AIMessage(content=text))
        else:
            messages.append(ChatMessage(role=role or "user", content=text))
    return messages


def messages_to_gemini_contents(
    messages: List[BaseMessage],
) -> Tuple[Optional[str], List[Dict[str, str]]]:
    """
    Extracts system_instruction and conversation_items from LangChain messages for generate_text.
    """
    system_parts: List[str] = []
    conversation_items: List[Dict[str, str]] = []

    for m in messages:
        if isinstance(m, SystemMessage):
            system_parts.append(m.content)
        elif isinstance(m, HumanMessage):
            conversation_items.append({"role": "user", "text": m.content})
        elif isinstance(m, AIMessage):
            conversation_items.append({"role": "model", "text": m.content})
        elif isinstance(m, ChatMessage):
            role = "user" if m.role == "user" else "model"
            conversation_items.append({"role": role, "text": m.content})

    system_instruction = "\n\n".join(system_parts) if system_parts else None
    return system_instruction, conversation_items


class GeminiChatModel(BaseChatModel):
    """
    Thin BaseChatModel wrapper calling apps.common.gemini_client.generate_text.
    Propagates AIConfigError, AIBusyError, and AIFailureError unchanged.
    """
    max_output_tokens: int = Field(default=400)
    generate_fn: Optional[Any] = Field(default=None)

    @property
    def _llm_type(self) -> str:
        return "gemini_chat_model"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:
        system_instruction, conversation_items = messages_to_gemini_contents(messages)
        fn = self.generate_fn or generate_text

        output_text = fn(
            contents=conversation_items,
            system_instruction=system_instruction,
            max_output_tokens=self.max_output_tokens,
        )
        generation = ChatGeneration(message=AIMessage(content=output_text))
        return ChatResult(generations=[generation])


def parse_assistant_output(
    raw_text: str,
    candidate_dict: Dict[int, Any],
) -> Tuple[str, List[Any]]:
    """
    Parses LLM output:
    - Strips markdown code fences (```json ... ```)
    - If valid JSON:
        - Validates 'reply' exists and is a non-empty str. If missing/invalid, raises AssistantOutputParsingError.
        - Cross-references 'opportunity_ids' against candidate_dict. Drops invalid IDs. Deduplicates. Caps at 3.
    - If not valid JSON (e.g. plain text response):
        - Falls back gracefully: treats raw_text as reply with empty opportunities.
    """
    clean_text = raw_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
    if clean_text.endswith("```"):
        clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    parsed_json = None
    try:
        parsed_json = json.loads(clean_text)
    except Exception:
        parsed_json = None

    if not isinstance(parsed_json, dict):
        # Fallback: treat raw text as reply with no opportunities
        reply_text = raw_text.strip()[:1200]
        return reply_text, []

    reply_val = parsed_json.get("reply")
    if not isinstance(reply_val, str) or not reply_val.strip():
        logger.error("Parsed assistant response missing or invalid string 'reply'.")
        raise AssistantOutputParsingError("Parsed assistant response missing or invalid string 'reply'.")

    reply_text = reply_val.strip()[:1200]
    raw_opp_ids = parsed_json.get("opportunity_ids", [])
    if not isinstance(raw_opp_ids, list):
        raw_opp_ids = []

    valid_opp_objs: List[Any] = []
    candidate_ids_set = set(candidate_dict.keys())
    for item in raw_opp_ids:
        try:
            item_int = int(item)
            if item_int in candidate_ids_set and item_int not in [o.id for o in valid_opp_objs]:
                valid_opp_objs.append(candidate_dict[item_int])
                if len(valid_opp_objs) >= 3:
                    break
        except (ValueError, TypeError):
            continue

    return reply_text, valid_opp_objs


def create_assistant_chain(
    chat_model: Optional[BaseChatModel] = None,
    generate_fn: Optional[Any] = None,
) -> Runnable:
    """
    Creates an LCEL chain combining prompt construction, GeminiChatModel, and output parsing.
    """
    model = chat_model or GeminiChatModel(generate_fn=generate_fn)

    def build_prompt_messages(inputs: Dict[str, Any]) -> List[BaseMessage]:
        profile_data = inputs["profile_data"]
        candidate_opportunities = inputs["candidate_opportunities"]
        source = inputs["source"]
        history = inputs.get("history", [])
        message = inputs["message"]

        system_instruction = build_system_instruction(
            profile_data=profile_data,
            candidate_opportunities=candidate_opportunities,
            source=source,
        )
        conversation_items = build_conversation(history, message)
        conversation_messages = conversation_to_messages(conversation_items)
        return [SystemMessage(content=system_instruction)] + conversation_messages

    def parse_output(inputs: Dict[str, Any]) -> Tuple[str, List[Any]]:
        ai_message = inputs["ai_message"]
        candidate_dict = inputs["candidate_dict"]
        return parse_assistant_output(ai_message.content, candidate_dict)

    prompt_runnable = RunnableLambda(build_prompt_messages)

    chain = (
        RunnablePassthrough.assign(
            ai_message=prompt_runnable | model
        )
        | RunnableLambda(parse_output)
    )
    return chain
