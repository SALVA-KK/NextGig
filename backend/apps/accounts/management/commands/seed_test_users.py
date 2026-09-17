from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.accounts.models import StudentProfile, ProviderProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Seed/populate test user profiles (student and provider) idempotently for development testing."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Seeding test user profiles..."))

        # 1. Student User Profile
        student = User.objects.filter(role=User.Role.STUDENT).first()
        if not student:
            student, created = User.objects.get_or_create(
                email="test_student@example.com",
                defaults={
                    "full_name": "Alex Johnson",
                    "role": User.Role.STUDENT,
                    "is_verified": True,
                }
            )
            if created:
                student.set_password("password123")
                student.save()

        sp, sp_created = StudentProfile.objects.get_or_create(
            user=student,
            defaults={
                "bio": "Passionate Full-Stack Student Developer building React and Django applications.",
                "skills": ["React", "Python", "Django", "TailwindCSS"],
                "languages": ["English", "Spanish"],
                "portfolio_url": "https://alexjohnson.dev",
                "city": "San Francisco, CA",
                "qualification_type": "degree",
                "qualification_name": "B.S. Computer Science",
                "institution": "Stanford University",
            }
        )
        if not sp_created:
            sp.bio = "Passionate Full-Stack Student Developer building React and Django applications."
            sp.skills = ["React", "Python", "Django", "TailwindCSS"]
            sp.languages = ["English", "Spanish"]
            sp.portfolio_url = "https://alexjohnson.dev"
            sp.city = "San Francisco, CA"
            sp.qualification_type = "degree"
            sp.qualification_name = "B.S. Computer Science"
            sp.institution = "Stanford University"
            sp.save()

        self.stdout.write(self.style.SUCCESS(f"Updated student profile: {student.email}"))

        # 2. Provider User Profile
        provider = User.objects.filter(role=User.Role.PROVIDER).first()
        if not provider:
            provider, created = User.objects.get_or_create(
                email="test_provider@example.com",
                defaults={
                    "full_name": "Sarah Connor",
                    "role": User.Role.PROVIDER,
                    "is_verified": True,
                }
            )
            if created:
                provider.set_password("password123")
                provider.save()

        pp, pp_created = ProviderProfile.objects.get_or_create(
            user=provider,
            defaults={
                "description": "Leading tech innovator building next-generation web platforms.",
                "organization_name": "Acme Tech Solutions",
                "organization_type": ProviderProfile.OrganizationType.COMPANY,
                "contact_person": "Sarah Connor (Head of Talent)",
                "address": "500 Market St, Suite 300",
                "city": "San Francisco, CA",
                "website": "https://acmetech.com",
            }
        )
        if not pp_created:
            pp.description = "Leading tech innovator building next-generation web platforms."
            pp.organization_name = "Acme Tech Solutions"
            pp.organization_type = ProviderProfile.OrganizationType.COMPANY
            pp.contact_person = "Sarah Connor (Head of Talent)"
            pp.address = "500 Market St, Suite 300"
            pp.city = "San Francisco, CA"
            pp.website = "https://acmetech.com"
            pp.save()

        self.stdout.write(self.style.SUCCESS(f"Updated provider profile: {provider.email}"))
