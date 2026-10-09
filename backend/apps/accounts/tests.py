from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import CustomUser, ProviderProfile, StudentProfile, Resume
from apps.accounts.utils import format_phone_for_msg91


@override_settings(ALLOWED_HOSTS=["*"])
class MSG91PhoneOTPTestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email="testuser@example.com",
            full_name="Test User",
            phone_number="+919207362507",
            password="TestPassword123!",
            is_verified=True,
        )

    def test_format_phone_for_msg91(self):
        self.assertEqual(format_phone_for_msg91("+919207362507"), "919207362507")
        self.assertEqual(format_phone_for_msg91("9207362507"), "919207362507")
        self.assertEqual(format_phone_for_msg91("919207362507"), "919207362507")
        self.assertEqual(format_phone_for_msg91(""), "")

    def test_verify_otp_invalid_code(self):
        response = self.client.post(
            "/api/accounts/phone-login/verify-otp/",
            data={"phone_number": "+919207362507", "otp": "000000"},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["detail"], "Invalid or expired OTP.")

    def test_firebase_id_token_phone_login_success(self):
        from unittest.mock import patch
        from django.core.cache import cache
        cache.clear()

        with patch("apps.accounts.views.verify_firebase_id_token", return_value="+919207362507"):
            response = self.client.post(
                "/api/accounts/phone-login/verify-otp/",
                data={"id_token": "mock_valid_firebase_id_token_123456"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            res_data = response.json()
            self.assertIn("access", res_data)
            self.assertIn("refresh", res_data)
            self.assertEqual(res_data["user"]["email"], "testuser@example.com")
            self.assertEqual(res_data["user"]["full_name"], "Test User")

    def test_firebase_login_unknown_phone_number_rejected(self):
        from unittest.mock import patch
        from django.core.cache import cache
        cache.clear()

        user_count_before = CustomUser.objects.count()

        # Firebase token is valid and returns +919999999999 (not registered in database)
        with patch("apps.accounts.views.verify_firebase_id_token", return_value="+919999999999"):
            response = self.client.post(
                "/api/accounts/phone-login/verify-otp/",
                data={"id_token": "mock_token_unregistered_phone"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json()["detail"],
                "No active user account found matching this verified phone number.",
            )
            # Confirm NO user was auto-created
            self.assertEqual(CustomUser.objects.count(), user_count_before)

    def test_firebase_login_invalid_token_rejected(self):
        from unittest.mock import patch
        from django.core.cache import cache
        cache.clear()

        # Firebase ID token verification fails (returns None)
        with patch("apps.accounts.views.verify_firebase_id_token", return_value=None):
            response = self.client.post(
                "/api/accounts/phone-login/verify-otp/",
                data={"id_token": "invalid_or_expired_token_abc"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json()["detail"],
                "Invalid or expired Firebase ID token.",
            )

    def test_firebase_phone_login_admin_mfa_required(self):
        from unittest.mock import patch
        from django.core.cache import cache
        from apps.accounts.models import AdminMFA
        cache.clear()

        # Create an Admin user with phone number +919876543210 and active AdminMFA
        admin_user = CustomUser.objects.create_user(
            email="phone_admin_mfa@example.com",
            full_name="Phone Admin MFA",
            password="StrongPassword123!",
            phone_number="+919876543210",
            role=CustomUser.Role.ADMIN,
            is_verified=True,
        )
        AdminMFA.objects.create(
            user=admin_user,
            totp_secret="JBSWY3DPEHPK3PXP",
            is_enabled=True,
        )

        with patch("apps.accounts.views.verify_firebase_id_token", return_value="+919876543210"):
            response = self.client.post(
                "/api/accounts/phone-login/verify-otp/",
                data={"id_token": "valid_firebase_id_token_for_admin"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            res_data = response.json()
            # Assert MFA challenge is returned instead of direct access/refresh tokens
            self.assertTrue(res_data.get("mfa_required"))
            self.assertIn("mfa_token", res_data)
            self.assertNotIn("access", res_data)
            self.assertNotIn("refresh", res_data)


@override_settings(ALLOWED_HOSTS=["*"])
class GoogleOAuthTestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.existing_user = CustomUser.objects.create_user(
            email="existing_google_user@example.com",
            full_name="Google User",
            password="StrongPassword123!",
            is_verified=True,
        )

    def test_google_login_existing_user_success(self):
        from unittest.mock import patch

        mock_payload = {
            "email": "existing_google_user@example.com",
            "name": "Google User",
            "google_id": "google_123456789",
        }

        with patch("apps.accounts.views.verify_google_id_token", return_value=mock_payload):
            response = self.client.post(
                "/api/accounts/google-login/",
                data={"id_token": "valid_mock_google_id_token"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            res_data = response.json()
            self.assertIn("access", res_data)
            self.assertIn("refresh", res_data)
            self.assertEqual(res_data["user"]["email"], "existing_google_user@example.com")
            self.assertEqual(res_data["user"]["full_name"], "Google User")

    def test_google_login_new_user_autoregistration(self):
        from unittest.mock import patch

        user_count_before = CustomUser.objects.count()
        mock_payload = {
            "email": "new_google_user@example.com",
            "name": "New Google User",
            "google_id": "google_987654321",
        }

        with patch("apps.accounts.views.verify_google_id_token", return_value=mock_payload):
            response = self.client.post(
                "/api/accounts/google-login/",
                data={"id_token": "valid_mock_google_id_token_new"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            res_data = response.json()
            self.assertIn("access", res_data)
            self.assertIn("refresh", res_data)
            self.assertEqual(res_data["user"]["email"], "new_google_user@example.com")
            self.assertEqual(res_data["user"]["full_name"], "New Google User")
            self.assertEqual(res_data["user"]["role"], "student")

            # Verify CustomUser database record
            self.assertEqual(CustomUser.objects.count(), user_count_before + 1)
            created_user = CustomUser.objects.get(email="new_google_user@example.com")
            self.assertTrue(created_user.is_verified)
            self.assertFalse(created_user.has_usable_password())

    def test_google_login_account_linking_no_duplicate(self):
        from unittest.mock import patch

        # User registered normally via email/password with mixed-case email
        password_user = CustomUser.objects.create_user(
            email="John@Example.com",
            full_name="John Doe",
            password="StrongPassword123!",
            is_verified=True,
        )

        user_count_before = CustomUser.objects.count()

        # User logs in via Google OAuth which returns lowercase "john@example.com"
        mock_payload = {
            "email": "john@example.com",
            "name": "John Doe",
            "google_id": "google_1020304050",
        }

        with patch("apps.accounts.views.verify_google_id_token", return_value=mock_payload):
            response = self.client.post(
                "/api/accounts/google-login/",
                data={"id_token": "valid_mock_google_id_token"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            res_data = response.json()
            self.assertIn("access", res_data)
            self.assertIn("refresh", res_data)
            self.assertEqual(res_data["user"]["id"], password_user.id)

            # Confirm NO duplicate account was created in the database
            self.assertEqual(CustomUser.objects.count(), user_count_before)

    def test_google_login_admin_mfa_required(self):
        from unittest.mock import patch
        from apps.accounts.models import AdminMFA

        # Create an Admin user with active AdminMFA
        admin_user = CustomUser.objects.create_user(
            email="admin_mfa_user@example.com",
            full_name="Admin MFA User",
            password="StrongPassword123!",
            role=CustomUser.Role.ADMIN,
            is_verified=True,
        )
        AdminMFA.objects.create(
            user=admin_user,
            totp_secret="JBSWY3DPEHPK3PXP",
            is_enabled=True,
        )

        mock_payload = {
            "email": "admin_mfa_user@example.com",
            "name": "Admin MFA User",
            "google_id": "google_admin_999",
        }

        with patch("apps.accounts.views.verify_google_id_token", return_value=mock_payload):
            response = self.client.post(
                "/api/accounts/google-login/",
                data={"id_token": "valid_admin_google_id_token"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            res_data = response.json()
            # Assert MFA challenge is returned instead of direct access/refresh tokens
            self.assertTrue(res_data.get("mfa_required"))
            self.assertIn("mfa_token", res_data)
            self.assertNotIn("access", res_data)
            self.assertNotIn("refresh", res_data)

    def test_google_login_invalid_token_rejected(self):
        from unittest.mock import patch

        with patch("apps.accounts.views.verify_google_id_token", return_value=None):
            response = self.client.post(
                "/api/accounts/google-login/",
                data={"id_token": "invalid_or_expired_google_token"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.json()["detail"],
                "Invalid, expired, or unverified Google ID token.",
            )


@override_settings(ALLOWED_HOSTS=["*"])
class ReCAPTCHAV3TestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email="recaptcha_user@example.com",
            full_name="ReCAPTCHA User",
            password="StrongPassword123!",
            is_verified=True,
        )

    def test_registration_blocked_when_recaptcha_fails(self):
        from unittest.mock import patch

        reg_data = {
            "email": "new_recaptcha_student@example.com",
            "full_name": "New Student",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
            "recaptcha_token": "failed_recaptcha_token",
        }

        with patch("apps.accounts.serializers.verify_recaptcha_token", return_value=False):
            response = self.client.post(
                "/api/accounts/register/",
                data=reg_data,
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_registration_allowed_when_recaptcha_passes(self):
        from unittest.mock import patch

        reg_data = {
            "email": "new_recaptcha_student_passed@example.com",
            "full_name": "New Student",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!",
            "recaptcha_token": "valid_recaptcha_token",
        }

        with patch("apps.accounts.serializers.verify_recaptcha_token", return_value=True):
            response = self.client.post(
                "/api/accounts/register/",
                data=reg_data,
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login_blocked_when_recaptcha_fails(self):
        from unittest.mock import patch

        login_data = {
            "email": "recaptcha_user@example.com",
            "password": "StrongPassword123!",
            "recaptcha_token": "failed_token",
        }

        with patch("apps.accounts.serializers.verify_recaptcha_token", return_value=False):
            response = self.client.post(
                "/api/accounts/login/",
                data=login_data,
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_allowed_when_recaptcha_passes(self):
        from unittest.mock import patch

        login_data = {
            "email": "recaptcha_user@example.com",
            "password": "StrongPassword123!",
            "recaptcha_token": "valid_token",
        }

        with patch("apps.accounts.serializers.verify_recaptcha_token", return_value=True):
            response = self.client.post(
                "/api/accounts/login/",
                data=login_data,
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_forgot_password_blocked_when_recaptcha_fails(self):
        from unittest.mock import patch

        forgot_data = {
            "email": "recaptcha_user@example.com",
            "recaptcha_token": "failed_token",
        }

        with patch("apps.accounts.serializers.verify_recaptcha_token", return_value=False):
            response = self.client.post(
                "/api/accounts/forgot-password/",
                data=forgot_data,
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_forgot_password_allowed_when_recaptcha_passes(self):
        from unittest.mock import patch

        forgot_data = {
            "email": "recaptcha_user@example.com",
            "recaptcha_token": "valid_token",
        }

        with patch("apps.accounts.serializers.verify_recaptcha_token", return_value=True):
            response = self.client.post(
                "/api/accounts/forgot-password/",
                data=forgot_data,
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)


from apps.accounts.models import Invitation


@override_settings(ALLOWED_HOSTS=["*"])
class InvitationTestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.inviter = CustomUser.objects.create_user(
            email="inviter@example.com",
            full_name="Alice Inviter",
            password="Password123!",
            is_verified=True,
        )

    def test_unauthenticated_user_cannot_create_invitation(self):
        response = self.client.post("/api/accounts/invitations/", format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_create_invitation(self):
        self.client.force_authenticate(user=self.inviter)
        response = self.client.post("/api/accounts/invitations/", format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn("invite_url", data)
        self.assertIn("token", data)
        self.assertTrue(data["invite_url"].endswith(data["token"]))

        invitation = Invitation.objects.get(token=data["token"])
        self.assertEqual(invitation.inviter, self.inviter)
        self.assertFalse(invitation.is_used)

    def test_get_public_invitation_valid_and_invalid(self):
        self.client.force_authenticate(user=self.inviter)
        create_res = self.client.post("/api/accounts/invitations/", format="json")
        token = create_res.json()["token"]

        # Public GET with valid token
        self.client.force_authenticate(user=None)
        get_res = self.client.get(f"/api/accounts/invitations/{token}/")
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        get_data = get_res.json()
        self.assertTrue(get_data["valid"])
        self.assertEqual(get_data["inviter"]["full_name"], "Alice Inviter")
        self.assertEqual(get_data["inviter"]["id"], self.inviter.id)

        # Public GET with invalid token
        invalid_res = self.client.get("/api/accounts/invitations/invalid-token-123/")
        self.assertEqual(invalid_res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(invalid_res.json()["valid"])

    def test_registration_with_and_without_invitation(self):
        # 1. Normal registration without invite
        reg_res_1 = self.client.post(
            "/api/accounts/register/",
            data={
                "full_name": "Bob Normal",
                "email": "bob@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            format="json",
        )
        self.assertEqual(reg_res_1.status_code, status.HTTP_201_CREATED)

        # 2. Invitation registration
        self.client.force_authenticate(user=self.inviter)
        inv_res = self.client.post("/api/accounts/invitations/", format="json")
        invite_token = inv_res.json()["token"]

        self.client.force_authenticate(user=None)
        from django.core.cache import cache
        cache.clear()
        reg_res_2 = self.client.post(
            "/api/accounts/register/",
            data={
                "full_name": "Charlie Invited",
                "email": "charlie@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
                "invite_token": invite_token,
            },
            format="json",
        )
        self.assertEqual(reg_res_2.status_code, status.HTTP_201_CREATED)

        invitation = Invitation.objects.get(token=invite_token)
        self.assertTrue(invitation.is_used)
        self.assertIsNotNone(invitation.invited_user)
        self.assertEqual(invitation.invited_user.email, "charlie@example.com")
        self.assertEqual(invitation.inviter, self.inviter)

    def test_duplicate_email_registration_anti_enumeration(self):
        from django.core.cache import cache
        cache.clear()

        # Initial registration
        reg1 = self.client.post(
            "/api/accounts/register/",
            data={
                "full_name": "Original User",
                "email": "original@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(reg1.status_code, status.HTTP_201_CREATED)

        cache.clear()
        # Duplicate registration attempt with existing email
        reg2 = self.client.post(
            "/api/accounts/register/",
            data={
                "full_name": "Attacker Impostor",
                "email": "original@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(reg2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            reg2.json()["message"],
            "Student account registered successfully. Please check your email to verify your account."
        )
        # Ensure only 1 user with that email exists in DB
        self.assertEqual(CustomUser.objects.filter(email="original@example.com").count(), 1)

    def test_rate_limiting_login(self):
        from django.core.cache import cache
        cache.clear()

        for i in range(1, 6):
            res = self.client.post(
                "/api/accounts/login/",
                data={"email": "test_throttle@example.com", "password": "WrongPassword!"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        # 6th attempt should be throttled (5 per minute)
        throttled_res = self.client.post(
            "/api/accounts/login/",
            data={"email": "test_throttle@example.com", "password": "WrongPassword!"},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(throttled_res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_registration_burst_throttling(self):
        from django.core.cache import cache
        cache.clear()

        # 1st request passes
        res1 = self.client.post(
            "/api/accounts/register/",
            data={
                "full_name": "Burst User 1",
                "email": "burst1@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # 2nd request immediately within 4 seconds is burst-throttled
        res2 = self.client.post(
            "/api/accounts/register/",
            data={
                "full_name": "Burst User 2",
                "email": "burst2@example.com",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(res2.status_code, status.HTTP_429_TOO_MANY_REQUESTS)



from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes


@override_settings(ALLOWED_HOSTS=["*"])
class PasswordStrengthValidationTestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.user = CustomUser.objects.create_user(
            email="strength_user@example.com",
            full_name="Strength User",
            password="StrongPassword123!",
            is_verified=True,
        )

    def test_registration_rejects_weak_password(self):
        response = self.client.post(
            "/api/accounts/register/",
            data={
                "full_name": "Weak User",
                "email": "weak_user@example.com",
                "password": "password",
                "confirm_password": "password",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.json())

    def test_change_password_rejects_weak_password(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/accounts/change-password/",
            data={
                "old_password": "StrongPassword123!",
                "new_password": "password",
                "confirm_password": "password",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.json())

    def test_reset_password_rejects_weak_password(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            f"/api/accounts/reset-password/?uid={uidb64}&token={token}",
            data={
                "new_password": "password",
                "confirm_password": "password",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("new_password", response.json())

    def test_complexity_validator_rejects_correcthorsebattery(self):
        # Test register endpoint
        reg_res = self.client.post(
            "/api/accounts/register/",
            data={
                "full_name": "CHB User",
                "email": "chb@example.com",
                "password": "correcthorsebattery",
                "confirm_password": "correcthorsebattery",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(reg_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            reg_res.json()["password"],
            ["Password must contain at least one uppercase letter (A-Z)."]
        )

        # Test change-password endpoint
        self.client.force_authenticate(user=self.user)
        change_res = self.client.post(
            "/api/accounts/change-password/",
            data={
                "old_password": "StrongPassword123!",
                "new_password": "correcthorsebattery",
                "confirm_password": "correcthorsebattery",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(change_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            change_res.json()["new_password"],
            ["Password must contain at least one uppercase letter (A-Z)."]
        )

        # Test reset-password endpoint
        self.client.force_authenticate(user=None)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        reset_res = self.client.post(
            f"/api/accounts/reset-password/?uid={uidb64}&token={token}",
            data={
                "new_password": "correcthorsebattery",
                "confirm_password": "correcthorsebattery",
            },
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(reset_res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            reset_res.json()["new_password"],
            ["Password must contain at least one uppercase letter (A-Z)."]
        )

    def test_forgot_password_throttling(self):
        from django.core.cache import cache
        cache.clear()

        # Send 3 requests within 1 hour -> HTTP 200 OK
        for i in range(1, 4):
            res = self.client.post(
                "/api/accounts/forgot-password/",
                data={"email": "strength_user@example.com"},
                format="json",
                HTTP_HOST="localhost",
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 4th request within an hour -> HTTP 429 Too Many Requests
        res4 = self.client.post(
            "/api/accounts/forgot-password/",
            data={"email": "strength_user@example.com"},
            format="json",
            HTTP_HOST="localhost",
        )
        self.assertEqual(res4.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_forgot_password_email_throttling_across_different_ips(self):
        from django.core.cache import cache
        cache.clear()

        target_email = "target_victim@example.com"
        simulated_ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3", "192.168.1.4"]

        # Send 3 requests targeting the same email from 3 different IPs -> HTTP 200 OK
        for i in range(3):
            res = self.client.post(
                "/api/accounts/forgot-password/",
                data={"email": target_email},
                format="json",
                HTTP_HOST="localhost",
                REMOTE_ADDR=simulated_ips[i],
            )
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 4th request targeting the same email from a 4th DIFFERENT IP -> HTTP 429 Too Many Requests
        res4 = self.client.post(
            "/api/accounts/forgot-password/",
            data={"email": target_email},
            format="json",
            HTTP_HOST="localhost",
            REMOTE_ADDR=simulated_ips[3],
        )
        self.assertEqual(res4.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


@override_settings(ALLOWED_HOSTS=["*"])
class ProviderProfileTestCase(TestCase):
    """
    Test suite for provider registration, role validation, and ProviderProfile CRUD endpoints.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.provider_user = CustomUser.objects.create_user(
            email="provider@example.com",
            password="Password123!",
            full_name="Acme Corp Admin",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )
        self.student_user = CustomUser.objects.create_user(
            email="student@example.com",
            password="Password123!",
            full_name="Regular Student",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.other_provider = CustomUser.objects.create_user(
            email="otherprovider@example.com",
            password="Password123!",
            full_name="Other Provider",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )

        self.provider_profile_url = reverse("accounts:provider-profile")
        self.register_url = reverse("accounts:student-register")

    def test_register_with_provider_role(self):
        """Registering with role='provider' creates a CustomUser with role='provider'."""
        payload = {
            "email": "newprovider@example.com",
            "full_name": "New Provider",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "provider",
        }
        res = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        new_user = CustomUser.objects.get(email="newprovider@example.com")
        self.assertEqual(new_user.role, CustomUser.Role.PROVIDER)

    def test_register_with_admin_role_rejected(self):
        """Attempting to register with role='admin' is explicitly rejected with 400 Bad Request."""
        payload = {
            "email": "attacker@example.com",
            "full_name": "Attacker",
            "password": "Password123!",
            "confirm_password": "Password123!",
            "role": "admin",
        }
        res = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("role", res.data)
        self.assertFalse(CustomUser.objects.filter(email="attacker@example.com").exists())

    def test_provider_can_get_and_update_own_profile(self):
        """A provider user can view and update their own ProviderProfile."""
        self.client.force_authenticate(user=self.provider_user)

        # GET creates or fetches profile
        get_res = self.client.get(self.provider_profile_url)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.data["organization_name"], "Acme Corp Admin")

        # PATCH updates profile
        update_payload = {
            "organization_name": "Acme Technologies Inc",
            "organization_type": "startup",
            "city": "Bangalore",
            "website": "https://acme.example.com",
            "description": "Building AI software.",
        }
        patch_res = self.client.patch(self.provider_profile_url, update_payload, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["organization_name"], "Acme Technologies Inc")
        self.assertEqual(patch_res.data["city"], "Bangalore")

    def test_provider_cannot_self_verify_profile_via_api(self):
        """Provider attempting to send is_verified=True via PATCH is ignored (remains False)."""
        self.client.force_authenticate(user=self.provider_user)

        patch_res = self.client.patch(
            self.provider_profile_url,
            {"organization_name": "Hack Corp", "is_verified": True},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertFalse(patch_res.data["is_verified"])
        profile = ProviderProfile.objects.get(user=self.provider_user)
        self.assertFalse(profile.is_verified)

    def test_student_gets_403_on_provider_profile(self):
        """A student account attempting to access /provider-profile/ gets 403 Forbidden."""
        self.client.force_authenticate(user=self.student_user)
        res = self.client.get(self.provider_profile_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_provider_cannot_access_another_providers_profile(self):
        """Provider only ever accesses their own profile (get_object resolves to request.user's profile)."""
        # Create profile for other_provider first
        ProviderProfile.objects.create(
            user=self.other_provider,
            organization_name="Other Provider Org",
        )

        # Authenticate as provider_user and request endpoint
        self.client.force_authenticate(user=self.provider_user)
        res = self.client.get(self.provider_profile_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotEqual(res.data["organization_name"], "Other Provider Org")
        self.assertEqual(res.data["organization_name"], "Acme Corp Admin")

    def test_provider_welcome_notification_created_once(self):
        """A new provider's first profile access creates exactly one welcome notification; subsequent accesses do not duplicate it."""
        from apps.notifications.models import Notification

        new_provider = CustomUser.objects.create_user(
            email="fresh_provider@example.com",
            password="Password123!",
            full_name="Fresh Provider",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )

        self.client.force_authenticate(user=new_provider)

        # 1. First GET request creates profile and exactly 1 welcome notification
        res1 = self.client.get(self.provider_profile_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        welcome_notifs = Notification.objects.filter(
            recipient=new_provider,
            notification_type=Notification.NotificationType.PROVIDER_WELCOME,
        )
        self.assertEqual(welcome_notifs.count(), 1)
        self.assertIn("Your organization profile is live", welcome_notifs.first().message)

        # 2. Second GET / PATCH request does NOT create duplicate welcome notification
        res2 = self.client.get(self.provider_profile_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        res_patch = self.client.patch(self.provider_profile_url, {"city": "New City"}, format="json")
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)

        self.assertEqual(welcome_notifs.count(), 1)


class StudentResumeTestCase(TestCase):
    """
    Test suite for Student Resume Upload, View, Replace, Delete, Download, and Security rules.
    """

    def setUp(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client = APIClient()
        self.resume_url = "/api/accounts/profile/resume/"
        self.download_url = "/api/accounts/profile/resume/download/"

        # Verified Student User
        self.verified_student = CustomUser.objects.create_user(
            email="student1@example.com",
            full_name="Alice Student",
            password="Password123!",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )

        # Unverified Student User
        self.unverified_student = CustomUser.objects.create_user(
            email="unverified@example.com",
            full_name="Unverified Student",
            password="Password123!",
            role=CustomUser.Role.STUDENT,
            is_verified=False,
        )

        # Provider User
        self.provider_user = CustomUser.objects.create_user(
            email="provider@example.com",
            full_name="Bob Provider",
            password="Password123!",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )

        # Admin User
        self.admin_user = CustomUser.objects.create_user(
            email="admin@example.com",
            full_name="Admin User",
            password="Password123!",
            role=CustomUser.Role.ADMIN,
            is_verified=True,
            is_staff=True,
        )

        # Valid Sample Files
        self.sample_pdf_bytes = b"%PDF-1.5 %sample pdf header and text stream..."
        self.sample_docx_bytes = b"PK\x03\x04 sample docx zip header and content..."

    def test_anonymous_user_denied(self):
        """Unauthenticated requests return 401 Unauthorized."""
        res_get = self.client.get(self.resume_url)
        self.assertEqual(res_get.status_code, status.HTTP_401_UNAUTHORIZED)

        res_post = self.client.post(self.resume_url, {})
        self.assertEqual(res_post.status_code, status.HTTP_401_UNAUTHORIZED)

        res_del = self.client.delete(self.resume_url)
        self.assertEqual(res_del.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unverified_student_denied(self):
        """Unverified student gets 403 Forbidden."""
        self.client.force_authenticate(user=self.unverified_student)
        res = self.client.get(self.resume_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_provider_user_denied(self):
        """Provider account gets 403 Forbidden."""
        self.client.force_authenticate(user=self.provider_user)
        res = self.client.get(self.resume_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_user_denied(self):
        """Admin account gets 403 Forbidden when attempting student resume endpoint."""
        self.client.force_authenticate(user=self.admin_user)
        res = self.client.get(self.resume_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_verified_student_upload_pdf_success(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        pdf_file = SimpleUploadedFile("alice_resume.pdf", self.sample_pdf_bytes, content_type="application/pdf")

        res = self.client.post(self.resume_url, {"file": pdf_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["original_filename"], "alice_resume.pdf")
        self.assertEqual(res.data["download_url"], self.download_url)
        self.assertTrue(self.verified_student.resume is not None)

    def test_verified_student_upload_docx_success(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        docx_file = SimpleUploadedFile("alice_resume.docx", self.sample_docx_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        res = self.client.post(self.resume_url, {"file": docx_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["original_filename"], "alice_resume.docx")

    def test_upload_invalid_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        txt_file = SimpleUploadedFile("resume.txt", b"Plain text resume", content_type="text/plain")

        res = self.client.post(self.resume_url, {"file": txt_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unsupported file type", str(res.data))

    def test_upload_fake_pdf_magic_bytes_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        # File ends in .pdf but header is executable/text, NOT %PDF-
        fake_pdf = SimpleUploadedFile("fake.pdf", b"MZ\x90\x00 fake windows executable content", content_type="application/pdf")

        res = self.client.post(self.resume_url, {"file": fake_pdf}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid or corrupted PDF file", str(res.data))

    def test_upload_oversized_file_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        # Create file over 5 MB
        big_content = b"%PDF-" + b"0" * (5 * 1024 * 1024 + 100)
        big_file = SimpleUploadedFile("big.pdf", big_content, content_type="application/pdf")

        res = self.client.post(self.resume_url, {"file": big_file}, format="multipart")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("File is too large", str(res.data))

    def test_student_get_resume_metadata(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        pdf_file = SimpleUploadedFile("alice_resume.pdf", self.sample_pdf_bytes, content_type="application/pdf")
        self.client.post(self.resume_url, {"file": pdf_file}, format="multipart")

        res = self.client.get(self.resume_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["original_filename"], "alice_resume.pdf")

    def test_student_replace_resume_success(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        # First upload
        file1 = SimpleUploadedFile("old_resume.pdf", self.sample_pdf_bytes, content_type="application/pdf")
        self.client.post(self.resume_url, {"file": file1}, format="multipart")

        # Replacement upload
        file2 = SimpleUploadedFile("new_resume.docx", self.sample_docx_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        res_replace = self.client.post(self.resume_url, {"file": file2}, format="multipart")

        self.assertEqual(res_replace.status_code, status.HTTP_200_OK)
        self.assertEqual(res_replace.data["original_filename"], "new_resume.docx")

    def test_failed_replacement_preserves_existing_resume(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        # Upload valid resume
        file1 = SimpleUploadedFile("initial_resume.pdf", self.sample_pdf_bytes, content_type="application/pdf")
        self.client.post(self.resume_url, {"file": file1}, format="multipart")

        # Attempt invalid replacement
        invalid_file = SimpleUploadedFile("bad.txt", b"plain text", content_type="text/plain")
        res_failed = self.client.post(self.resume_url, {"file": invalid_file}, format="multipart")
        self.assertEqual(res_failed.status_code, status.HTTP_400_BAD_REQUEST)

        # Verify initial resume remains intact
        res_get = self.client.get(self.resume_url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data["original_filename"], "initial_resume.pdf")

    def test_student_delete_resume_success(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        file1 = SimpleUploadedFile("to_delete.pdf", self.sample_pdf_bytes, content_type="application/pdf")
        self.client.post(self.resume_url, {"file": file1}, format="multipart")

        res_del = self.client.delete(self.resume_url)
        self.assertEqual(res_del.status_code, status.HTTP_200_OK)

        # Refresh user instance from DB to ensure no stale cached relation
        self.verified_student.refresh_from_db()
        self.client.force_authenticate(user=self.verified_student)

        # GET should return no resume
        res_get = self.client.get(self.resume_url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data["resume"], None)


    def test_student_download_resume_success(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.verified_student)
        file1 = SimpleUploadedFile("my_resume.pdf", self.sample_pdf_bytes, content_type="application/pdf")
        self.client.post(self.resume_url, {"file": file1}, format="multipart")

        res_dl = self.client.get(self.download_url)
        self.assertEqual(res_dl.status_code, status.HTTP_200_OK)
        self.assertIn("my_resume.pdf", res_dl["Content-Disposition"])

    def test_resume_upload_burst_and_sustained_throttles(self):
        from apps.accounts.throttling import ResumeUploadBurstRateThrottle, ResumeUploadSustainedRateThrottle
        from django.core.cache import cache
        from django.test import override_settings

        cache.clear()
        burst_throttle = ResumeUploadBurstRateThrottle()
        sustained_throttle = ResumeUploadSustainedRateThrottle()

        self.assertEqual(burst_throttle.parse_rate("1/10s"), (1, 10))
        self.assertEqual(sustained_throttle.scope, "resume_upload_sustained")

        class DummyRequest:
            user = self.verified_student

        req = DummyRequest()
        with override_settings(TESTING=False):
            key_burst = burst_throttle.get_cache_key(req, None)
            key_sustained = sustained_throttle.get_cache_key(req, None)
            self.assertIn("resume_upload_burst", key_burst)
            self.assertIn("resume_upload_sustained", key_sustained)


class StudentProfileTestCase(TestCase):
    """
    Test suite for StudentProfile model, view, validators, social links, and privacy enforcement.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.student_user = CustomUser.objects.create_user(
            email="student_profile_test@example.com",
            full_name="Profile Student",
            password="Password123!",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.provider_user = CustomUser.objects.create_user(
            email="provider_profile_test@example.com",
            full_name="Profile Provider",
            password="Password123!",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )
        self.student_profile_url = reverse("accounts:student-profile")

    def test_student_profile_get_and_update_success(self):
        self.client.force_authenticate(user=self.student_user)

        # GET creates profile on first access
        get_res = self.client.get(self.student_profile_url)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)

        payload = {
            "profession": "Full Stack Developer",
            "qualification_type": "degree",
            "qualification_name": "B.Tech Computer Science",
            "institution": "IIT Bombay",
            "skills": ["React", "Django", "Python"],
            "bio": "Passionate developer building web applications.",
            "availability": "immediate",
            "languages": ["English", "Hindi"],
            "city": "Mumbai",
            "portfolio_url": "https://alice.dev",
            "whatsapp_number": "+919876543210",
            "show_phone": True,
            "show_whatsapp": True,
            "social_links": {
                "linkedin": "https://linkedin.com/in/alicedev",
                "github": "https://github.com/alicedev",
            },
        }

        patch_res = self.client.patch(self.student_profile_url, payload, format="json")
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data["profession"], "Full Stack Developer")
        self.assertEqual(patch_res.data["skills"], ["React", "Django", "Python"])
        self.assertTrue(patch_res.data["show_phone"])
        self.assertEqual(patch_res.data["social_links"]["github"], "https://github.com/alicedev")

    def test_social_links_validation_allowed_and_disallowed_keys(self):
        self.client.force_authenticate(user=self.student_user)

        # 1. Valid URLs for all allowed platforms: linkedin, github, instagram, twitter, website
        valid_payload = {
            "social_links": {
                "linkedin": "https://linkedin.com/in/student",
                "github": "https://github.com/student",
                "instagram": "https://instagram.com/student",
                "twitter": "https://x.com/student",
                "website": "https://studentportfolio.com",
            }
        }
        res_valid = self.client.patch(self.student_profile_url, valid_payload, format="json")
        self.assertEqual(res_valid.status_code, status.HTTP_200_OK)
        self.assertEqual(res_valid.data["social_links"]["github"], "https://github.com/student")

        # 2. Unknown key (e.g. "facebook") rejected
        bad_key_payload = {
            "social_links": {
                "facebook": "https://facebook.com/user",
            }
        }
        res_bad_key = self.client.patch(self.student_profile_url, bad_key_payload, format="json")
        self.assertEqual(res_bad_key.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("social_links", res_bad_key.data)

        # 3. Non-URL value rejected
        bad_url_payload = {
            "social_links": {
                "linkedin": "not-a-valid-url",
            }
        }
        res_bad_url = self.client.patch(self.student_profile_url, bad_url_payload, format="json")
        self.assertEqual(res_bad_url.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("social_links", res_bad_url.data)

    def test_profile_picture_validation(self):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.force_authenticate(user=self.student_user)

        # 1. Valid JPEG succeeds
        img_jpg = Image.new("RGB", (100, 100), color="blue")
        buf_jpg = BytesIO()
        img_jpg.save(buf_jpg, format="JPEG")
        valid_jpg = SimpleUploadedFile("avatar.jpg", buf_jpg.getvalue(), content_type="image/jpeg")
        res_jpg = self.client.patch(self.student_profile_url, {"profile_picture": valid_jpg}, format="multipart")
        self.assertEqual(res_jpg.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(res_jpg.data["profile_picture"])

        # 2. Valid PNG succeeds
        img_png = Image.new("RGB", (100, 100), color="red")
        buf_png = BytesIO()
        img_png.save(buf_png, format="PNG")
        valid_png = SimpleUploadedFile("avatar.png", buf_png.getvalue(), content_type="image/png")
        res_png = self.client.patch(self.student_profile_url, {"profile_picture": valid_png}, format="multipart")
        self.assertEqual(res_png.status_code, status.HTTP_200_OK)

        # 3. Valid WEBP succeeds
        img_webp = Image.new("RGB", (100, 100), color="green")
        buf_webp = BytesIO()
        img_webp.save(buf_webp, format="WEBP")
        valid_webp = SimpleUploadedFile("avatar.webp", buf_webp.getvalue(), content_type="image/webp")
        res_webp = self.client.patch(self.student_profile_url, {"profile_picture": valid_webp}, format="multipart")
        self.assertEqual(res_webp.status_code, status.HTTP_200_OK)

        # 4. Wrong file type rejected
        invalid_txt = SimpleUploadedFile("avatar.txt", b"Plain text file", content_type="text/plain")
        res_invalid = self.client.patch(self.student_profile_url, {"profile_picture": invalid_txt}, format="multipart")
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("profile_picture", res_invalid.data)

        # 5. File over 2MB rejected
        oversized_header = b"\xff\xd8" + b"\x00" * (2 * 1024 * 1024 + 500)
        oversized_file = SimpleUploadedFile("huge.jpg", oversized_header, content_type="image/jpeg")
        res_huge = self.client.patch(self.student_profile_url, {"profile_picture": oversized_file}, format="multipart")
        self.assertEqual(res_huge.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("profile_picture", res_huge.data)

    def test_role_isolation_provider_access_denied(self):
        # Unauthenticated -> 401
        res_anon = self.client.get(self.student_profile_url)
        self.assertEqual(res_anon.status_code, status.HTTP_401_UNAUTHORIZED)

        # Provider user -> 403
        self.client.force_authenticate(user=self.provider_user)
        res_provider = self.client.get(self.student_profile_url)
        self.assertEqual(res_provider.status_code, status.HTTP_403_FORBIDDEN)

    def test_contact_privacy_server_side_enforcement(self):
        from apps.opportunities.serializers import ApplicantPublicSerializer, PosterPublicSerializer
        from apps.accounts.models import StudentProfile, ProviderProfile

        # Setup student with phone/whatsapp but privacy toggles FALSE
        stud_prof, _ = StudentProfile.objects.get_or_create(user=self.student_user)
        stud_prof.phone_number = "+919876543210"
        stud_prof.whatsapp_number = "+919876543210"
        stud_prof.show_phone = False
        stud_prof.show_whatsapp = False
        stud_prof.save()

        # Serialize applicant
        ser_applicant = ApplicantPublicSerializer(self.student_user).data
        self.assertIsNone(ser_applicant["phone_number"])
        self.assertIsNone(ser_applicant["whatsapp_number"])

        # Enable privacy toggles TRUE
        stud_prof.show_phone = True
        stud_prof.show_whatsapp = True
        stud_prof.save()

        ser_applicant_opted = ApplicantPublicSerializer(self.student_user).data
        self.assertEqual(ser_applicant_opted["phone_number"], "+919876543210")
        self.assertEqual(ser_applicant_opted["whatsapp_number"], "+919876543210")


from unittest.mock import MagicMock, patch
from django.core.files.uploadedfile import SimpleUploadedFile


@override_settings(ALLOWED_HOSTS=["*"])
class ResumeAIParsingTestCase(TestCase):
    """
    Test suite for AI-assisted resume parsing endpoint (/api/accounts/profile/resume/parse/).
    Verifies authentication/permissions, markdown json parsing, sanitization/limits,
    missing API keys, fallback model retries, 503/502 error responses, real DOCX text extraction,
    and database immutability.
    """

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()
        self.parse_url = "/api/accounts/profile/resume/parse/"

        self.student_user = CustomUser.objects.create_user(
            email="parse_student@example.com",
            password="Password123!",
            full_name="Parse Student",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.student_profile, _ = StudentProfile.objects.get_or_create(user=self.student_user)

        self.provider_user = CustomUser.objects.create_user(
            email="parse_provider@example.com",
            password="Password123!",
            full_name="Parse Provider",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )

    def _attach_resume(self, user, filename="resume.pdf", content=b"%PDF-1.4\n1 0 obj\n"):
        resume_file = SimpleUploadedFile(filename, content, content_type="application/pdf")
        return Resume.objects.create(
            user=user,
            file=resume_file,
            original_filename=filename,
            file_size=len(content),
            mime_type="application/pdf",
        )

    def test_unauthenticated_returns_401(self):
        res = self.client.post(self.parse_url)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_provider_returns_403(self):
        self.client.force_authenticate(user=self.provider_user)
        res = self.client.post(self.parse_url)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    @patch("pypdf.PdfReader")
    def test_missing_google_api_key_returns_503(self, mock_pdf):
        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "Some text")]
        self._attach_resume(self.student_user)
        self.client.force_authenticate(user=self.student_user)
        with override_settings(GOOGLE_API_KEY=""):
            res = self.client.post(self.parse_url)
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(res.json()["detail"], "AI resume parsing is not configured.")

    @patch("pypdf.PdfReader")
    @patch("apps.common.gemini_client.genai.Client")
    def test_model_output_wrapped_in_json_fences(self, mock_client_class, mock_pdf):
        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "Some text")]
        self._attach_resume(self.student_user)
        self.client.force_authenticate(user=self.student_user)

        mock_resp = MagicMock()
        mock_resp.text = '```json\n{\n  "skills": ["Python", "Django"],\n  "qualification_name": "B.Tech CS",\n  "institution": "MIT"\n}\n```'
        mock_client_inst = MagicMock()
        mock_client_inst.models.generate_content.return_value = mock_resp
        mock_client_class.return_value = mock_client_inst

        with override_settings(GOOGLE_API_KEY="test_key_123"):
            res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["skills"], ["Python", "Django"])
        self.assertEqual(data["qualification_name"], "B.Tech CS")
        self.assertEqual(data["institution"], "MIT")

    @patch("pypdf.PdfReader")
    @patch("apps.common.gemini_client.genai.Client")
    def test_skills_sanitization_dedupe_and_caps(self, mock_client_class, mock_pdf):
        import json
        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "Some text")]
        self._attach_resume(self.student_user)
        self.client.force_authenticate(user=self.student_user)

        skills_100 = [f"Skill {i}" for i in range(100)]
        skills_list = ["Python", "python", "A" * 60] + skills_100

        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "skills": skills_list,
            "qualification_name": "Degree " + "X" * 300,
            "institution": "School " + "Y" * 300,
        })
        mock_client_inst = MagicMock()
        mock_client_inst.models.generate_content.return_value = mock_resp
        mock_client_class.return_value = mock_client_inst

        with override_settings(GOOGLE_API_KEY="test_key_123"):
            res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(len(data["skills"]), 30)
        self.assertEqual(data["skills"][0], "Python")
        self.assertNotIn("python", data["skills"])
        self.assertNotIn("A" * 60, data["skills"])
        self.assertEqual(len(data["qualification_name"]), 200)
        self.assertEqual(len(data["institution"]), 200)

    @patch("apps.common.gemini_client.time.sleep")
    @patch("pypdf.PdfReader")
    @patch("apps.common.gemini_client.genai.Client")
    def test_primary_503_fallback_succeeds(self, mock_client_class, mock_pdf, mock_sleep):
        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "Some text")]
        self._attach_resume(self.student_user)
        self.client.force_authenticate(user=self.student_user)

        from google.genai.errors import ServerError
        error_503 = ServerError(503, {"error": {"message": "Service Unavailable"}})
        success_resp = MagicMock(text='{"skills": ["Go"], "qualification_name": "BSc", "institution": "Oxford"}')

        mock_client_inst = MagicMock()
        mock_client_inst.models.generate_content.side_effect = [error_503, success_resp]
        mock_client_class.return_value = mock_client_inst

        with override_settings(GOOGLE_API_KEY="test_key_123", GEMINI_MODEL="primary-model", GEMINI_FALLBACK_MODEL="fallback-model"):
            res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["skills"], ["Go"])
        self.assertEqual(mock_client_inst.models.generate_content.call_count, 2)
        second_call_kwargs = mock_client_inst.models.generate_content.call_args_list[1].kwargs
        self.assertEqual(second_call_kwargs["model"], "fallback-model")
        mock_sleep.assert_called_once_with(2)

    @patch("apps.common.gemini_client.time.sleep")
    @patch("pypdf.PdfReader")
    @patch("apps.common.gemini_client.genai.Client")
    def test_httpx_read_timeout_primary_fallback_succeeds(self, mock_client_class, mock_pdf, mock_sleep):
        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "Some text")]
        self._attach_resume(self.student_user)
        self.client.force_authenticate(user=self.student_user)

        import httpx
        timeout_error = httpx.ReadTimeout("")
        success_resp = MagicMock(text='{"skills": ["Rust"], "qualification_name": "BSc", "institution": "MIT"}')

        mock_client_inst = MagicMock()
        mock_client_inst.models.generate_content.side_effect = [timeout_error, success_resp]
        mock_client_class.return_value = mock_client_inst

        with override_settings(GOOGLE_API_KEY="test_key_123", GEMINI_MODEL="primary-model", GEMINI_FALLBACK_MODEL="fallback-model"):
            res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["skills"], ["Rust"])
        self.assertEqual(mock_client_inst.models.generate_content.call_count, 2)
        second_call_kwargs = mock_client_inst.models.generate_content.call_args_list[1].kwargs
        self.assertEqual(second_call_kwargs["model"], "fallback-model")
        mock_sleep.assert_called_once_with(2)

    @patch("apps.common.gemini_client.time.sleep")
    @patch("pypdf.PdfReader")
    @patch("apps.common.gemini_client.genai.Client")
    def test_both_models_503_returns_503_busy(self, mock_client_class, mock_pdf, mock_sleep):
        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "Some text")]
        self._attach_resume(self.student_user)
        self.client.force_authenticate(user=self.student_user)

        from google.genai.errors import ServerError
        error_503 = ServerError(503, {"error": {"message": "Service Unavailable"}})

        mock_client_inst = MagicMock()
        mock_client_inst.models.generate_content.side_effect = [error_503, error_503]
        mock_client_class.return_value = mock_client_inst

        with override_settings(GOOGLE_API_KEY="test_key_123"):
            res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(res.json()["detail"], "The AI service is busy right now. Please try again in a minute.")
        self.assertEqual(mock_client_inst.models.generate_content.call_count, 2)

    @patch("pypdf.PdfReader")
    @patch("apps.common.gemini_client.genai.Client")
    def test_gemini_404_error_returns_502_not_retried(self, mock_client_class, mock_pdf):
        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "Some text")]
        self._attach_resume(self.student_user)
        self.client.force_authenticate(user=self.student_user)

        from google.genai.errors import ClientError
        error_404 = ClientError(404, {"error": {"message": "Model not found"}})

        mock_client_inst = MagicMock()
        mock_client_inst.models.generate_content.side_effect = error_404
        mock_client_class.return_value = mock_client_inst

        with override_settings(GOOGLE_API_KEY="test_key_123"):
            res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(res.json()["detail"], "Could not analyse the resume right now. Please try again.")
        self.assertEqual(mock_client_inst.models.generate_content.call_count, 1)

    @patch("pypdf.PdfReader")
    def test_parse_burst_rate_limiting_4th_request_429(self, mock_pdf):
        from django.core.cache import cache
        cache.clear()

        mock_pdf.return_value.pages = [MagicMock(extract_text=lambda: "Some text")]
        self._attach_resume(self.student_user)
        self.client.force_authenticate(user=self.student_user)

        with patch("apps.accounts.throttling.settings.TESTING", False):
            with patch("apps.common.gemini_client.genai.Client") as mock_client_class:
                mock_resp = MagicMock()
                mock_resp.text = '{"skills": ["Python"], "qualification_name": "", "institution": ""}'
                mock_inst = MagicMock()
                mock_inst.models.generate_content.return_value = mock_resp
                mock_client_class.return_value = mock_inst

                with override_settings(GOOGLE_API_KEY="test_key_123"):
                    for _ in range(3):
                        res = self.client.post(self.parse_url)
                        self.assertEqual(res.status_code, status.HTTP_200_OK)

                    res4 = self.client.post(self.parse_url)
                    self.assertEqual(res4.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    @patch("apps.common.gemini_client.genai.Client")
    def test_real_docx_extraction_with_mocked_gemini(self, mock_client_class):
        import docx
        import io
        doc = docx.Document()
        doc.add_paragraph("John Doe - Python Developer with B.Tech in Computer Science at Stanford University")
        buf = io.BytesIO()
        doc.save(buf)
        docx_bytes = buf.getvalue()

        resume_file = SimpleUploadedFile("sample.docx", docx_bytes, content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        Resume.objects.create(
            user=self.student_user,
            file=resume_file,
            original_filename="sample.docx",
            file_size=len(docx_bytes),
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        mock_resp = MagicMock()
        mock_resp.text = '{"skills": ["Python"], "qualification_name": "B.Tech", "institution": "Stanford"}'
        mock_client_inst = MagicMock()
        mock_client_inst.models.generate_content.return_value = mock_resp
        mock_client_class.return_value = mock_client_inst

        self.client.force_authenticate(user=self.student_user)
        with override_settings(GOOGLE_API_KEY="test_key_123"):
            res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        gen_prompt = mock_client_inst.models.generate_content.call_args.kwargs["contents"]
        self.assertIn("Python Developer with B.Tech in Computer Science at Stanford University", gen_prompt)

    @patch("pypdf.PdfReader")
    @patch("apps.common.gemini_client.genai.Client")
    def test_successful_resume_parse_does_not_modify_database(self, mock_client_class, mock_pdf_reader):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Python Developer with B.Tech at Stanford"
        mock_pdf_reader.return_value.pages = [mock_page]

        sample_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n" + b"A" * 500
        resume_file = SimpleUploadedFile("my_resume.pdf", sample_pdf_content, content_type="application/pdf")
        Resume.objects.create(
            user=self.student_user,
            file=resume_file,
            original_filename="my_resume.pdf",
            file_size=len(sample_pdf_content),
            mime_type="application/pdf",
        )

        mock_response = MagicMock()
        mock_response.text = '{\n  "skills": ["Python", "Django", "React"],\n  "qualification_name": "Bachelor of Technology",\n  "institution": "Stanford University"\n}'
        mock_client_instance = MagicMock()
        mock_client_instance.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client_instance

        self.student_profile.refresh_from_db()
        skills_before = list(self.student_profile.skills)
        qual_before = self.student_profile.qualification_name
        inst_before = self.student_profile.institution

        self.client.force_authenticate(user=self.student_user)
        with override_settings(GOOGLE_API_KEY="test_key_123"):
            res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["skills"], ["Python", "Django", "React"])

        # ASSERT DATABASE IS UNCHANGED
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.skills, skills_before)
        self.assertEqual(self.student_profile.qualification_name, qual_before)
        self.assertEqual(self.student_profile.institution, inst_before)


@override_settings(ALLOWED_HOSTS=["*"])
class PeopleSearchPublicProfilesTestCase(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.client = APIClient()

        # Requesting User (Student, verified)
        self.req_user = CustomUser.objects.create_user(
            email="req_student@example.com",
            full_name="Requesting Student",
            password="Password123!",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.req_profile, _ = StudentProfile.objects.get_or_create(user=self.req_user)
        self.req_profile.city = "New York"
        self.req_profile.skills = ["Python", "Django"]
        self.req_profile.save()

        # Target Student 1 (discoverable, show_phone=False)
        self.student1 = CustomUser.objects.create_user(
            email="student1@example.com",
            full_name="Alice Student",
            password="Password123!",
            phone_number="+12025550101",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.student1_profile, _ = StudentProfile.objects.get_or_create(user=self.student1)
        self.student1_profile.profession = "Backend Developer"
        self.student1_profile.qualification_name = "B.S. Computer Science"
        self.student1_profile.institution = "MIT"
        self.student1_profile.skills = ["Python", "Django", "PostgreSQL"]
        self.student1_profile.city = "Boston"
        self.student1_profile.availability = "Full-time"
        self.student1_profile.bio = "Passionate Python dev"
        self.student1_profile.whatsapp_number = "+12025550199"
        self.student1_profile.show_phone = False
        self.student1_profile.show_whatsapp = False
        self.student1_profile.is_discoverable = True
        self.student1_profile.save()

        # Target Student 2 (discoverable, show_phone=True)
        self.student2 = CustomUser.objects.create_user(
            email="student2@example.com",
            full_name="Bob Student",
            password="Password123!",
            phone_number="+12025550102",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.student2_profile, _ = StudentProfile.objects.get_or_create(user=self.student2)
        self.student2_profile.profession = "Frontend Developer"
        self.student2_profile.skills = ["React", "JavaScript", "CSS"]
        self.student2_profile.city = "Boston"
        self.student2_profile.whatsapp_number = "+12025550188"
        self.student2_profile.show_phone = True
        self.student2_profile.show_whatsapp = True
        self.student2_profile.is_discoverable = True
        self.student2_profile.save()

        # Target Provider 1 (discoverable, verified)
        self.provider1 = CustomUser.objects.create_user(
            email="provider1@example.com",
            full_name="John ProviderUserFullName",
            password="Password123!",
            role=CustomUser.Role.PROVIDER,
            is_verified=True,
        )
        self.provider1_profile, _ = ProviderProfile.objects.get_or_create(user=self.provider1)
        self.provider1_profile.organization_name = "Acme Technologies"
        self.provider1_profile.organization_type = ProviderProfile.OrganizationType.COMPANY
        self.provider1_profile.description = "Top software engineering agency"
        self.provider1_profile.contact_person = "John Contact"
        self.provider1_profile.address = "123 Main Street"
        self.provider1_profile.city = "San Francisco"
        self.provider1_profile.is_verified = True
        self.provider1_profile.show_phone = False
        self.provider1_profile.show_whatsapp = False
        self.provider1_profile.is_discoverable = True
        self.provider1_profile.save()

        # Target Hidden Student (is_discoverable=False)
        self.hidden_student = CustomUser.objects.create_user(
            email="hidden_student@example.com",
            full_name="Hidden Student",
            password="Password123!",
            role=CustomUser.Role.STUDENT,
            is_verified=True,
        )
        self.hidden_student_profile, _ = StudentProfile.objects.get_or_create(user=self.hidden_student)
        self.hidden_student_profile.is_discoverable = False
        self.hidden_student_profile.save()

        # Inactive User
        self.inactive_user = CustomUser.objects.create_user(
            email="inactive@example.com",
            full_name="Inactive User",
            password="Password123!",
            role=CustomUser.Role.STUDENT,
            is_active=False,
            is_verified=True,
        )

        # Staff User
        self.staff_user = CustomUser.objects.create_user(
            email="staff@example.com",
            full_name="Staff User",
            password="Password123!",
            role=CustomUser.Role.STUDENT,
            is_staff=True,
            is_verified=True,
        )

        # Admin User
        self.admin_user = CustomUser.objects.create_user(
            email="admin@example.com",
            full_name="Admin User",
            password="Password123!",
            role=CustomUser.Role.ADMIN,
            is_verified=True,
        )

        # Unverified User
        self.unverified_user = CustomUser.objects.create_user(
            email="unverified@example.com",
            full_name="Unverified User",
            password="Password123!",
            role=CustomUser.Role.STUDENT,
            is_verified=False,
        )

    def test_anonymous_and_unverified_access(self):
        # Anonymous search -> 401
        res = self.client.get("/api/accounts/people/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Anonymous detail -> 401
        res = self.client.get(f"/api/accounts/people/{self.student1.id}/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Unverified search -> 403
        self.client.force_authenticate(user=self.unverified_user)
        res = self.client.get("/api/accounts/people/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

        # Unverified detail -> 403
        res = self.client.get(f"/api/accounts/people/{self.student1.id}/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_provider_q_search_does_not_match_user_full_name(self):
        self.client.force_authenticate(user=self.req_user)

        # Searching for provider user's full_name ("ProviderUserFullName") MUST NOT match provider
        res_no_match = self.client.get("/api/accounts/people/?q=ProviderUserFullName")
        self.assertEqual(res_no_match.status_code, status.HTTP_200_OK)
        user_ids = [item["user_id"] for item in res_no_match.json()["results"]]
        self.assertNotIn(self.provider1.id, user_ids)

        # Searching for organization_name ("Acme Technologies") MUST match provider
        res_match = self.client.get("/api/accounts/people/?q=Acme Technologies")
        self.assertEqual(res_match.status_code, status.HTTP_200_OK)
        user_ids_match = [item["user_id"] for item in res_match.json()["results"]]
        self.assertIn(self.provider1.id, user_ids_match)

    def test_skills_filter_case_insensitive(self):
        self.client.force_authenticate(user=self.req_user)

        # "python" in lowercase finds Student1 with skills=["Python", "Django", "PostgreSQL"]
        res_lower = self.client.get("/api/accounts/people/?skills=python")
        self.assertEqual(res_lower.status_code, status.HTTP_200_OK)
        results = res_lower.json()["results"]
        user_ids = [item["user_id"] for item in results]
        self.assertIn(self.student1.id, user_ids)

    def test_skills_filter_negative_case(self):
        self.client.force_authenticate(user=self.req_user)

        # "xyzzy" matching no student skills returns empty list []
        res = self.client.get("/api/accounts/people/?skills=xyzzy")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["results"], [])

    def test_skills_filter_or_semantics(self):
        self.client.force_authenticate(user=self.req_user)

        # Searching for two skills where only one matches ("python,nonexistentskill") still returns Student1 (OR semantics)
        res = self.client.get("/api/accounts/people/?skills=python,nonexistentskill")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        results = res.json()["results"]
        user_ids = [item["user_id"] for item in results]
        self.assertIn(self.student1.id, user_ids)

    def test_skills_filter_one_character_rejected(self):
        self.client.force_authenticate(user=self.req_user)

        # 1-character skill search term ("a") returns 400 Bad Request
        res = self.client.get("/api/accounts/people/?skills=a")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["detail"], "Skill search terms must be at least 2 characters long.")

    def test_own_profile_detail_returns_200_and_absent_from_search(self):
        self.client.force_authenticate(user=self.req_user)

        # Requesting user IS ABSENT from search results list
        res_search = self.client.get("/api/accounts/people/")
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        search_user_ids = [item["user_id"] for item in res_search.json()["results"]]
        self.assertNotIn(self.req_user.id, search_user_ids)

        # Requesting user CAN view their OWN profile detail -> 200 OK
        res_detail = self.client.get(f"/api/accounts/people/{self.req_user.id}/")
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        data = res_detail.json()
        self.assertEqual(data["user_id"], self.req_user.id)
        self.assertEqual(data["full_name"], "Requesting Student")
        self.assertEqual(data["display_name"], "Requesting Student")

    def test_self_detail_allowed_when_hidden_and_other_hidden_returns_404(self):
        self.client.force_authenticate(user=self.req_user)

        # Hide requesting user's profile
        self.req_profile.is_discoverable = False
        self.req_profile.save()

        # Own detail returns 200 OK even when is_discoverable=False
        res_own = self.client.get(f"/api/accounts/people/{self.req_user.id}/")
        self.assertEqual(res_own.status_code, status.HTTP_200_OK)
        self.assertEqual(res_own.json()["user_id"], self.req_user.id)

        # Other hidden user's detail returns 404
        res_other = self.client.get(f"/api/accounts/people/{self.hidden_student.id}/")
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

    def test_over_length_q_and_too_many_skills_rejected(self):
        self.client.force_authenticate(user=self.req_user)

        # q > 100 chars -> 400
        long_q = "a" * 101
        res_q = self.client.get(f"/api/accounts/people/?q={long_q}")
        self.assertEqual(res_q.status_code, status.HTTP_400_BAD_REQUEST)

        # 11 skills -> 400
        many_skills = ",".join([f"skill{i}" for i in range(11)])
        res_skills = self.client.get(f"/api/accounts/people/?skills={many_skills}")
        self.assertEqual(res_skills.status_code, status.HTTP_400_BAD_REQUEST)

    def test_role_and_city_filters(self):
        self.client.force_authenticate(user=self.req_user)

        # Filter by role='provider'
        res_role = self.client.get("/api/accounts/people/?role=provider")
        self.assertEqual(res_role.status_code, status.HTTP_200_OK)
        results_role = res_role.json()["results"]
        self.assertEqual(len(results_role), 1)
        self.assertEqual(results_role[0]["role"], "provider")

        # Filter by city='San Francisco'
        res_city = self.client.get("/api/accounts/people/?city=San Francisco")
        self.assertEqual(res_city.status_code, status.HTTP_200_OK)
        results_city = res_city.json()["results"]
        self.assertEqual(len(results_city), 1)
        self.assertEqual(results_city[0]["organization_name"], "Acme Technologies")
        self.assertEqual(results_city[0]["display_name"], "Acme Technologies")

    def test_pagination_across_pages_and_stable_ordering(self):
        self.client.force_authenticate(user=self.req_user)

        # Create 25 matching discoverable student users to ensure >20 total matches
        pagination_users = []
        for i in range(25):
            u = CustomUser.objects.create_user(
                email=f"page_user_{i}@example.com",
                full_name=f"Page Student {i:02d}",
                password="Password123!",
                role=CustomUser.Role.STUDENT,
                is_verified=True,
            )
            sp, _ = StudentProfile.objects.get_or_create(user=u)
            sp.city = "PaginatedCity"
            sp.is_discoverable = True
            sp.save()
            pagination_users.append(u)

        # Fetch page 1
        res_p1 = self.client.get("/api/accounts/people/?city=PaginatedCity&page=1")
        self.assertEqual(res_p1.status_code, status.HTTP_200_OK)
        data1 = res_p1.json()
        self.assertEqual(data1["count"], 25)
        self.assertEqual(len(data1["results"]), 20)

        # Fetch page 2
        res_p2 = self.client.get("/api/accounts/people/?city=PaginatedCity&page=2")
        self.assertEqual(res_p2.status_code, status.HTTP_200_OK)
        data2 = res_p2.json()
        self.assertEqual(data2["count"], 25)
        self.assertEqual(len(data2["results"]), 5)

        # Assert combined IDs are unique across pages and total count matches 25
        ids_p1 = [item["user_id"] for item in data1["results"]]
        ids_p2 = [item["user_id"] for item in data2["results"]]
        all_ids = ids_p1 + ids_p2

        self.assertEqual(len(all_ids), 25)
        self.assertEqual(len(set(all_ids)), 25)

        # Verify ordering is stable across pages (all_ids match DB ordering)
        db_ordered_ids = list(
            CustomUser.objects.filter(id__in=[u.id for u in pagination_users])
            .order_by("-created_at", "id")
            .values_list("id", flat=True)
        )
        self.assertEqual(all_ids, db_ordered_ids)

    def test_assert_num_queries_bound_check_with_10_plus_users(self):
        self.client.force_authenticate(user=self.req_user)

        # Create 12 discoverable users
        for i in range(12):
            u = CustomUser.objects.create_user(
                email=f"bound_user_{i}@example.com",
                full_name=f"Bound Student {i}",
                password="Password123!",
                role=CustomUser.Role.STUDENT,
                is_verified=True,
            )
            sp, _ = StudentProfile.objects.get_or_create(user=u)
            sp.is_discoverable = True
            sp.save()

        # Verify pagination + select_related executes bounded queries (2 queries total)
        with self.assertNumQueries(2):
            res = self.client.get("/api/accounts/people/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_throttling_returns_429_on_burst(self):
        from django.core.cache import cache
        cache.clear()
        self.client.force_authenticate(user=self.req_user)

        # Make 30 requests to search endpoint (burst limit 30/minute)
        for _ in range(30):
            res = self.client.get("/api/accounts/people/")
            self.assertEqual(res.status_code, status.HTTP_200_OK)

        # 31st request triggers HTTP 429
        res_search_throttled = self.client.get("/api/accounts/people/")
        self.assertEqual(res_search_throttled.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

        # Check detail endpoint throttling (60/minute)
        cache.clear()
        for _ in range(60):
            res_d = self.client.get(f"/api/accounts/people/{self.student1.id}/")
            self.assertEqual(res_d.status_code, status.HTTP_200_OK)

        res_detail_throttled = self.client.get(f"/api/accounts/people/{self.student1.id}/")
        self.assertEqual(res_detail_throttled.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_provider_detail_exposes_is_verified_and_hides_address_and_contact_person(self):
        self.client.force_authenticate(user=self.req_user)
        res = self.client.get(f"/api/accounts/people/{self.provider1.id}/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertTrue(data.get("is_verified"))
        self.assertEqual(data.get("display_name"), "Acme Technologies")
        self.assertNotIn("address", data)
        self.assertNotIn("contact_person", data)

    def test_search_never_returns_forbidden_fields(self):
        self.client.force_authenticate(user=self.req_user)
        res = self.client.get("/api/accounts/people/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = res.json()["results"]
        self.assertTrue(len(items) > 0)

        forbidden_keys = {"email", "address", "contact_person", "show_phone", "show_whatsapp", "is_discoverable"}
        for item in items:
            for key in forbidden_keys:
                self.assertNotIn(key, item, f"Forbidden key '{key}' leaked in list response item")

    def test_phone_and_whatsapp_gating(self):
        self.client.force_authenticate(user=self.req_user)

        # Student1 has show_phone=False and show_whatsapp=False -> None
        res_hidden = self.client.get(f"/api/accounts/people/{self.student1.id}/")
        self.assertEqual(res_hidden.status_code, status.HTTP_200_OK)
        data_hidden = res_hidden.json()
        self.assertIsNone(data_hidden.get("phone_number"))
        self.assertIsNone(data_hidden.get("whatsapp_number"))

        # Student2 has show_phone=True and show_whatsapp=True -> present
        res_visible = self.client.get(f"/api/accounts/people/{self.student2.id}/")
        self.assertEqual(res_visible.status_code, status.HTTP_200_OK)
        data_visible = res_visible.json()
        self.assertEqual(data_visible.get("phone_number"), "+12025550102")
        self.assertEqual(data_visible.get("whatsapp_number"), "+12025550188")

    def test_is_discoverable_false_absent_and_404(self):
        self.client.force_authenticate(user=self.req_user)

        res = self.client.get("/api/accounts/people/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user_ids = [item["user_id"] for item in res.json()["results"]]
        self.assertNotIn(self.hidden_student.id, user_ids)

        detail_res = self.client.get(f"/api/accounts/people/{self.hidden_student.id}/")
        self.assertEqual(detail_res.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_staff_and_admin_users_absent_and_404(self):
        self.client.force_authenticate(user=self.req_user)

        res = self.client.get("/api/accounts/people/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user_ids = [item["user_id"] for item in res.json()["results"]]
        self.assertNotIn(self.inactive_user.id, user_ids)
        self.assertNotIn(self.staff_user.id, user_ids)
        self.assertNotIn(self.admin_user.id, user_ids)

        self.assertEqual(self.client.get(f"/api/accounts/people/{self.inactive_user.id}/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(f"/api/accounts/people/{self.staff_user.id}/").status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.get(f"/api/accounts/people/{self.admin_user.id}/").status_code, status.HTTP_404_NOT_FOUND)












