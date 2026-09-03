from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import CustomUser
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







