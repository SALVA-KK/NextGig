import hashlib
from typing import Any, List

from django.conf import settings
from apps.common.gemini_client import AIConfigError, AIFailureError, embed_texts
from apps.opportunities.models import Opportunity, OpportunityEmbedding


def sanitize_text(val: Any, max_len: int = 500) -> str:
    """
    Strips newlines, collapses consecutive whitespace, and caps length at max_len.
    """
    if val is None:
        return ""
    val_str = str(val).replace("\r", " ").replace("\n", " ")
    collapsed = " ".join(val_str.split())
    return collapsed[:max_len]


def build_opportunity_document(opportunity: Opportunity) -> str:
    """
    Constructs a plain-text document representation of an Opportunity for semantic embedding.
    Combines: title, category, description, required_skills, city, work_mode, location_text,
    duration, working_hours.

    Excludes: contact_info, poster details, user personal info, pay_amount, status, deadline.
    Capped at 3000 characters total.
    """
    sections: List[str] = []

    title = sanitize_text(getattr(opportunity, "title", ""), 200)
    if title:
        sections.append(f"Title: {title}")

    category = getattr(opportunity, "category", "")
    if hasattr(opportunity, "get_category_display"):
        category = opportunity.get_category_display()
    category = sanitize_text(category, 100)
    if category:
        sections.append(f"Category: {category}")

    work_mode = getattr(opportunity, "work_mode", "")
    if hasattr(opportunity, "get_work_mode_display"):
        work_mode = opportunity.get_work_mode_display()
    work_mode = sanitize_text(work_mode, 50)
    if work_mode:
        sections.append(f"Work Mode: {work_mode}")

    city = sanitize_text(getattr(opportunity, "city", ""), 100)
    if city:
        sections.append(f"City: {city}")

    location_text = sanitize_text(getattr(opportunity, "location_text", ""), 255)
    if location_text:
        sections.append(f"Location: {location_text}")

    duration = sanitize_text(getattr(opportunity, "duration", ""), 100)
    if duration:
        sections.append(f"Duration: {duration}")

    working_hours = sanitize_text(getattr(opportunity, "working_hours", ""), 100)
    if working_hours:
        sections.append(f"Working Hours: {working_hours}")

    raw_skills = getattr(opportunity, "required_skills", [])
    if isinstance(raw_skills, list):
        cleaned_skills = [sanitize_text(s, 50) for s in raw_skills if s and sanitize_text(s, 50)]
        if cleaned_skills:
            sections.append(f"Required Skills: {', '.join(cleaned_skills)}")

    description = sanitize_text(getattr(opportunity, "description", ""), 2000)
    if description:
        sections.append(f"Description: {description}")

    doc = "\n".join(sections)
    return doc[:3000]


def compute_content_hash(document: str) -> str:
    """
    Computes a deterministic SHA-256 hex digest of the document string.
    """
    if not document:
        return hashlib.sha256(b"").hexdigest()
    return hashlib.sha256(document.encode("utf-8")).hexdigest()


def index_opportunity(opportunity: Opportunity) -> str:
    """
    Synchronously updates or creates the OpportunityEmbedding for a single Opportunity.
    - Only opportunities with status == 'open' are indexed; returns 'skipped' for draft/closed.
    - Returns 'unchanged' if hash, embedding_model, and embedding_dim match stored values.
    - Otherwise calls embed_texts([doc], task_type='RETRIEVAL_DOCUMENT') and upserts the row.
    - Guards against embedding dimension mismatch with OpportunityEmbedding's VectorField.
    """
    if opportunity.status != Opportunity.Status.OPEN:
        return "skipped"

    # Dimension guard against VectorField dimension (768)
    vector_field_dim = OpportunityEmbedding._meta.get_field("embedding").dimensions
    dim_setting = getattr(settings, "GEMINI_EMBEDDING_DIM", None)
    if dim_setting != vector_field_dim:
        raise AIConfigError(
            f"Configured GEMINI_EMBEDDING_DIM ({dim_setting}) does not match "
            f"OpportunityEmbedding VectorField dimensions ({vector_field_dim})."
        )

    model_setting = getattr(settings, "GEMINI_EMBEDDING_MODEL", None)
    if not model_setting or not str(model_setting).strip():
        raise AIConfigError("GEMINI_EMBEDDING_MODEL is not configured in settings.")

    doc = build_opportunity_document(opportunity)
    content_hash = compute_content_hash(doc)

    existing = OpportunityEmbedding.objects.filter(opportunity=opportunity).first()
    if (
        existing is not None
        and existing.content_hash == content_hash
        and existing.embedding_model == model_setting
        and existing.embedding_dim == dim_setting
    ):
        return "unchanged"

    vectors = embed_texts([doc], task_type="RETRIEVAL_DOCUMENT")
    if not vectors or len(vectors) < 1:
        raise AIFailureError("Failed to obtain vector from embed_texts.")

    OpportunityEmbedding.objects.update_or_create(
        opportunity=opportunity,
        defaults={
            "embedding": vectors[0],
            "content_hash": content_hash,
            "embedding_model": model_setting,
            "embedding_dim": dim_setting,
        },
    )
    return "embedded"


__all__ = [
    "OpportunityEmbedding",
    "sanitize_text",
    "build_opportunity_document",
    "compute_content_hash",
    "index_opportunity",
]
