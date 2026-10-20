"""
LangGraph agent for NextGig Student Assistant.
Implements a read-only agent with tool-calling capabilities, hard step caps,
and strict privacy isolation for student profile data.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, TypedDict

from langgraph.graph import StateGraph, START, END

from apps.assistant.constants import PLATFORM_FACT_SHEET, SYSTEM_INSTRUCTION_BASE
from apps.assistant.context import get_student_profile_context
from apps.assistant.rag.retrieval import build_query_text, retrieve_with_source
from apps.assistant.views import build_conversation
from apps.common.gemini_client import (
    AIBusyError,
    AIConfigError,
    AIFailureError,
    generate_text,
)

logger = logging.getLogger(__name__)


class GraphError(Exception):
    """Raised when the LangGraph agent encounters an unexpected or malformed state."""
    pass


class AgentState(TypedDict):
    """
    State container for the student assistant LangGraph agent.
    """
    messages: List[Any]
    step_count: int
    final_output: Optional[Dict[str, Any]]
    pending_action: Optional[Dict[str, Any]]
    profile_data: Dict[str, Any]
    candidate_dict: Dict[int, Any]
    candidate_opportunities: List[Dict[str, Any]]
    source: str
    user_message: str
    history: List[Dict[str, str]]
    last_action_text: str
    tool_feedback: str


# ----------------------------------------------------------------------
# Read-only Tools
# ----------------------------------------------------------------------
def retrieve_opportunities(
    query: str,
    student_profile_data: Dict[str, Any],
    retrieve_fn: Optional[Any] = None,
) -> Tuple[Dict[int, Any], List[Dict[str, Any]], str]:
    """
    Read-only tool: retrieves candidate opportunities using retrieve_with_source.
    Scoped strictly to the authenticated student's sanitized profile.
    Accepts ONLY a query string from the model (no model-supplied user or id arguments).
    """
    fn = retrieve_fn or retrieve_with_source
    query_str = str(query or "").strip()
    return fn(query_text=query_str, student_profile_data=student_profile_data)


def get_my_profile(student_profile_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Read-only tool: returns the existing sanitized profile dictionary for request.user only.
    Accepts NO model-supplied user or id arguments.
    """
    return student_profile_data


# ----------------------------------------------------------------------
# Output Validation Helper
# ----------------------------------------------------------------------
def validate_final_answer(
    parsed_json: Dict[str, Any],
    candidate_dict: Dict[int, Any],
) -> Tuple[str, List[Any]]:
    """
    Validates final answer JSON:
    - Requires non-empty string 'reply'.
    - Checks 'opportunity_ids' against candidate_dict. Drops invalid IDs.
    - Max 3 opportunities, deduplicated.
    """
    reply_val = parsed_json.get("reply")
    if not isinstance(reply_val, str) or not reply_val.strip():
        raise GraphError("Parsed assistant response missing or invalid string 'reply'.")

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


# ----------------------------------------------------------------------
# Graph Construction
# ----------------------------------------------------------------------
def create_agent_graph(
    user: Any,
    profile_data: Dict[str, Any],
    generate_fn: Optional[Any] = None,
    retrieve_fn: Optional[Any] = None,
):
    """
    Constructs and compiles the StateGraph for the student assistant.
    Enforces a hard cap of at most 2 model calls per question.
    """
    gen_call = generate_fn or generate_text

    def agent_node(state: AgentState) -> Dict[str, Any]:
        step_count = state.get("step_count", 0)
        history = state.get("history", [])
        user_message = state.get("user_message", "")
        profile = state.get("profile_data", profile_data)
        candidate_opps = state.get("candidate_opportunities", [])
        candidate_dict = state.get("candidate_dict", {})
        source = state.get("source", "vector")

        # Hard cap safety check: if already reached 2 model calls, produce graceful reply
        if step_count >= 2:
            fallback_reply = (
                "Here are the opportunities I found for your search."
                if candidate_opps
                else "I'm sorry, I couldn't finish processing your request. Please try asking again."
            )
            valid_objs = list(candidate_dict.values())[:3] if candidate_opps else []
            return {
                "final_output": {"reply": fallback_reply, "valid_opp_objs": valid_objs},
                "pending_action": None,
            }

        base_instruction = SYSTEM_INSTRUCTION_BASE
        if source == "no_match":
            base_instruction = (
                f"{base_instruction}\n"
                "If the candidate list is empty, say that no listing matches and suggest browsing the Opportunities page."
            )

        if step_count == 0:
            action_instructions = (
                "\n\nINSTRUCTIONS FOR RESPONSE FORMAT:\n"
                "You MUST reply ONLY with a valid JSON object, in one of these three formats:\n"
                '1. To search for matching opportunities: {"action": "retrieve", "query": "<search keywords>"}\n'
                '2. To inspect the student profile: {"action": "profile"}\n'
                '3. To answer directly without searching: {"reply": "<your answer>", "opportunity_ids": [<ids from candidate opportunities only>]}\n'
                "Never include any text outside the JSON object.\n"
                "If the student asks about opportunities, internships, jobs, gigs, events, or what to apply for, you MUST reply with the retrieve action first. Answer directly only for platform questions or greetings.\n"
                "If the student refers to earlier opportunities (for example 'those', 'it', 'the first one') or asks about remote, location, pay or deadline, use the opportunities in CANDIDATE OPPORTUNITIES DATA if present; if the list is empty, reply with the retrieve action using keywords from the earlier conversation."
            )
        else:
            action_instructions = (
                "\n\nINSTRUCTIONS FOR RESPONSE FORMAT:\n"
                "You MUST now provide your final reply to the student. Do NOT request any more actions or tools.\n"
                'Output ONLY a JSON object: {"reply": "<text>", "opportunity_ids": [<ids from candidate opportunities only>]}\n'
                "Never include any text outside the JSON object."
            )

        system_instruction = (
            f"{base_instruction}\n\n"
            "DATA BLOCKS:\n\n"
            "--- STUDENT PROFILE DATA ---\n"
            f"{json.dumps(profile, indent=2)}\n\n"
            "--- PLATFORM FACT SHEET ---\n"
            f"{PLATFORM_FACT_SHEET}\n\n"
            "--- CANDIDATE OPPORTUNITIES DATA ---\n"
            f"{json.dumps(candidate_opps, indent=2)}"
            f"{action_instructions}"
        )

        base_conv = build_conversation(history, user_message)
        if step_count == 0:
            contents = base_conv
        else:
            prev_action = state.get("last_action_text", '{"action": "tool"}')
            tool_feedback = state.get("tool_feedback", "Tool executed. Candidate opportunities loaded.")
            contents = base_conv + [
                {"role": "model", "text": prev_action},
                {"role": "user", "text": tool_feedback},
            ]

        raw_output = gen_call(
            contents=contents,
            system_instruction=system_instruction,
            max_output_tokens=400,
        )

        new_step_count = step_count + 1

        clean_text = raw_output.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        clean_text = clean_text.strip()

        parsed_json = None
        if clean_text.startswith("{") or clean_text.startswith("["):
            try:
                parsed_json = json.loads(clean_text)
            except Exception as exc:
                raise GraphError(f"Malformed JSON from model: {raw_output}") from exc
        elif not clean_text:
            raise GraphError("Empty response from model")
        else:
            # Plain text response: accepted as reply with no opportunities
            reply_text = clean_text[:1200]
            return {
                "step_count": new_step_count,
                "final_output": {"reply": reply_text, "valid_opp_objs": []},
                "pending_action": None,
            }

        if not isinstance(parsed_json, dict):
            raise GraphError("Model JSON output must be a JSON object")

        if "action" in parsed_json:
            # HARD CAP: after 1 tool call, step_count reaches 2 on this return
            if new_step_count >= 2:
                # Model asked for a tool again despite cap: end after 2 model calls with graceful reply
                fallback_reply = (
                    "Here are the opportunities I found for your search."
                    if candidate_opps
                    else "I'm sorry, I couldn't finish processing your request. Please try asking again."
                )
                valid_objs = list(candidate_dict.values())[:3] if candidate_opps else []
                return {
                    "step_count": new_step_count,
                    "final_output": {"reply": fallback_reply, "valid_opp_objs": valid_objs},
                    "pending_action": None,
                }
            return {
                "step_count": new_step_count,
                "pending_action": parsed_json,
                "last_action_text": raw_output,
            }

        if "reply" in parsed_json:
            reply_text, valid_opp_objs = validate_final_answer(parsed_json, candidate_dict)
            return {
                "step_count": new_step_count,
                "final_output": {"reply": reply_text, "valid_opp_objs": valid_opp_objs},
                "pending_action": None,
            }

        raise GraphError("JSON response did not contain 'action' or 'reply'")

    def tools_node(state: AgentState) -> Dict[str, Any]:
        action_dict = state.get("pending_action") or {}
        action = action_dict.get("action")

        if action == "retrieve":
            query = action_dict.get("query", "")
            cand_dict, cand_opps, src = retrieve_opportunities(
                query=query,
                student_profile_data=state.get("profile_data", profile_data),
                retrieve_fn=retrieve_fn,
            )
            feedback = f"Retrieved {len(cand_opps)} matching opportunities. Opportunities loaded into DATA BLOCKS."
            return {
                "candidate_dict": cand_dict,
                "candidate_opportunities": cand_opps,
                "source": src,
                "pending_action": None,
                "tool_feedback": feedback,
            }
        elif action == "profile":
            prof = get_my_profile(state.get("profile_data", profile_data))
            feedback = f"Student profile retrieved: {json.dumps(prof)}. Profile loaded into DATA BLOCKS."
            return {
                "profile_data": prof,
                "pending_action": None,
                "tool_feedback": feedback,
            }
        else:
            raise GraphError(f"Unknown action '{action}' requested by model")

    def route_agent(state: AgentState) -> str:
        if state.get("final_output") is not None:
            return END
        if state.get("pending_action") is not None:
            return "tools"
        return END

    workflow = StateGraph(AgentState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.add_edge(START, "agent")
    workflow.add_conditional_edges("agent", route_agent, ["tools", END])
    workflow.add_edge("tools", "agent")

    return workflow.compile()


def run_langgraph_agent(
    message: str,
    history: List[Dict[str, str]],
    user: Any,
    generate_fn: Optional[Any] = None,
    retrieve_fn: Optional[Any] = None,
) -> Tuple[str, List[Any]]:
    """
    Executes the LangGraph agent for the student assistant.
    Returns:
    - reply_text: str
    - valid_opp_objs: list of Opportunity instances
    """
    profile_data = get_student_profile_context(user)
    candidate_dict: Dict[int, Any] = {}
    candidate_opportunities: List[Dict[str, Any]] = []
    source = "vector"

    if history:
        try:
            retrieve_call = retrieve_fn or retrieve_with_source
            query_text = build_query_text(message, history)
            candidate_dict, candidate_opportunities, source = retrieve_call(
                query_text=query_text,
                student_profile_data=profile_data,
            )
        except (AIConfigError, AIBusyError, AIFailureError):
            raise
        except Exception as exc:
            logger.warning(
                "Assistant pre-load retrieval error (%s); proceeding with empty candidates",
                type(exc).__name__,
            )
            candidate_dict = {}
            candidate_opportunities = []
            source = "vector"

    app = create_agent_graph(
        user=user,
        profile_data=profile_data,
        generate_fn=generate_fn,
        retrieve_fn=retrieve_fn,
    )
    initial_state: AgentState = {
        "messages": [],
        "step_count": 0,
        "final_output": None,
        "pending_action": None,
        "profile_data": profile_data,
        "candidate_dict": candidate_dict,
        "candidate_opportunities": candidate_opportunities,
        "source": source,
        "user_message": message,
        "history": history,
        "last_action_text": "",
        "tool_feedback": "",
    }
    result_state = app.invoke(initial_state)
    final_output = result_state.get("final_output")
    if not final_output:
        raise GraphError("LangGraph agent finished without final output")
    return final_output["reply"], final_output["valid_opp_objs"]
