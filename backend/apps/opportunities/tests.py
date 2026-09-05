from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Application, Opportunity, SavedOpportunity
from .tasks import (
    close_expired_opportunities,
    notify_applicant_of_status_change,
    notify_poster_of_new_application,
)

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


class SavedOpportunityTests(APITestCase):
    """
    Test suite for Saved Opportunities (bookmarking) feature.
    """

    def setUp(self):
        self.verified_user = User.objects.create_user(
            email="saver@example.com",
            password="Password123!",
            full_name="Verified Saver",
            is_verified=True,
        )

        self.unverified_user = User.objects.create_user(
            email="unverifiedsaver@example.com",
            password="Password123!",
            full_name="Unverified Saver",
            is_verified=False,
        )

        self.other_user = User.objects.create_user(
            email="othersaver@example.com",
            password="Password123!",
            full_name="Other Saver",
            is_verified=True,
        )

        self.opportunity1 = Opportunity.objects.create(
            poster=self.verified_user,
            title="Python Backend Gig",
            description="Build Django REST APIs",
            category=Opportunity.Category.FREELANCE,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.HOURLY,
            pay_amount=50.00,
            status=Opportunity.Status.OPEN,
        )

        self.opportunity2 = Opportunity.objects.create(
            poster=self.verified_user,
            title="UI/UX Designer",
            description="Design Figma prototypes",
            category=Opportunity.Category.PROJECT_COLLABORATION,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.STIPEND,
            pay_amount=800.00,
            status=Opportunity.Status.OPEN,
        )

        self.save_url1 = reverse("opportunities:opportunity-save", kwargs={"pk": self.opportunity1.pk})
        self.save_url2 = reverse("opportunities:opportunity-save", kwargs={"pk": self.opportunity2.pk})
        self.saved_list_url = "/api/saved-opportunities/"

    def test_verified_user_can_save_opportunity(self):
        """Verified user can save an opportunity (returns 201 Created)."""
        self.client.force_authenticate(user=self.verified_user)
        response = self.client.post(self.save_url1)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["message"], "Opportunity saved successfully.")
        self.assertTrue(SavedOpportunity.objects.filter(user=self.verified_user, opportunity=self.opportunity1).exists())

    def test_saving_same_opportunity_twice_is_idempotent(self):
        """Saving the same opportunity twice is idempotent (returns 200 OK, no duplicate database record)."""
        self.client.force_authenticate(user=self.verified_user)
        res1 = self.client.post(self.save_url1)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(self.save_url1)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data["message"], "Opportunity is already saved.")
        self.assertEqual(SavedOpportunity.objects.filter(user=self.verified_user, opportunity=self.opportunity1).count(), 1)

    def test_unverified_user_cannot_save_opportunity(self):
        """Unverified user gets 403 Forbidden when trying to save an opportunity."""
        self.client.force_authenticate(user=self.unverified_user)
        response = self.client.post(self.save_url1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(SavedOpportunity.objects.count(), 0)

    def test_user_can_unsave_saved_opportunity(self):
        """User can unsave a previously saved opportunity (returns 200 OK)."""
        self.client.force_authenticate(user=self.verified_user)
        self.client.post(self.save_url1)
        self.assertEqual(SavedOpportunity.objects.count(), 1)

        unsave_resp = self.client.delete(self.save_url1)
        self.assertEqual(unsave_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(unsave_resp.data["message"], "Opportunity unsaved successfully.")
        self.assertEqual(SavedOpportunity.objects.count(), 0)

    def test_unsaving_never_saved_opportunity_returns_404(self):
        """Unsaving an opportunity that was never saved returns 404 Not Found."""
        self.client.force_authenticate(user=self.verified_user)
        response = self.client.delete(self.save_url1)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_saved_opportunities_list_user_isolation(self):
        """GET /api/saved-opportunities/ returns only the authenticated user's own saved opportunities."""
        # Save opp1 for verified_user and opp2 for other_user
        SavedOpportunity.objects.create(user=self.verified_user, opportunity=self.opportunity1)
        SavedOpportunity.objects.create(user=self.other_user, opportunity=self.opportunity2)

        # Authenticate as verified_user
        self.client.force_authenticate(user=self.verified_user)
        response = self.client.get(self.saved_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["opportunity"]["title"], "Python Backend Gig")

    def test_deleting_opportunity_cascades_saved_opportunity(self):
        """Deleting an Opportunity automatically deletes all SavedOpportunity records pointing to it."""
        SavedOpportunity.objects.create(user=self.verified_user, opportunity=self.opportunity1)
        SavedOpportunity.objects.create(user=self.other_user, opportunity=self.opportunity1)
        self.assertEqual(SavedOpportunity.objects.count(), 2)

        self.opportunity1.delete()
        self.assertEqual(SavedOpportunity.objects.count(), 0)


class ApplicationTests(APITestCase):
    """
    Test suite for Applications feature, status transitions, permissions, and Celery notifications.
    """

    def setUp(self):
        self.poster = User.objects.create_user(
            email="poster_app@example.com",
            password="Password123!",
            full_name="Opportunity Poster",
            role="provider",
            is_verified=True,
        )

        self.student = User.objects.create_user(
            email="student_app@example.com",
            password="Password123!",
            full_name="Student Applicant",
            role="student",
            is_verified=True,
        )

        self.unverified_student = User.objects.create_user(
            email="unverified_student@example.com",
            password="Password123!",
            full_name="Unverified Student",
            role="student",
            is_verified=False,
        )

        self.provider = User.objects.create_user(
            email="provider_app@example.com",
            password="Password123!",
            full_name="Other Provider",
            role="provider",
            is_verified=True,
        )

        self.other_student = User.objects.create_user(
            email="other_student@example.com",
            password="Password123!",
            full_name="Other Student",
            role="student",
            is_verified=True,
        )

        self.open_opp = Opportunity.objects.create(
            poster=self.poster,
            title="Django Backend Intern",
            description="Build APIs with Django REST framework",
            category=Opportunity.Category.INTERNSHIP,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.STIPEND,
            status=Opportunity.Status.OPEN,
            deadline=date.today() + timedelta(days=10),
        )

        self.closed_opp = Opportunity.objects.create(
            poster=self.poster,
            title="Closed Gig",
            description="Expired job",
            category=Opportunity.Category.FREELANCE,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.HOURLY,
            status=Opportunity.Status.CLOSED,
        )

        self.draft_opp = Opportunity.objects.create(
            poster=self.poster,
            title="Draft Gig",
            description="Work in progress job",
            category=Opportunity.Category.FREELANCE,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.HOURLY,
            status=Opportunity.Status.DRAFT,
        )

        self.apply_url = reverse("opportunities:opportunity-apply", kwargs={"pk": self.open_opp.pk})
        self.my_apps_url = "/api/applications/"

    def test_student_can_apply_to_open_opportunity(self):
        """Verified student can apply to an open opportunity."""
        self.client.force_authenticate(user=self.student)
        response = self.client.post(self.apply_url, {"cover_note": "Interested in Django!"})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "applied")
        self.assertEqual(response.data["cover_note"], "Interested in Django!")
        self.assertTrue(Application.objects.filter(applicant=self.student, opportunity=self.open_opp).exists())

    def test_cannot_apply_twice_clean_400(self):
        """Applying twice returns clean 400 Bad Request error (not 500 server error)."""
        self.client.force_authenticate(user=self.student)
        res1 = self.client.post(self.apply_url, {"cover_note": "First note"})
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(self.apply_url, {"cover_note": "Second note"})
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already applied", res2.data["detail"].lower())

    def test_student_cannot_apply_to_own_posted_opportunity(self):
        """A student who posted a project_collaboration opportunity cannot apply to it themselves (400 Bad Request)."""
        proj_collab_opp = Opportunity.objects.create(
            poster=self.student,
            title="Open Source AI Tool",
            description="Collaborate on LLM tooling",
            category=Opportunity.Category.PROJECT_COLLABORATION,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.UNPAID,
            status=Opportunity.Status.OPEN,
        )
        self.client.force_authenticate(user=self.student)
        apply_own_url = reverse("opportunities:opportunity-apply", kwargs={"pk": proj_collab_opp.pk})
        response = self.client.post(apply_own_url, {"cover_note": "Applying to my own project"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cannot apply to your own", response.data["detail"].lower())

    def test_cannot_apply_to_closed_or_draft_opportunity(self):
        """Cannot apply to closed or draft opportunities."""
        self.client.force_authenticate(user=self.student)

        closed_url = reverse("opportunities:opportunity-apply", kwargs={"pk": self.closed_opp.pk})
        res_closed = self.client.post(closed_url, {"cover_note": "Try closed"})
        self.assertEqual(res_closed.status_code, status.HTTP_400_BAD_REQUEST)

        draft_url = reverse("opportunities:opportunity-apply", kwargs={"pk": self.draft_opp.pk})
        res_draft = self.client.post(draft_url, {"cover_note": "Try draft"})
        self.assertEqual(res_draft.status_code, status.HTTP_400_BAD_REQUEST)

    def test_provider_or_unverified_student_cannot_apply(self):
        """Provider or unverified student gets 403 Forbidden when trying to apply."""
        self.client.force_authenticate(user=self.provider)
        res_provider = self.client.post(self.apply_url, {"cover_note": "Provider apply"})
        self.assertEqual(res_provider.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.unverified_student)
        res_unverified = self.client.post(self.apply_url, {"cover_note": "Unverified apply"})
        self.assertEqual(res_unverified.status_code, status.HTTP_403_FORBIDDEN)

    def test_poster_can_view_applicants(self):
        """Poster can view applicants for their own opportunity."""
        Application.objects.create(applicant=self.student, opportunity=self.open_opp, cover_note="Note 1")
        Application.objects.create(applicant=self.other_student, opportunity=self.open_opp, cover_note="Note 2")

        applicants_url = reverse("opportunities:opportunity-applicants", kwargs={"pk": self.open_opp.pk})
        self.client.force_authenticate(user=self.poster)
        response = self.client.get(applicants_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_non_poster_cannot_view_applicants(self):
        """Non-poster receives 403 Forbidden when attempting to view opportunity applicants."""
        applicants_url = reverse("opportunities:opportunity-applicants", kwargs={"pk": self.open_opp.pk})
        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(applicants_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_poster_can_update_status_accepted_rejected(self):
        """Poster can update applicant status to under_review, accepted, or rejected."""
        app = Application.objects.create(applicant=self.student, opportunity=self.open_opp)
        status_url = f"/api/applications/{app.pk}/status/"

        self.client.force_authenticate(user=self.poster)
        res_review = self.client.patch(status_url, {"status": "under_review"})
        self.assertEqual(res_review.status_code, status.HTTP_200_OK)
        self.assertEqual(res_review.data["status"], "under_review")

        res_accept = self.client.patch(status_url, {"status": "accepted"})
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)
        self.assertEqual(res_accept.data["status"], "accepted")

    def test_poster_cannot_set_applied_or_withdrawn_status(self):
        """Poster cannot set status back to 'applied' or 'withdrawn'."""
        app = Application.objects.create(applicant=self.student, opportunity=self.open_opp)
        status_url = f"/api/applications/{app.pk}/status/"

        self.client.force_authenticate(user=self.poster)
        res_applied = self.client.patch(status_url, {"status": "applied"})
        self.assertEqual(res_applied.status_code, status.HTTP_400_BAD_REQUEST)

        res_withdrawn = self.client.patch(status_url, {"status": "withdrawn"})
        self.assertEqual(res_withdrawn.status_code, status.HTTP_400_BAD_REQUEST)

    def test_applicant_can_withdraw_pending_application(self):
        """Applicant can withdraw their own pending application (status='applied' or 'under_review')."""
        app = Application.objects.create(applicant=self.student, opportunity=self.open_opp, status="applied")
        status_url = f"/api/applications/{app.pk}/status/"

        self.client.force_authenticate(user=self.student)
        response = self.client.patch(status_url, {"status": "withdrawn"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "withdrawn")

    def test_applicant_cannot_withdraw_accepted_or_rejected_application(self):
        """Applicant cannot withdraw an application that has already been accepted or rejected."""
        app_accepted = Application.objects.create(applicant=self.student, opportunity=self.open_opp, status="accepted")
        status_url = f"/api/applications/{app_accepted.pk}/status/"

        self.client.force_authenticate(user=self.student)
        response = self.client.patch(status_url, {"status": "withdrawn"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_applicant_non_poster_gets_403_on_status_update(self):
        """Non-applicant and non-poster user receives 403 Forbidden on status update."""
        app = Application.objects.create(applicant=self.student, opportunity=self.open_opp)
        status_url = f"/api/applications/{app.pk}/status/"

        self.client.force_authenticate(user=self.other_student)
        response = self.client.patch(status_url, {"status": "accepted"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_celery_application_notification_tasks(self):
        """Test Celery notification tasks directly."""
        app = Application.objects.create(
            applicant=self.student,
            opportunity=self.open_opp,
            cover_note="Test note",
        )
        res_poster = notify_poster_of_new_application(app.pk)
        self.assertTrue(res_poster)

        res_applicant = notify_applicant_of_status_change(app.pk)
        self.assertTrue(res_applicant)

    def test_close_expired_opportunities_periodic_task(self):
        """Celery Beat periodic task closes open opportunities past deadline while leaving future deadlines untouched."""
        past_opp = Opportunity.objects.create(
            poster=self.poster,
            title="Past Opp",
            description="Expired",
            category=Opportunity.Category.FREELANCE,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.HOURLY,
            status=Opportunity.Status.OPEN,
            deadline=date.today() - timedelta(days=2),
        )

        future_opp = Opportunity.objects.create(
            poster=self.poster,
            title="Future Opp",
            description="Valid",
            category=Opportunity.Category.FREELANCE,
            work_mode=Opportunity.WorkMode.REMOTE,
            pay_type=Opportunity.PayType.HOURLY,
            status=Opportunity.Status.OPEN,
            deadline=date.today() + timedelta(days=5),
        )

        closed_count = close_expired_opportunities()
        self.assertEqual(closed_count, 1)

        past_opp.refresh_from_db()
        future_opp.refresh_from_db()

        self.assertEqual(past_opp.status, Opportunity.Status.CLOSED)
        self.assertEqual(future_opp.status, Opportunity.Status.OPEN)


