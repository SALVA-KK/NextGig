from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Opportunity

User = get_user_model()


class OpportunityAPITests(APITestCase):
    """
    Test suite for the Opportunity model and CRUD endpoints.
    """

    def setUp(self):
        # Create verified user (Opportunity Poster)
        self.verified_user = User.objects.create_user(
            email="poster@example.com",
            password="Password123!",
            full_name="Verified Poster",
            is_verified=True,
        )

        # Create unverified user
        self.unverified_user = User.objects.create_user(
            email="unverified@example.com",
            password="Password123!",
            full_name="Unverified User",
            is_verified=False,
        )

        # Create another verified user (Non-owner)
        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="Password123!",
            full_name="Other User",
            is_verified=True,
        )

        # Create admin user
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            password="Password123!",
            full_name="Admin User",
            role=User.Role.ADMIN,
            is_staff=True,
            is_verified=True,
        )

        # Create sample opportunity
        self.opportunity = Opportunity.objects.create(
            poster=self.verified_user,
            title="Frontend Developer Internship",
            description="Build cool React apps",
            category=Opportunity.Category.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.STIPEND,
            pay_amount=1500.00,
            city="Kochi",
            status=Opportunity.Status.OPEN,
            vacancies=2,
            deadline=date.today() + timedelta(days=30),
        )

        self.list_create_url = reverse("opportunities:opportunity-list-create")
        self.detail_url = reverse("opportunities:opportunity-detail", kwargs={"pk": self.opportunity.pk})

    def test_anonymous_user_can_view_list_and_detail(self):
        """Anonymous users can view opportunities list and detail."""
        response = self.client.get(self.list_create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

        detail_resp = self.client.get(self.detail_url)
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_resp.data["title"], "Frontend Developer Internship")

    def test_anonymous_user_cannot_create_opportunity(self):
        """Anonymous user cannot create an opportunity (401 Unauthorized)."""
        payload = {
            "title": "Backend Dev",
            "description": "Django REST Framework APIs",
            "category": "part_time",
            "work_mode": "remote",
            "pay_type": "hourly",
            "pay_amount": 25.00,
        }
        response = self.client.post(self.list_create_url, payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unverified_user_cannot_create_opportunity(self):
        """Unverified user cannot create an opportunity (403 Forbidden)."""
        self.client.force_authenticate(user=self.unverified_user)
        payload = {
            "title": "Backend Dev",
            "description": "Django REST Framework APIs",
            "category": "part_time",
            "work_mode": "remote",
            "pay_type": "hourly",
            "pay_amount": 25.00,
        }
        response = self.client.post(self.list_create_url, payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_verified_user_can_create_opportunity(self):
        """Verified user can successfully create an opportunity."""
        self.client.force_authenticate(user=self.verified_user)
        payload = {
            "title": "Full Stack Engineer",
            "description": "React and Django development",
            "category": "freelance",
            "work_mode": "remote",
            "pay_type": "monthly",
            "pay_amount": 3000.00,
            "required_skills": ["React", "Django", "PostgreSQL"],
            "vacancies": 3,
            "city": "Bangalore",
            "deadline": str(date.today() + timedelta(days=15)),
        }
        response = self.client.post(self.list_create_url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Full Stack Engineer")
        self.assertEqual(Opportunity.objects.count(), 2)

    def test_opportunity_validation_deadline_and_vacancies(self):
        """Validation errors returned for past deadlines or invalid vacancies."""
        self.client.force_authenticate(user=self.verified_user)

        # Past deadline
        payload_past = {
            "title": "Invalid Date Opp",
            "description": "Testing past deadline",
            "category": "part_time",
            "work_mode": "remote",
            "pay_type": "unpaid",
            "deadline": str(date.today() - timedelta(days=1)),
        }
        resp = self.client.post(self.list_create_url, payload_past)
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deadline", resp.data)

        # Invalid vacancies <= 0
        payload_vacancies = {
            "title": "Zero Vacancy Opp",
            "description": "Testing zero vacancies",
            "category": "part_time",
            "work_mode": "remote",
            "pay_type": "unpaid",
            "vacancies": 0,
        }
        resp_vac = self.client.post(self.list_create_url, payload_vacancies)
        self.assertEqual(resp_vac.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("vacancies", resp_vac.data)

    def test_owner_and_admin_can_update_and_delete(self):
        """Owner can update and delete their own opportunity."""
        self.client.force_authenticate(user=self.verified_user)
        update_payload = {
            "title": "Updated Title",
            "description": "Updated description",
            "category": "internship",
            "work_mode": "remote",
            "pay_type": "stipend",
            "pay_amount": 2000.00,
        }
        resp = self.client.put(self.detail_url, update_payload)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["title"], "Updated Title")

        # Admin can delete
        self.client.force_authenticate(user=self.admin_user)
        del_resp = self.client.delete(self.detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Opportunity.objects.count(), 0)

    def test_non_owner_cannot_update_or_delete(self):
        """Non-owner cannot update or delete someone else's opportunity (403 Forbidden)."""
        self.client.force_authenticate(user=self.other_user)
        update_payload = {
            "title": "Hacked Title",
            "description": "Hacked description",
            "category": "internship",
            "work_mode": "remote",
            "pay_type": "stipend",
        }
        resp = self.client.put(self.detail_url, update_payload)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

        del_resp = self.client.delete(self.detail_url)
        self.assertEqual(del_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_query_param_filtering(self):
        """Test filtering list view by category, work_mode, city, and status."""
        Opportunity.objects.create(
            poster=self.verified_user,
            title="Onsite Tutor",
            description="Teach math in person",
            category=Opportunity.Category.TUTORING,
            work_mode=Opportunity.WorkMode.ONSITE,
            pay_type=Opportunity.PayType.HOURLY,
            city="Chennai",
            status=Opportunity.Status.OPEN,
        )

        # Filter by category
        resp_cat = self.client.get(f"{self.list_create_url}?category=tutoring")
        self.assertEqual(resp_cat.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_cat.data["results"]), 1)
        self.assertEqual(resp_cat.data["results"][0]["title"], "Onsite Tutor")

        # Filter by city
        resp_city = self.client.get(f"{self.list_create_url}?city=Kochi")
        self.assertEqual(resp_city.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_city.data["results"]), 1)
        self.assertEqual(resp_city.data["results"][0]["title"], "Frontend Developer Internship")

        # Filter by work_mode
        resp_mode = self.client.get(f"{self.list_create_url}?work_mode=onsite")
        self.assertEqual(resp_mode.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_mode.data["results"]), 1)
        self.assertEqual(resp_mode.data["results"][0]["title"], "Onsite Tutor")

    def test_list_view_excludes_draft_and_closed_by_default(self):
        """List view defaults to status='open', excluding draft and closed opportunities."""
        Opportunity.objects.create(
            poster=self.verified_user,
            title="Closed Opp",
            description="Finished job",
            category=Opportunity.Category.FREELANCE,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.HOURLY,
            status=Opportunity.Status.CLOSED,
        )
        Opportunity.objects.create(
            poster=self.verified_user,
            title="Draft Opp",
            description="Drafting job",
            category=Opportunity.Category.FREELANCE,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.HOURLY,
            status=Opportunity.Status.DRAFT,
        )
        resp = self.client.get(self.list_create_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["title"], "Frontend Developer Internship")

        # Passing status=all returns all 3
        resp_all = self.client.get(f"{self.list_create_url}?status=all")
        self.assertEqual(resp_all.data["count"], 3)

