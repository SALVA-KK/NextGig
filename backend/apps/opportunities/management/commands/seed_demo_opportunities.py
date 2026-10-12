import datetime
import logging
from typing import Any, Dict, List

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.opportunities.models import Opportunity

logger = logging.getLogger(__name__)

DEMO_LISTINGS: List[Dict[str, Any]] = [
    {
        "title": "UI/UX Design Intern for a Mobile App",
        "category": Opportunity.Category.INTERNSHIP,
        "work_mode": Opportunity.WorkMode.HYBRID,
        "city": "Kochi",
        "pay_type": Opportunity.PayType.STIPEND,
        "skills": ["Figma", "wireframing", "user research"],
        "days": 45,
        "description": (
            "Help design screens for a student budgeting app. You will create wireframes in Figma, "
            "run small usability tests, and work with two developers. No prior job experience needed; "
            "a portfolio of class projects is enough."
        ),
    },
    {
        "title": "Social Media Content Creator",
        "category": Opportunity.Category.PART_TIME,
        "work_mode": Opportunity.WorkMode.REMOTE,
        "city": "Remote",
        "pay_type": Opportunity.PayType.MONTHLY,
        "skills": ["Instagram", "copywriting", "Canva"],
        "days": 30,
        "description": (
            "Plan and post short videos and graphics for a campus lifestyle brand. About 15 hours a week, "
            "flexible timings. You should understand trends and write catchy captions."
        ),
    },
    {
        "title": "Maths Tutor for Class 10 Students",
        "category": Opportunity.Category.TUTORING,
        "work_mode": Opportunity.WorkMode.ONSITE,
        "city": "Kozhikode",
        "pay_type": Opportunity.PayType.HOURLY,
        "skills": ["Mathematics", "teaching", "patience"],
        "days": 40,
        "description": (
            "Teach algebra and geometry to small groups of Class 10 students on weekday evenings. "
            "Strong fundamentals and clear explanation matter more than degrees."
        ),
    },
    {
        "title": "YouTube Video Editor",
        "category": Opportunity.Category.FREELANCE,
        "work_mode": Opportunity.WorkMode.REMOTE,
        "city": "Remote",
        "pay_type": Opportunity.PayType.HOURLY,
        "skills": ["Premiere Pro", "DaVinci Resolve", "storytelling"],
        "days": 35,
        "description": (
            "Edit weekly educational videos for a tech channel, including cuts, captions and basic motion graphics. "
            "Paid per video with steady work for the right person."
        ),
    },
    {
        "title": "Volunteers for College Tech Fest",
        "category": Opportunity.Category.EVENT_BASED,
        "work_mode": Opportunity.WorkMode.ONSITE,
        "city": "Thrissur",
        "pay_type": Opportunity.PayType.UNPAID,
        "skills": ["Event management", "communication", "teamwork"],
        "days": 25,
        "description": (
            "Help run registration, stage coordination and guest hospitality during a two-day technical festival. "
            "Certificate and meals provided."
        ),
    },
    {
        "title": "Digital Marketing Intern",
        "category": Opportunity.Category.INTERNSHIP,
        "work_mode": Opportunity.WorkMode.REMOTE,
        "city": "Remote",
        "pay_type": Opportunity.PayType.STIPEND,
        "skills": ["SEO", "Google Analytics", "email marketing"],
        "days": 50,
        "description": (
            "Support a small e-commerce startup with search optimisation, newsletters and simple campaign reports. "
            "You will learn the tools while working on real campaigns."
        ),
    },
    {
        "title": "WordPress Website for a Local Bakery",
        "category": Opportunity.Category.FREELANCE,
        "work_mode": Opportunity.WorkMode.REMOTE,
        "city": "Kochi",
        "pay_type": Opportunity.PayType.MONTHLY,
        "skills": ["WordPress", "Elementor", "basic SEO"],
        "days": 28,
        "description": (
            "Build a five-page website with an online menu and order enquiry form for a neighbourhood bakery. "
            "One-time project with a clear scope and deadline."
        ),
    },
    {
        "title": "Event Photographer for Cultural Fest",
        "category": Opportunity.Category.FREELANCE,
        "work_mode": Opportunity.WorkMode.ONSITE,
        "city": "Calicut",
        "pay_type": Opportunity.PayType.HOURLY,
        "skills": ["Photography", "Lightroom", "event coverage"],
        "days": 20,
        "description": (
            "Capture photographs of performances and winners during a college cultural festival and deliver edited pictures within three days."
        ),
    },
    {
        "title": "Data Entry Assistant",
        "category": Opportunity.Category.PART_TIME,
        "work_mode": Opportunity.WorkMode.REMOTE,
        "city": "Remote",
        "pay_type": Opportunity.PayType.MONTHLY,
        "skills": ["Excel", "typing", "attention to detail"],
        "days": 33,
        "description": (
            "Enter and verify product details in spreadsheets for an online store. Work from home with flexible hours; accuracy is the main requirement."
        ),
    },
    {
        "title": "Campus Ambassador for an Ed-Tech Startup",
        "category": Opportunity.Category.PART_TIME,
        "work_mode": Opportunity.WorkMode.HYBRID,
        "city": "Bangalore",
        "pay_type": Opportunity.PayType.STIPEND,
        "skills": ["Communication", "networking", "leadership"],
        "days": 60,
        "description": (
            "Represent a learning platform on your campus by organising small workshops and sharing opportunities with classmates. Good for students who like meeting people."
        ),
    },
    {
        "title": "Python Automation Scripts for a Small Business",
        "category": Opportunity.Category.FREELANCE,
        "work_mode": Opportunity.WorkMode.REMOTE,
        "city": "Remote",
        "pay_type": Opportunity.PayType.HOURLY,
        "skills": ["Python", "pandas", "automation"],
        "days": 38,
        "description": (
            "Write scripts to clean spreadsheets and generate weekly reports for a family-run distribution business. Clear written requirements are provided."
        ),
    },
    {
        "title": "Mobile App Beta Testers",
        "category": Opportunity.Category.PROJECT_COLLABORATION,
        "work_mode": Opportunity.WorkMode.REMOTE,
        "city": "Remote",
        "pay_type": Opportunity.PayType.UNPAID,
        "skills": ["Testing", "feedback", "Android"],
        "days": 42,
        "description": (
            "Try an early version of a study planner app, report bugs, and suggest improvements. Great for students who want to see how products are built."
        ),
    },
]


class Command(BaseCommand):
    help = "Seed realistic demo opportunities for a provider account and optionally close obsolete listings."

    def add_arguments(self, parser):
        parser.add_argument(
            "--poster-email",
            type=str,
            required=True,
            help="Email address of the existing provider account who will own the listings.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate actions without writing to the database.",
        )
        parser.add_argument(
            "--close-ids",
            type=str,
            default="",
            help="Comma-separated opportunity IDs to close (only if currently open).",
        )

    def handle(self, *args, **options):
        poster_email = (options.get("poster_email") or options.get("poster-email") or "").strip()
        dry_run = options.get("dry_run", False)
        close_ids_raw = (options.get("close_ids") or options.get("close-ids") or "").strip()

        User = get_user_model()

        # 1. Validate provider user
        if not poster_email:
            raise CommandError("Option --poster-email is required.")

        try:
            user = User.objects.get(email__iexact=poster_email)
        except User.DoesNotExist:
            raise CommandError(f"User with email '{poster_email}' does not exist.")

        provider_role = getattr(User.Role, "PROVIDER", "provider")
        if user.role != provider_role:
            raise CommandError(
                f"User '{poster_email}' has role '{user.role}', but must be a provider."
            )

        self.stdout.write(f"Operating for provider: {user.email} (ID: {user.id})")

        # 2. Process --close-ids if provided
        closed_count = 0
        if close_ids_raw:
            raw_id_list = [s.strip() for s in close_ids_raw.split(",") if s.strip()]
            for raw_id in raw_id_list:
                try:
                    opp_id = int(raw_id)
                except ValueError:
                    self.stdout.write(
                        self.style.WARNING(f"Invalid opportunity ID '{raw_id}', skipping.")
                    )
                    continue

                opp_to_close = Opportunity.objects.filter(id=opp_id).first()
                if not opp_to_close:
                    self.stdout.write(
                        self.style.WARNING(f"Opportunity #{opp_id} not found, skipping.")
                    )
                    continue

                if opp_to_close.status == Opportunity.Status.OPEN:
                    if not dry_run:
                        opp_to_close.status = Opportunity.Status.CLOSED
                        opp_to_close.close_reason = Opportunity.CloseReason.ADMIN_MODERATED
                        opp_to_close.closed_by = None
                        opp_to_close.save()
                    closed_count += 1
                    msg_prefix = "[DRY-RUN] Would close" if dry_run else "Closed"
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{msg_prefix} open opportunity #{opp_to_close.id}: '{opp_to_close.title}'"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.NOTICE(
                            f"Opportunity #{opp_to_close.id} status is already '{opp_to_close.status}', left untouched."
                        )
                    )

        # 3. Seed listings
        today = timezone.localdate()
        created_items: List[Opportunity] = []
        existing_items: List[Opportunity] = []
        dry_run_items: List[Dict[str, Any]] = []

        for item in DEMO_LISTINGS:
            title = item["title"]
            existing = Opportunity.objects.filter(poster=user, title=title).first()

            deadline = today + datetime.timedelta(days=item["days"])

            if existing:
                existing_items.append(existing)
                self.stdout.write(self.style.NOTICE(f"[exists] '{title}' (ID: {existing.id})"))
            elif dry_run:
                dry_run_items.append({
                    "id": "-",
                    "title": title,
                    "category": item["category"],
                    "city": item["city"],
                    "deadline": deadline,
                })
                self.stdout.write(self.style.SUCCESS(f"[DRY-RUN would create] '{title}' (deadline in {item['days']} days)"))
            else:
                new_opp = Opportunity(
                    poster=user,
                    title=title,
                    category=item["category"],
                    work_mode=item["work_mode"],
                    city=item["city"],
                    pay_type=item["pay_type"],
                    required_skills=item["skills"],
                    deadline=deadline,
                    description=item["description"],
                    vacancies=1,
                    status=Opportunity.Status.OPEN,
                    contact_info="Apply through NextGig",
                )
                new_opp.save()
                created_items.append(new_opp)
                self.stdout.write(self.style.SUCCESS(f"[created] '{title}' (ID: {new_opp.id})"))

        # 4. Print Table: id | title | category | city | deadline
        self.stdout.write("\n" + "=" * 105)
        self.stdout.write(
            f"{'ID':<6} | {'Title':<45} | {'Category':<20} | {'City':<12} | {'Deadline':<10}"
        )
        self.stdout.write("-" * 105)

        all_display_items = []
        for opp in created_items:
            all_display_items.append({
                "id": str(opp.id),
                "title": opp.title,
                "category": opp.get_category_display(),
                "city": opp.city,
                "deadline": opp.deadline.isoformat() if opp.deadline else "-",
            })

        for opp in existing_items:
            all_display_items.append({
                "id": str(opp.id),
                "title": opp.title,
                "category": opp.get_category_display(),
                "city": opp.city,
                "deadline": opp.deadline.isoformat() if opp.deadline else "-",
            })

        for item_data in dry_run_items:
            cat_display = item_data["category"]
            for choice in Opportunity.Category.choices:
                if choice[0] == item_data["category"]:
                    cat_display = choice[1]
                    break
            all_display_items.append({
                "id": item_data["id"],
                "title": item_data["title"],
                "category": str(cat_display),
                "city": item_data["city"],
                "deadline": item_data["deadline"].isoformat(),
            })

        for row in all_display_items:
            truncated_title = row["title"][:42] + "..." if len(row["title"]) > 45 else row["title"]
            self.stdout.write(
                f"{row['id']:<6} | {truncated_title:<45} | {row['category']:<20} | {row['city']:<12} | {row['deadline']:<10}"
            )

        self.stdout.write("=" * 105)

        # 5. Summary
        created_count = len(created_items) if not dry_run else len(dry_run_items)
        created_label = "Would create" if dry_run else "Created"
        self.stdout.write(
            self.style.SUCCESS(
                f"Summary: {created_label}: {created_count}, Existing: {len(existing_items)}, "
                f"Closed: {closed_count}{' [DRY-RUN]' if dry_run else ''}"
            )
        )
