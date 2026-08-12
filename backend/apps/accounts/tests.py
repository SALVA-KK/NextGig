from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import CustomUser
from apps.accounts.utils import format_phone_for_msg91


@override_settings(ALLOWED_HOSTS=["*"])
class MSG91PhoneOTPTestCase(TestCase):
    def setUp(self):
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


from apps.accounts.models import Invitation


@override_settings(ALLOWED_HOSTS=["*"])
class InvitationTestCase(TestCase):
    def setUp(self):
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


