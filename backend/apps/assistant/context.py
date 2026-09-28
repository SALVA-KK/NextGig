from typing import Any, Dict, List, Tuple
from django.utils import timezone
from apps.accounts.models import StudentProfile
from apps.opportunities.models import Opportunity


def sanitize_text(val: Any, max_len: int = 100) -> str:
    """
    Strips newlines, collapses consecutive whitespace, and caps length at max_len.
    """
    if val is None:
        return ""
    val_str = str(val)
    val_str = val_str.replace("\r", " ").replace("\n", " ")
    collapsed = " ".join(val_str.split())
    return collapsed[:max_len]


def get_student_profile_context(user) -> Dict[str, Any]:
    """
    Retrieves and sanitizes the requesting student's OWN profile data.
    """
    profile = StudentProfile.objects.filter(user=user).first()
    if not profile:
        return {
            "skills": [],
            "city": "",
            "qualification_type": "",
            "qualification_name": "",
            "institution": "",
            "availability": "",
            "languages": [],
        }

    raw_skills = profile.skills if isinstance(profile.skills, list) else []
    sanitized_skills = [sanitize_text(s, 100) for s in raw_skills[:30] if s and sanitize_text(s, 100)]

    raw_languages = profile.languages if isinstance(profile.languages, list) else []
    sanitized_languages = [sanitize_text(l, 100) for l in raw_languages[:30] if l and sanitize_text(l, 100)]

    return {
        "skills": sanitized_skills,
        "city": sanitize_text(profile.city, 100),
        "qualification_type": sanitize_text(profile.qualification_type, 100),
        "qualification_name": sanitize_text(profile.qualification_name, 100),
        "institution": sanitize_text(profile.institution, 100),
        "availability": sanitize_text(profile.availability, 100),
        "languages": sanitized_languages,
    }


def get_candidate_opportunities_context(student_profile_data: Dict[str, Any]) -> Tuple[Dict[int, Opportunity], List[Dict[str, Any]]]:
    """
    Queries open opportunities (status='open' AND (deadline is null OR deadline >= today)),
    ranks up to 200 rows by skill overlap, city match, and recency, and returns top 8.
    Returns:
    - candidate_rows: dict mapping opportunity ID to DB Opportunity instance (top 8)
    - sanitized_opts: list of sanitized opportunity dicts for prompt DATA block
    """
    today = timezone.localdate()

    # Query status='open' AND (deadline is null OR deadline >= today), newest first (-created_at)
    queryset = (
        Opportunity.objects.filter(status=Opportunity.Status.OPEN)
        .filter(deadline__isnull=True)
        | Opportunity.objects.filter(status=Opportunity.Status.OPEN).filter(deadline__gte=today)
    )

    candidate_pool = list(
        queryset.order_by("-created_at").only(
            "id",
            "title",
            "category",
            "city",
            "work_mode",
            "pay_type",
            "deadline",
            "required_skills",
            "created_at",
        )[:200]
    )

    student_skills_lower = set(s.lower() for s in student_profile_data.get("skills", []) if isinstance(s, str))
    student_city_lower = (student_profile_data.get("city") or "").lower()

    scored_candidates = []
    for opt in candidate_pool:
        opt_skills = opt.required_skills if isinstance(opt.required_skills, list) else []
        skill_overlap = sum(1 for s in opt_skills if isinstance(s, str) and s.lower() in student_skills_lower)
        city_match = 1 if opt.city and opt.city.lower() == student_city_lower and student_city_lower else 0

        # Tuple sort key: (-skill_overlap, -city_match)
        scored_candidates.append((skill_overlap, city_match, opt))

    # Python sort is stable, preserving -created_at order for equal scores
    scored_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top_8 = [item[2] for item in scored_candidates[:8]]

    candidate_rows = {opt.id: opt for opt in top_8}

    sanitized_opts = []
    for opt in top_8:
        raw_skills = opt.required_skills if isinstance(opt.required_skills, list) else []
        sanitized_skills = [sanitize_text(s, 100) for s in raw_skills[:10] if s and sanitize_text(s, 100)]

        sanitized_opts.append({
            "id": opt.id,
            "title": sanitize_text(opt.title, 100),
            "category": sanitize_text(opt.category, 100),
            "city": sanitize_text(opt.city, 100),
            "work_mode": sanitize_text(opt.work_mode, 100),
            "pay_type": sanitize_text(opt.pay_type, 100),
            "deadline": opt.deadline.isoformat() if opt.deadline else None,
            "required_skills": sanitized_skills,
        })

    return candidate_rows, sanitized_opts
