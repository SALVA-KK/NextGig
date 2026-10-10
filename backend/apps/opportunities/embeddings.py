import hashlib
from typing import Any, List

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


__all__ = [
    "OpportunityEmbedding",
    "sanitize_text",
    "build_opportunity_document",
    "compute_content_hash",
]
