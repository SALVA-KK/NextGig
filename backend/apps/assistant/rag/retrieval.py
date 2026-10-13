import logging
from typing import Any, Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.utils import timezone
from pgvector.django import CosineDistance

from apps.assistant.context import get_candidate_opportunities_context, sanitize_text
from apps.common.gemini_client import (
    AIBusyError,
    AIConfigError,
    AIFailureError,
    embed_texts,
)
from apps.opportunities.models import Opportunity, OpportunityEmbedding

logger = logging.getLogger(__name__)

# Re-ranking weight constants
SKILL_OVERLAP_WEIGHT = 0.05
MAX_SKILL_OVERLAP = 3
CITY_MATCH_WEIGHT = 0.03


def get_query_embed_timeout() -> Union[int, float]:
    """
    Reads RAG_QUERY_EMBED_TIMEOUT_SECONDS from settings (default 5).
    Raises ImproperlyConfigured if invalid or non-positive.
    """
    raw_timeout = getattr(settings, "RAG_QUERY_EMBED_TIMEOUT_SECONDS", 5)
    if raw_timeout is None or (isinstance(raw_timeout, str) and not raw_timeout.strip()):
        return 5
    try:
        val = float(raw_timeout)
        if val <= 0:
            raise ValueError("Timeout must be positive.")
        return int(val) if val.is_integer() else val
    except (ValueError, TypeError) as exc:
        raise ImproperlyConfigured(
            f"Invalid RAG_QUERY_EMBED_TIMEOUT_SECONDS setting '{raw_timeout}': must be a positive number."
        ) from exc


def build_query_text(
    message: str,
    history: Optional[List[Dict[str, Any]]] = None,
    max_len: int = 500,
) -> str:

    """
    Builds a sanitized retrieval query combining the current message with up to the
    last 2 previous USER turns from history.
    - Strips/collapses whitespace and newlines.
    - Caps total string length at max_len.
    """
    user_turns: List[str] = []
    if history and isinstance(history, list):
        for item in history:
            if isinstance(item, dict) and item.get("role") == "user":
                content = item.get("content")
                if content and isinstance(content, str):
                    user_turns.append(content)

    recent_user_turns = user_turns[-2:]
    all_parts = recent_user_turns + ([message] if message else [])
    combined = " ".join(all_parts)
    collapsed = " ".join(combined.replace("\r", " ").replace("\n", " ").split())
    return collapsed[:max_len]


def sanitize_opportunity(opt: Opportunity) -> Dict[str, Any]:
    """
    Sanitizes an Opportunity instance into a dictionary matching exactly the shape
    and fields returned by apps.assistant.context.get_candidate_opportunities_context.
    """
    raw_skills = opt.required_skills if isinstance(opt.required_skills, list) else []
    sanitized_skills = [sanitize_text(s, 100) for s in raw_skills[:10] if s and sanitize_text(s, 100)]

    return {
        "id": opt.id,
        "title": sanitize_text(opt.title, 100),
        "category": sanitize_text(opt.category, 100),
        "city": sanitize_text(opt.city, 100),
        "work_mode": sanitize_text(opt.work_mode, 100),
        "pay_type": sanitize_text(opt.pay_type, 100),
        "deadline": opt.deadline.isoformat() if opt.deadline else None,
        "required_skills": sanitized_skills,
    }


def retrieve_with_source(
    query_text: str,
    student_profile_data: Optional[Dict[str, Any]] = None,
    k: int = 8,
    pool: int = 20,
    return_metadata: bool = False,
) -> Union[
    Tuple[Dict[int, Opportunity], List[Dict[str, Any]], str],
    Tuple[Dict[int, Opportunity], List[Dict[str, Any]], str, Dict[str, Any]],
]:
    """
    Performs vector similarity search against OpportunityEmbedding joined with Opportunity.
    - Annotates pgvector CosineDistance and limits to candidate pool.
    - Re-ranks candidates using similarity + skill overlap + city match.
    - Applies RAG_MIN_SIMILARITY threshold if set.
    - Falls back gracefully to heuristic context on AIBusyError, AIFailureError,
      AIConfigError, or when vector search returns 0 results.

    Returns:
    - (candidate_rows, sanitized_opts, "vector" | "fallback")
    - If return_metadata is True, returns 4-tuple with metadata dict containing top_similarity.
    """
    profile_data = student_profile_data or {}

    if not query_text or not query_text.strip():
        logger.info("Empty query text; falling back to heuristic context")
        rows, opts = get_candidate_opportunities_context(profile_data)
        if return_metadata:
            return rows, opts, "fallback", {"top_similarity": None}
        return rows, opts, "fallback"

    query_timeout = get_query_embed_timeout()

    try:
        vectors = embed_texts([query_text], task_type="RETRIEVAL_QUERY", timeout=query_timeout)
        if not vectors or not vectors[0]:
            raise AIFailureError("Empty vector response returned for query")
        query_vector = vectors[0]

    except (AIBusyError, AIFailureError, AIConfigError) as exc:
        logger.warning(
            "Vector embedding failed (%s); falling back to heuristic context",
            type(exc).__name__,
        )
        rows, opts = get_candidate_opportunities_context(profile_data)
        if return_metadata:
            return rows, opts, "fallback", {"top_similarity": None}
        return rows, opts, "fallback"

    today = timezone.localdate()
    embeddings_qs = (
        OpportunityEmbedding.objects.select_related("opportunity")
        .filter(
            opportunity__status=Opportunity.Status.OPEN,
            embedding_model=settings.GEMINI_EMBEDDING_MODEL,
            embedding_dim=settings.GEMINI_EMBEDDING_DIM,
        )
        .filter(
            Q(opportunity__deadline__isnull=True)
            | Q(opportunity__deadline__gte=today)
        )
        .annotate(distance=CosineDistance("embedding", query_vector))
        .order_by("distance")[:pool]
    )

    embeddings_list = list(embeddings_qs)
    if not embeddings_list:
        logger.info(
            "Vector search returned 0 embeddings in database; falling back to heuristic context"
        )
        rows, opts = get_candidate_opportunities_context(profile_data)
        if return_metadata:
            return rows, opts, "fallback", {"top_similarity": None}
        return rows, opts, "fallback"

    student_skills_lower = set(
        s.lower() for s in profile_data.get("skills", []) if isinstance(s, str)
    )
    student_city_lower = (profile_data.get("city") or "").lower()
    min_sim = getattr(settings, "RAG_MIN_SIMILARITY", None)

    scored_items: List[Dict[str, Any]] = []
    for emb in embeddings_list:
        opt = emb.opportunity
        similarity = 1.0 - float(emb.distance)

        if min_sim is not None and similarity < min_sim:
            continue

        opt_skills = opt.required_skills if isinstance(opt.required_skills, list) else []
        skill_overlap = sum(
            1 for s in opt_skills if isinstance(s, str) and s.lower() in student_skills_lower
        )
        city_match = (
            1 if opt.city and opt.city.lower() == student_city_lower and student_city_lower else 0
        )

        re_rank_score = (
            similarity
            + SKILL_OVERLAP_WEIGHT * min(skill_overlap, MAX_SKILL_OVERLAP)
            + CITY_MATCH_WEIGHT * city_match
        )
        scored_items.append({
            "opt": opt,
            "similarity": similarity,
            "score": re_rank_score,
        })

    if not scored_items:
        logger.info(
            "Vector search returned %d candidates but all were filtered by RAG_MIN_SIMILARITY; returning no_match",
            len(embeddings_list),
        )
        if return_metadata:
            return {}, [], "no_match", {"top_similarity": None}
        return {}, [], "no_match"


    scored_items.sort(key=lambda x: (x["score"], x["similarity"]), reverse=True)
    top_k_items = scored_items[:k]
    top_k = [item["opt"] for item in top_k_items]
    top_similarity = top_k_items[0]["similarity"] if top_k_items else None

    candidate_rows = {opt.id: opt for opt in top_k}
    sanitized_opts = [sanitize_opportunity(opt) for opt in top_k]

    if return_metadata:
        return candidate_rows, sanitized_opts, "vector", {"top_similarity": top_similarity}
    return candidate_rows, sanitized_opts, "vector"


def retrieve_candidate_opportunities(
    query_text: str,
    student_profile_data: Optional[Dict[str, Any]] = None,
    k: int = 8,
    pool: int = 20,
) -> Tuple[Dict[int, Opportunity], List[Dict[str, Any]]]:
    """
    Retrieves the top k candidate opportunities for the given query text and student profile.
    Returns (candidate_rows, sanitized_opts) matching exactly the contract of
    apps.assistant.context.get_candidate_opportunities_context.
    """
    rows, opts, _ = retrieve_with_source(
        query_text=query_text,
        student_profile_data=student_profile_data,
        k=k,
        pool=pool,
        return_metadata=False,
    )
    return rows, opts
