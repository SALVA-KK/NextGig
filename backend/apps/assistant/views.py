import json
import logging
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiTypes

from apps.accounts.permissions import IsStudentRole
from apps.assistant.serializers import AssistantChatSerializer
from apps.assistant.throttling import (
    AssistantBurstRateThrottle,
    AssistantSustainedRateThrottle,
)
from apps.assistant.constants import SYSTEM_INSTRUCTION_BASE, PLATFORM_FACT_SHEET
from apps.assistant.context import (
    get_student_profile_context,
    get_candidate_opportunities_context,
)
from apps.common.gemini_client import (
    generate_text,
    AIConfigError,
    AIBusyError,
    AIFailureError,
)

logger = logging.getLogger(__name__)


def build_conversation(history_items, new_message):
    """
    Format history items + new_message into conversation items for generate_text:
    list of {"role": "user"|"model", "text": str}.
    - Maps "user" -> "user", "assistant" -> "model".
    - Drops leading "model" ("assistant") items.
    - Merges consecutive same-role items.
    - Appends new_message as final "user" turn.
    """
    turns = []
    for item in history_items:
        role = "user" if item["role"] == "user" else "model"
        text = item["content"]
        turns.append({"role": role, "text": text})

    # Drop leading "model" turns
    while turns and turns[0]["role"] == "model":
        turns.pop(0)

    # Merge consecutive same-role turns
    merged = []
    for turn in turns:
        if merged and merged[-1]["role"] == turn["role"]:
            merged[-1]["text"] = merged[-1]["text"] + "\n\n" + turn["text"]
        else:
            merged.append(turn)

    # Append new_message as final user turn
    if merged and merged[-1]["role"] == "user":
        merged[-1]["text"] = merged[-1]["text"] + "\n\n" + new_message
    else:
        merged.append({"role": "user", "text": new_message})

    return merged


class AssistantChatView(APIView):
    """
    POST /api/assistant/chat/
    Read-only AI chat assistant for NextGig students.
    Answers platform questions and suggests relevant open opportunities.
    """

    permission_classes = [permissions.IsAuthenticated, IsStudentRole]
    throttle_classes = [AssistantBurstRateThrottle, AssistantSustainedRateThrottle]

    @extend_schema(
        summary="AI Chat Assistant for Students",
        description="Answers NextGig platform questions and suggests relevant open opportunities for students.",
        request=AssistantChatSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 502: OpenApiTypes.OBJECT, 503: OpenApiTypes.OBJECT},
    )
    def post(self, request):
        serializer = AssistantChatSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        message = validated_data["message"]
        history = validated_data.get("history", [])

        # 1. Build context data
        profile_data = get_student_profile_context(request.user)
        candidate_rows, sanitized_opts = get_candidate_opportunities_context(profile_data)

        # 2. Build full system instruction
        system_instruction = (
            f"{SYSTEM_INSTRUCTION_BASE}\n\n"
            "DATA BLOCKS:\n\n"
            "--- STUDENT PROFILE DATA ---\n"
            f"{json.dumps(profile_data, indent=2)}\n\n"
            "--- PLATFORM FACT SHEET ---\n"
            f"{PLATFORM_FACT_SHEET}\n\n"
            "--- CANDIDATE OPPORTUNITIES DATA ---\n"
            f"{json.dumps(sanitized_opts, indent=2)}"
        )

        # 3. Format conversation turns
        conversation_items = build_conversation(history, message)

        # 4. Call model via helper
        try:
            raw_text = generate_text(
                contents=conversation_items,
                system_instruction=system_instruction,
                max_output_tokens=400,
            )
        except AIConfigError as exc:
            logger.error(f"Gemini API failure: {type(exc).__name__}")
            return Response(
                {"detail": "The assistant is not available right now."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIBusyError as exc:
            logger.error(f"Gemini API failure: {type(exc).__name__}")
            return Response(
                {"detail": "The assistant is busy right now. Please try again in a minute."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AIFailureError as exc:
            logger.error(f"Gemini API failure: {type(exc).__name__}")
            return Response(
                {"detail": "The assistant couldn't answer right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:
            logger.error(f"Gemini API unexpected failure: {type(exc).__name__}")
            return Response(
                {"detail": "The assistant couldn't answer right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # 5. Parse response
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
            return Response(
                {"reply": reply_text, "opportunities": []},
                status=status.HTTP_200_OK,
            )

        reply_val = parsed_json.get("reply")
        if not isinstance(reply_val, str) or not reply_val.strip():
            logger.error("Parsed assistant response missing or invalid string 'reply'.")
            return Response(
                {"detail": "The assistant couldn't answer right now. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        reply_text = reply_val.strip()[:1200]
        raw_opp_ids = parsed_json.get("opportunity_ids", [])
        if not isinstance(raw_opp_ids, list):
            raw_opp_ids = []

        valid_opp_objs = []
        candidate_ids_set = set(candidate_rows.keys())
        for item in raw_opp_ids:
            try:
                item_int = int(item)
                if item_int in candidate_ids_set and item_int not in [o.id for o in valid_opp_objs]:
                    valid_opp_objs.append(candidate_rows[item_int])
                    if len(valid_opp_objs) >= 3:
                        break
            except (ValueError, TypeError):
                continue

        opportunities_data = [
            {
                "id": opt.id,
                "title": opt.title,
                "category": opt.category,
                "city": opt.city,
                "work_mode": opt.work_mode,
                "pay_type": opt.pay_type,
                "deadline": opt.deadline.isoformat() if opt.deadline else None,
            }
            for opt in valid_opp_objs
        ]

        return Response(
            {
                "reply": reply_text,
                "opportunities": opportunities_data,
            },
            status=status.HTTP_200_OK,
        )
