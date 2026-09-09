from datetime import timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.accounts.models import ProviderProfile
from apps.opportunities.models import Opportunity

User = get_user_model()


class Command(BaseCommand):
    help = "Seed realistic sample data (providers, students, opportunities, and student project collaborations) for demoing NextGig."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting NextGig demo data seeding..."))

        # 1. Create Provider Accounts & Profiles
        providers_data = [
            {
                "email": "demo_provider1@example.com",
                "full_name": "Sarah Connor",
                "organization_name": "TechCorp Solutions",
                "organization_type": ProviderProfile.OrganizationType.COMPANY,
                "description": "Leading software development and IT consulting firm building enterprise products.",
                "contact_person": "Sarah Connor",
                "website": "https://techcorp.example.com",
                "city": "Bangalore",
            },
            {
                "email": "demo_provider2@example.com",
                "full_name": "Vikram Mehta",
                "organization_name": "InnovateLab AI",
                "organization_type": ProviderProfile.OrganizationType.STARTUP,
                "description": "AI-driven startup building next-gen developer productivity and automation tools.",
                "contact_person": "Vikram Mehta",
                "website": "https://innovatelab.example.com",
                "city": "Mumbai",
            },
            {
                "email": "demo_provider3@example.com",
                "full_name": "Ananya Roy",
                "organization_name": "Artisan Coffee Roasters",
                "organization_type": ProviderProfile.OrganizationType.CAFE,
                "description": "Boutique specialty coffee chain and community hub offering part-time student barista roles.",
                "contact_person": "Ananya Roy",
                "website": "https://artisancoffee.example.com",
                "city": "Delhi",
            },
            {
                "email": "demo_provider4@example.com",
                "full_name": "David Miller",
                "organization_name": "EcoGreen Foundation",
                "organization_type": ProviderProfile.OrganizationType.NGO,
                "description": "Non-profit organization dedicated to urban reforestation, sustainability, and green education.",
                "contact_person": "David Miller",
                "website": "https://ecogreen.example.com",
                "city": "Hyderabad",
            },
        ]

        providers = {}
        for pdata in providers_data:
            user, created = User.objects.get_or_create(
                email=pdata["email"],
                defaults={
                    "full_name": pdata["full_name"],
                    "role": User.Role.PROVIDER,
                    "is_verified": True,
                },
            )
            if created:
                user.set_password("Password123!")
                user.save()
                self.stdout.write(f"  Created Provider User: {user.email}")
            else:
                self.stdout.write(f"  Found Provider User: {user.email}")

            profile, prof_created = ProviderProfile.objects.get_or_create(
                user=user,
                defaults={
                    "organization_name": pdata["organization_name"],
                    "organization_type": pdata["organization_type"],
                    "description": pdata["description"],
                    "contact_person": pdata["contact_person"],
                    "website": pdata["website"],
                    "city": pdata["city"],
                    "is_verified": True,
                },
            )
            providers[pdata["email"]] = user

        # 2. Create Student Accounts
        students_data = [
            {"email": "demo_student1@example.com", "full_name": "Alex Rivera", "phone": "+919876543210"},
            {"email": "demo_student2@example.com", "full_name": "Priya Sharma", "phone": "+919876543211"},
            {"email": "demo_student3@example.com", "full_name": "Liam Chen", "phone": "+919876543212"},
        ]

        students = {}
        for sdata in students_data:
            user, created = User.objects.get_or_create(
                email=sdata["email"],
                defaults={
                    "full_name": sdata["full_name"],
                    "phone_number": sdata["phone"],
                    "role": User.Role.STUDENT,
                    "is_verified": True,
                },
            )
            if created:
                user.set_password("Password123!")
                user.save()
                self.stdout.write(f"  Created Student User: {user.email}")
            else:
                self.stdout.write(f"  Found Student User: {user.email}")
            students[sdata["email"]] = user

        today = timezone.localdate()

        # 3. Create Provider Opportunities across various categories
        provider_opps_data = [
            {
                "poster": providers["demo_provider1@example.com"],
                "title": "Frontend React Developer Intern",
                "description": "Join TechCorp Solutions as a Frontend Engineering Intern. You will work alongside senior engineers to build responsive Web dashboards using React, TypeScript, and modern CSS frameworks.",
                "category": Opportunity.Category.INTERNSHIP,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "city": "Bangalore",
                "pay_type": Opportunity.PayType.STIPEND,
                "pay_amount": Decimal("15000.00"),
                "vacancies": 2,
                "deadline": today + timedelta(days=30),
                "required_skills": ["React", "TypeScript", "Tailwind CSS", "Git"],
                "contact_info": "careers@techcorp.example.com",
            },
            {
                "poster": providers["demo_provider1@example.com"],
                "title": "Junior Python & Django Backend Developer",
                "description": "We are seeking a part-time Python developer to maintain and expand REST API endpoints for our core analytics platform. Ideal for computer science students with strong SQL and Django fundamentals.",
                "category": Opportunity.Category.PART_TIME,
                "work_mode": Opportunity.WorkMode.HYBRID,
                "city": "Mumbai",
                "pay_type": Opportunity.PayType.MONTHLY,
                "pay_amount": Decimal("25000.00"),
                "vacancies": 1,
                "deadline": today + timedelta(days=21),
                "required_skills": ["Python", "Django", "PostgreSQL", "REST API"],
                "contact_info": "jobs@techcorp.example.com",
            },
            {
                "poster": providers["demo_provider2@example.com"],
                "title": "Full-Stack Software Engineer (Early Hire)",
                "description": "InnovateLab AI is hiring early-career full-stack developers. Build web applications powered by generative AI models. High-impact role with competitive equity and growth.",
                "category": Opportunity.Category.STARTUP_HIRING,
                "work_mode": Opportunity.WorkMode.ONSITE,
                "city": "Bangalore",
                "pay_type": Opportunity.PayType.MONTHLY,
                "pay_amount": Decimal("45000.00"),
                "vacancies": 3,
                "deadline": today + timedelta(days=45),
                "required_skills": ["Next.js", "Node.js", "Python", "MongoDB"],
                "contact_info": "founding-team@innovatelab.example.com",
            },
            {
                "poster": providers["demo_provider2@example.com"],
                "title": "UI/UX Product Designer",
                "description": "Create intuitive wireframes, visual design specs, and interactive prototypes for our AI SaaS products. Experience with Figma and user research preferred.",
                "category": Opportunity.Category.PART_TIME,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "city": "Chennai",
                "pay_type": Opportunity.PayType.MONTHLY,
                "pay_amount": Decimal("20000.00"),
                "vacancies": 1,
                "deadline": today + timedelta(days=14),
                "required_skills": ["Figma", "UI/UX", "User Research", "Wireframing"],
                "contact_info": "design@innovatelab.example.com",
            },
            {
                "poster": providers["demo_provider3@example.com"],
                "title": "Social Media & Content Marketing Specialist",
                "description": "Manage Instagram, LinkedIn, and TikTok channels for Artisan Coffee Roasters. Capture short-form video reels, design promotional graphics, and engage with community followers.",
                "category": Opportunity.Category.FREELANCE,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "city": "Delhi",
                "pay_type": Opportunity.PayType.HOURLY,
                "pay_amount": Decimal("500.00"),
                "vacancies": 2,
                "deadline": today + timedelta(days=18),
                "required_skills": ["Social Media", "Content Creation", "Canva", "Video Editing"],
                "contact_info": "marketing@artisancoffee.example.com",
            },
            {
                "poster": providers["demo_provider3@example.com"],
                "title": "Weekend Barista & Event Assistant",
                "description": "Join our cafe team on weekends for specialty coffee preparation and customer service during hosted weekend workshops and live acoustic sessions.",
                "category": Opportunity.Category.EVENT_BASED,
                "work_mode": Opportunity.WorkMode.ONSITE,
                "city": "Delhi",
                "pay_type": Opportunity.PayType.HOURLY,
                "pay_amount": Decimal("400.00"),
                "vacancies": 4,
                "deadline": today + timedelta(days=10),
                "required_skills": ["Customer Service", "Barista Experience", "Communication"],
                "contact_info": "manager@artisancoffee.example.com",
            },
            {
                "poster": providers["demo_provider4@example.com"],
                "title": "High School Mathematics & Physics Tutor",
                "description": "Provide online tutoring sessions for 10th-12th grade students in Algebra, Calculus, and Physics. Flexible scheduling around university classes.",
                "category": Opportunity.Category.TUTORING,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "city": "Pune",
                "pay_type": Opportunity.PayType.HOURLY,
                "pay_amount": Decimal("600.00"),
                "vacancies": 2,
                "deadline": today + timedelta(days=25),
                "required_skills": ["Mathematics", "Physics", "Teaching", "Communication"],
                "contact_info": "tutoring@ecogreen.example.com",
            },
            {
                "poster": providers["demo_provider4@example.com"],
                "title": "Urban Reforestation Volunteer Coordinator",
                "description": "Help organize weekend tree plantation drives and community sustainability workshops. Great opportunity for students passionate about climate action and environmental leadership.",
                "category": Opportunity.Category.VOLUNTEER,
                "work_mode": Opportunity.WorkMode.ONSITE,
                "city": "Hyderabad",
                "pay_type": Opportunity.PayType.UNPAID,
                "pay_amount": None,
                "vacancies": 5,
                "deadline": today + timedelta(days=35),
                "required_skills": ["Public Speaking", "Community Engagement", "Environmental Science"],
                "contact_info": "volunteer@ecogreen.example.com",
            },
        ]

        for opp_data in provider_opps_data:
            opp, created = Opportunity.objects.get_or_create(
                poster=opp_data["poster"],
                title=opp_data["title"],
                defaults={
                    "description": opp_data["description"],
                    "category": opp_data["category"],
                    "work_mode": opp_data["work_mode"],
                    "city": opp_data["city"],
                    "pay_type": opp_data["pay_type"],
                    "pay_amount": opp_data["pay_amount"],
                    "vacancies": opp_data["vacancies"],
                    "deadline": opp_data["deadline"],
                    "required_skills": opp_data["required_skills"],
                    "contact_info": opp_data["contact_info"],
                    "status": Opportunity.Status.OPEN,
                },
            )
            if created:
                self.stdout.write(f"  Created Provider Opportunity: '{opp.title}'")
            else:
                self.stdout.write(f"  Found Provider Opportunity: '{opp.title}'")

        # 4. Create Student Project Collaborations (category='project_collaboration', posted by STUDENTS)
        student_collabs_data = [
            {
                "poster": students["demo_student1@example.com"],
                "title": "Need a Flutter Developer for Final Year Capstone App",
                "description": "Looking for a student Flutter developer to collaborate on a cross-platform mobile app for campus resource sharing. We have wireframes ready and need help with state management and Firebase integration.",
                "category": Opportunity.Category.PROJECT_COLLABORATION,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "city": "Bangalore",
                "pay_type": Opportunity.PayType.UNPAID,
                "pay_amount": None,
                "vacancies": 2,
                "deadline": today + timedelta(days=40),
                "required_skills": ["Flutter", "Dart", "Firebase", "State Management"],
                "contact_info": "alex.rivera@example.com",
            },
            {
                "poster": students["demo_student2@example.com"],
                "title": "Looking for UI Designer & Pitch Lead for National Hackathon",
                "description": "Forming a 4-person team for an upcoming 36-hour national fintech hackathon. We need a UI/UX designer to craft Figma prototypes and help present the final pitch deck to judges.",
                "category": Opportunity.Category.PROJECT_COLLABORATION,
                "work_mode": Opportunity.WorkMode.HYBRID,
                "city": "Mumbai",
                "pay_type": Opportunity.PayType.UNPAID,
                "pay_amount": None,
                "vacancies": 1,
                "deadline": today + timedelta(days=12),
                "required_skills": ["Figma", "UI Design", "Pitching", "Prototyping"],
                "contact_info": "priya.sharma@example.com",
            },
            {
                "poster": students["demo_student3@example.com"],
                "title": "Co-founder & AI Engineer for Open-Source DevTools Project",
                "description": "Building an open-source LLM benchmarking framework for local model evaluation. Looking for a fellow student developer interested in PyTorch, Python, and open-source contribution.",
                "category": Opportunity.Category.PROJECT_COLLABORATION,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "city": "Bangalore",
                "pay_type": Opportunity.PayType.UNPAID,
                "pay_amount": None,
                "vacancies": 2,
                "deadline": today + timedelta(days=60),
                "required_skills": ["Python", "PyTorch", "LLMs", "Git"],
                "contact_info": "liam.chen@example.com",
            },
            {
                "poster": students["demo_student1@example.com"],
                "title": "Web3 & Smart Contract Developer for Student DAO",
                "description": "Collaborating on a decentralized governance tool for university student clubs. Seeking a developer familiar with Solidity or Web3.js to write and test smart contracts.",
                "category": Opportunity.Category.PROJECT_COLLABORATION,
                "work_mode": Opportunity.WorkMode.REMOTE,
                "city": "Delhi",
                "pay_type": Opportunity.PayType.UNPAID,
                "pay_amount": None,
                "vacancies": 1,
                "deadline": today + timedelta(days=28),
                "required_skills": ["Solidity", "Web3.js", "Ethereum", "Smart Contracts"],
                "contact_info": "alex.rivera@example.com",
            },
        ]

        for collab_data in student_collabs_data:
            opp, created = Opportunity.objects.get_or_create(
                poster=collab_data["poster"],
                title=collab_data["title"],
                defaults={
                    "description": collab_data["description"],
                    "category": collab_data["category"],
                    "work_mode": collab_data["work_mode"],
                    "city": collab_data["city"],
                    "pay_type": collab_data["pay_type"],
                    "pay_amount": collab_data["pay_amount"],
                    "vacancies": collab_data["vacancies"],
                    "deadline": collab_data["deadline"],
                    "required_skills": collab_data["required_skills"],
                    "contact_info": collab_data["contact_info"],
                    "status": Opportunity.Status.OPEN,
                },
            )
            if created:
                self.stdout.write(f"  Created Student Collaboration: '{opp.title}'")
            else:
                self.stdout.write(f"  Found Student Collaboration: '{opp.title}'")

        # 5. Create Sample Applications (students applying to provider opportunities)
        from apps.opportunities.models import Application

        # Fetch provider opportunities created above
        react_opp = Opportunity.objects.filter(title="Frontend React Developer Intern").first()
        python_opp = Opportunity.objects.filter(title="Junior Python & Django Backend Developer").first()
        design_opp = Opportunity.objects.filter(title="UI/UX Product Designer").first()
        marketing_opp = Opportunity.objects.filter(title="Social Media & Content Marketing Specialist").first()

        applications_data = [
            {
                "applicant": students["demo_student1@example.com"],
                "opportunity": react_opp,
                "cover_note": "I have built several React project dashboards and I am very excited about joining TechCorp Solutions for this summer internship!",
                "status": Application.Status.APPLIED,
            },
            {
                "applicant": students["demo_student2@example.com"],
                "opportunity": react_opp,
                "cover_note": "Experienced with TypeScript and Tailwind CSS. Looking forward to contributing to your enterprise frontend team.",
                "status": Application.Status.UNDER_REVIEW,
            },
            {
                "applicant": students["demo_student3@example.com"],
                "opportunity": python_opp,
                "cover_note": "Computer science major with strong Python background and building DRF backends. Available for 20 hrs/week.",
                "status": Application.Status.ACCEPTED,
            },
            {
                "applicant": students["demo_student1@example.com"],
                "opportunity": design_opp,
                "cover_note": "Check out my Figma portfolio link! I love crafting responsive UI systems and user flow diagrams.",
                "status": Application.Status.APPLIED,
            },
            {
                "applicant": students["demo_student2@example.com"],
                "opportunity": marketing_opp,
                "cover_note": "Managed student club Instagram page with 5k followers. Proficient in short-form video editing and Canva templates.",
                "status": Application.Status.UNDER_REVIEW,
            },
        ]

        for app_data in applications_data:
            if not app_data["opportunity"]:
                continue
            app, created = Application.objects.get_or_create(
                applicant=app_data["applicant"],
                opportunity=app_data["opportunity"],
                defaults={
                    "cover_note": app_data["cover_note"],
                    "status": app_data["status"],
                },
            )
            if created:
                self.stdout.write(f"  Created Application: {app.applicant.email} -> '{app.opportunity.title}' ({app.status})")
            else:
                self.stdout.write(f"  Found Application: {app.applicant.email} -> '{app.opportunity.title}' ({app.status})")

        self.stdout.write(self.style.SUCCESS("Successfully seeded NextGig demo data!"))

