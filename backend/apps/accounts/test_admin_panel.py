from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import AdminActionLog, CustomUser, ProviderProfile
from apps.opportunities.models import Opportunity


class AdminPanelAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Admin user
        self.admin = CustomUser.objects.create_user(
            email="admin_test@example.com",
            password="Password123!",
            full_name="Admin Test",
            role=CustomUser.Role.ADMIN,
            is_verified=True,
        )

        # Provider user & profile (unverified)
        self.provider_user = CustomUser.objects.create_user(
            email="provider_test@example.com",
            password="Password123!",
            full_name="Provider Test",
            role=CustomUser.Role.PROVIDER,
            is_verified=False,
        )
        self.provider_profile = ProviderProfile.objects.create(
            user=self.provider_user,
            organization_name="Acme Corp",
            organization_type="company",
            is_verified=False,
        )

        # Student user
        self.student_user = CustomUser.objects.create_user(
            email="student_test@example.com",
            password="Password123!",
            full_name="Student Test",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )

        # Sample Opportunity
        self.opportunity = Opportunity.objects.create(
            poster=self.provider_user,
            title="Sample Admin Moderation Job",
            description="Testing opportunity moderation.",
            category="internship",
            work_mode="remote",
            status="open",
        )

    # -------------------------------------------------------------------------
    # 1. Non-Admin Permission Checks (403 / 401)
    # -------------------------------------------------------------------------
    def test_non_admin_users_denied_access(self):
        """Confirm student and provider accounts get 403 Forbidden on all admin endpoints."""
        endpoints = [
            ("get", "/api/admin/providers/pending/"),
            ("patch", f"/api/admin/providers/{self.provider_profile.id}/verify/"),
            ("get", "/api/admin/users/"),
            ("patch", f"/api/admin/users/{self.student_user.id}/toggle-active/"),
            ("get", "/api/admin/opportunities/"),
            ("patch", f"/api/admin/opportunities/{self.opportunity.id}/force-close/"),
            ("delete", f"/api/admin/opportunities/{self.opportunity.id}/"),
        ]

        for role_user in [self.student_user, self.provider_user]:
            self.client.force_authenticate(user=role_user)
            for method, url in endpoints:
                func = getattr(self.client, method)
                response = func(url)
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                    f"User {role_user.email} was not blocked on {method.upper()} {url}",
                )

    # -------------------------------------------------------------------------
    # 2. Provider Verification Tests
    # -------------------------------------------------------------------------
    def test_admin_can_list_pending_providers(self):
        """Admin can list unverified provider profiles."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/providers/pending/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["organization_name"], "Acme Corp")
        self.assertEqual(results[0]["owner_email"], "provider_test@example.com")

    def test_admin_can_verify_provider(self):
        """Admin can set is_verified=True on a provider profile."""
        self.client.force_authenticate(user=self.admin)
        url = f"/api/admin/providers/{self.provider_profile.id}/verify/"
        response = self.client.patch(url, {"is_verified": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.provider_profile.refresh_from_db()
        self.provider_user.refresh_from_db()
        self.assertTrue(self.provider_profile.is_verified)
        self.assertTrue(self.provider_user.is_verified)

    def test_admin_verifying_provider_creates_notification_without_duplicates(self):
        """Verifying a provider sends exactly 1 provider_verified notification; re-verifying sends no duplicate."""
        from apps.notifications.models import Notification

        self.client.force_authenticate(user=self.admin)
        url = f"/api/admin/providers/{self.provider_profile.id}/verify/"

        # First verification (False -> True)
        res1 = self.client.patch(url, {"is_verified": True}, format="json")
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        notifs = Notification.objects.filter(
            recipient=self.provider_user,
            notification_type=Notification.NotificationType.PROVIDER_VERIFIED,
        )
        self.assertEqual(notifs.count(), 1)
        self.assertIn("You're Verified!", notifs.first().title)

        # Second verification (True -> True, no state change)
        res2 = self.client.patch(url, {"is_verified": True}, format="json")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Count MUST remain 1 (no duplicate notification created)
        self.assertEqual(notifs.count(), 1)

    # -------------------------------------------------------------------------
    # 3. User Management Tests
    # -------------------------------------------------------------------------
    def test_admin_can_list_users_with_search_and_role_filter(self):
        """Admin can fetch paginated user list with role and search filters."""
        self.client.force_authenticate(user=self.admin)

        # List all
        res_all = self.client.get("/api/admin/users/")
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)

        # Filter by role=student
        res_student = self.client.get("/api/admin/users/?role=student")
        self.assertEqual(res_student.status_code, status.HTTP_200_OK)
        results_student = res_student.data.get("results", res_student.data)
        self.assertEqual(len(results_student), 1)
        self.assertEqual(results_student[0]["email"], "student_test@example.com")

        # Search by email
        res_search = self.client.get("/api/admin/users/?search=Acme")
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)

    def test_admin_can_toggle_user_active_status(self):
        """Admin can activate/deactivate another user."""
        self.client.force_authenticate(user=self.admin)
        url = f"/api/admin/users/{self.student_user.id}/toggle-active/"

        # Deactivate
        res_deact = self.client.patch(url)
        self.assertEqual(res_deact.status_code, status.HTTP_200_OK)
        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)

        # Re-activate
        res_act = self.client.patch(url)
        self.assertEqual(res_act.status_code, status.HTTP_200_OK)
        self.student_user.refresh_from_db()
        self.assertTrue(self.student_user.is_active)

    def test_admin_cannot_deactivate_own_account(self):
        """Confirm admin gets 400 Bad Request when attempting to deactivate own account."""
        self.client.force_authenticate(user=self.admin)
        url = f"/api/admin/users/{self.admin.id}/toggle-active/"
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("You cannot deactivate your own admin account.", response.data.get("detail", ""))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_admin_cannot_deactivate_other_admin_unless_superuser(self):
        """Confirm non-superuser admin cannot deactivate another admin, but superuser can."""
        other_admin = CustomUser.objects.create_user(
            email="admin2_test@example.com",
            password="Password123!",
            full_name="Other Admin",
            role=CustomUser.Role.ADMIN,
            is_verified=True,
        )
        # 1. Non-superuser Admin A tries to deactivate Admin B -> 400 Bad Request
        self.client.force_authenticate(user=self.admin) # is_superuser=False
        url = f"/api/admin/users/{other_admin.id}/toggle-active/"
        res1 = self.client.patch(url)
        self.assertEqual(res1.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot deactivate another admin account.", res1.data.get("detail", ""))

        # 2. Superuser Admin tries to deactivate Admin B -> 200 OK
        superuser = CustomUser.objects.create_superuser(
            email="superuser_test@example.com",
            password="Password123!",
            full_name="Super Admin",
            role=CustomUser.Role.ADMIN,
            is_verified=True,
        )
        self.client.force_authenticate(user=superuser)
        res2 = self.client.patch(url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        other_admin.refresh_from_db()
        self.assertFalse(other_admin.is_active)

    # -------------------------------------------------------------------------
    # 4. Opportunity Moderation Tests
    # -------------------------------------------------------------------------
    def test_admin_can_list_all_opportunities(self):
        """Admin can list all opportunities across open/closed/draft statuses."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/opportunities/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Sample Admin Moderation Job")

    def test_admin_can_force_close_opportunity(self):
        """Admin can force-close any opportunity."""
        self.client.force_authenticate(user=self.admin)
        url = f"/api/admin/opportunities/{self.opportunity.id}/force-close/"
        response = self.client.patch(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.opportunity.refresh_from_db()
        self.assertEqual(self.opportunity.status, "closed")

    def test_admin_can_delete_opportunity(self):
        """Admin can delete any opportunity listing."""
        self.client.force_authenticate(user=self.admin)
        url = f"/api/admin/opportunities/{self.opportunity.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Opportunity.objects.filter(id=self.opportunity.id).exists())

    # -------------------------------------------------------------------------
    # 5. Audit Log & Throttling Tests
    # -------------------------------------------------------------------------
    def test_admin_actions_create_audit_logs(self):
        """Confirm an AdminActionLog record is created for each of the 4 destructive actions."""
        self.client.force_authenticate(user=self.admin)

        # 1. Verify Provider
        self.client.patch(f"/api/admin/providers/{self.provider_profile.id}/verify/", {"is_verified": True}, format="json")
        log1 = AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.PROVIDER_VERIFIED).first()
        self.assertIsNotNone(log1)
        self.assertEqual(log1.admin, self.admin)
        self.assertIn("Acme Corp", log1.target_description)

        # 2. Toggle User Active
        self.client.patch(f"/api/admin/users/{self.student_user.id}/toggle-active/")
        log2 = AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.USER_DEACTIVATED).first()
        self.assertIsNotNone(log2)
        self.assertEqual(log2.admin, self.admin)
        self.assertIn("student_test@example.com", log2.target_description)

        # 3. Force Close Opportunity
        self.client.patch(f"/api/admin/opportunities/{self.opportunity.id}/force-close/")
        log3 = AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.OPPORTUNITY_FORCE_CLOSED).first()
        self.assertIsNotNone(log3)
        self.assertEqual(log3.admin, self.admin)
        self.assertIn("Sample Admin Moderation Job", log3.target_description)

        # 4. Delete Opportunity
        self.client.delete(f"/api/admin/opportunities/{self.opportunity.id}/")
        log4 = AdminActionLog.objects.filter(action_type=AdminActionLog.ActionType.OPPORTUNITY_DELETED).first()
        self.assertIsNotNone(log4)
        self.assertEqual(log4.admin, self.admin)
        self.assertIn("Sample Admin Moderation Job", log4.target_description)

    def test_admin_audit_log_endpoint(self):
        """Admin can retrieve paginated audit log entries."""
        AdminActionLog.objects.create(
            admin=self.admin,
            action_type=AdminActionLog.ActionType.PROVIDER_VERIFIED,
            target_description="Provider #1: Acme Corp",
        )
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/admin/audit-log/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get("results", response.data)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["action_type"], "provider_verified")

    def test_admin_write_endpoint_throttling_scope(self):
        """Confirm throttle_scope='admin_write' is configured on admin write endpoints."""
        from apps.accounts.admin_views import AdminVerifyProviderView, AdminToggleUserActiveView
        from apps.opportunities.admin_views import AdminForceCloseOpportunityView, AdminDeleteOpportunityView

        for view_cls in [
            AdminVerifyProviderView,
            AdminToggleUserActiveView,
            AdminForceCloseOpportunityView,
            AdminDeleteOpportunityView,
        ]:
            self.assertEqual(getattr(view_cls, "throttle_scope", None), "admin_write")

