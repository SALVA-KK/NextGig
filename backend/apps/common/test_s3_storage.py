import json
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.accounts.models import Resume, StudentProfile
from apps.accounts.serializers import ResumeSerializer
from apps.opportunities.models import Application, Opportunity
from apps.opportunities.serializers import ApplicantListSerializer
from config.storage_config import build_storage_config
from storages.backends.s3 import S3Storage

User = get_user_model()


class S3StorageConfigTests(TestCase):
    def test_flag_off_returns_filesystem_storage_config_exactly(self):
        """When S3_STORAGE_ENABLED is false (or unset), standard FileSystemStorage is returned."""
        config_empty = build_storage_config({}, testing=False)
        self.assertEqual(
            config_empty,
            {
                "default": {
                    "BACKEND": "django.core.files.storage.FileSystemStorage",
                },
                "staticfiles": {
                    "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
                },
            },
        )

        config_false = build_storage_config({"S3_STORAGE_ENABLED": "false"}, testing=False)
        self.assertEqual(config_false["default"]["BACKEND"], "django.core.files.storage.FileSystemStorage")

    def test_flag_on_selects_s3_storage_with_options(self):
        """When S3_STORAGE_ENABLED is true, S3Storage backend is configured with options."""
        env = {
            "S3_STORAGE_ENABLED": "true",
            "S3_BUCKET_NAME": "my-bucket",
            "S3_ACCESS_KEY": "my-access-key",
            "S3_SECRET_KEY": "my-secret-key",
            "S3_ENDPOINT_URL": "http://minio:9000",
            "S3_REGION": "us-east-1",
            "S3_PUBLIC_BASE": "localhost:9000/my-bucket",
        }
        config = build_storage_config(env, testing=False)
        self.assertEqual(config["default"]["BACKEND"], "storages.backends.s3.S3Storage")
        opts = config["default"]["OPTIONS"]
        self.assertEqual(opts["bucket_name"], "my-bucket")
        self.assertEqual(opts["access_key"], "my-access-key")
        self.assertEqual(opts["secret_key"], "my-secret-key")
        self.assertEqual(opts["endpoint_url"], "http://minio:9000")
        self.assertEqual(opts["region_name"], "us-east-1")
        self.assertEqual(opts["custom_domain"], "localhost:9000/my-bucket")
        self.assertFalse(opts["querystring_auth"])
        self.assertFalse(opts["file_overwrite"])
        self.assertIsNone(opts["default_acl"])
        self.assertEqual(opts["url_protocol"], "http:")

    def test_missing_required_s3_vars_raise_improperly_configured_without_leaking_secrets(self):
        """Missing S3_BUCKET_NAME, S3_ACCESS_KEY, or S3_SECRET_KEY raise ImproperlyConfigured naming only the var."""
        fake_secret = "s3cret-xyz"

        # Missing bucket name
        env_no_bucket = {
            "S3_STORAGE_ENABLED": "true",
            "S3_ACCESS_KEY": fake_secret,
            "S3_SECRET_KEY": fake_secret,
        }
        with self.assertRaises(ImproperlyConfigured) as ctx1:
            build_storage_config(env_no_bucket, testing=False)
        self.assertIn("S3_BUCKET_NAME", str(ctx1.exception))
        self.assertNotIn(fake_secret, str(ctx1.exception))

        # Missing access key
        env_no_access = {
            "S3_STORAGE_ENABLED": "true",
            "S3_BUCKET_NAME": "my-bucket",
            "S3_SECRET_KEY": fake_secret,
        }
        with self.assertRaises(ImproperlyConfigured) as ctx2:
            build_storage_config(env_no_access, testing=False)
        self.assertIn("S3_ACCESS_KEY", str(ctx2.exception))
        self.assertNotIn(fake_secret, str(ctx2.exception))

        # Missing secret key
        env_no_secret = {
            "S3_STORAGE_ENABLED": "true",
            "S3_BUCKET_NAME": "my-bucket",
            "S3_ACCESS_KEY": fake_secret,
        }
        with self.assertRaises(ImproperlyConfigured) as ctx3:
            build_storage_config(env_no_secret, testing=False)
        self.assertIn("S3_SECRET_KEY", str(ctx3.exception))
        self.assertNotIn(fake_secret, str(ctx3.exception))

    def test_testing_forces_flag_off_even_if_env_says_true(self):
        """Under testing=True, S3_STORAGE_ENABLED is forced off and FileSystemStorage is selected."""
        env = {
            "S3_STORAGE_ENABLED": "true",
            "S3_BUCKET_NAME": "my-bucket",
            "S3_ACCESS_KEY": "key",
            "S3_SECRET_KEY": "secret",
        }
        config = build_storage_config(env, testing=True)
        self.assertEqual(config["default"]["BACKEND"], "django.core.files.storage.FileSystemStorage")


class S3StorageUrlAndPrivacyTests(TestCase):
    def test_picture_url_contains_no_query_string(self):
        """Profile picture URLs generated with querystring_auth=False contain no '?' query string."""
        storage = S3Storage(
            bucket_name="test-bucket",
            access_key="test-key",
            secret_key="test-secret",
            endpoint_url="http://minio:9000",
            custom_domain="localhost:9000/test-bucket",
            querystring_auth=False,
            file_overwrite=False,
            default_acl=None,
            url_protocol="http:",
        )
        url = storage.url("profile_pics/sample.jpg")
        self.assertEqual(url, "http://localhost:9000/test-bucket/profile_pics/sample.jpg")
        self.assertNotIn("?", url)

    def test_resume_serializers_and_views_never_output_a_resume_file_url(self):
        """Resume serializers and application list serializers expose only protected endpoints, never direct file URLs."""
        student = User.objects.create_user(
            email="privacy_student@example.com",
            password="Password123!",
            full_name="Privacy Student",
            role=User.Role.STUDENT,
        )
        resume_file = SimpleUploadedFile("resume.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        resume = Resume.objects.create(
            user=student,
            file=resume_file,
            original_filename="resume.pdf",
            file_size=len(b"%PDF-1.4 test content"),
            mime_type="application/pdf",
        )

        # ResumeSerializer metadata inspection
        resume_data = ResumeSerializer(resume).data
        self.assertEqual(resume_data["download_url"], "/api/accounts/profile/resume/download/")
        self.assertNotIn("file", resume_data)
        self.assertNotIn(resume.file.name, str(resume_data))

        # ApplicationListSerializer metadata inspection
        poster = User.objects.create_user(
            email="poster_privacy@example.com",
            password="Password123!",
            full_name="Poster Privacy",
            role=User.Role.PROVIDER,
        )
        opp = Opportunity.objects.create(
            poster=poster,
            title="Privacy Opportunity",
            category=Opportunity.Category.INTERNSHIP,
            description="Test opportunity",
            pay_type=Opportunity.PayType.UNPAID,
            work_mode=Opportunity.WorkMode.REMOTE,
        )
        app = Application.objects.create(
            opportunity=opp,
            applicant=student,
            cover_note="Cover note",
        )
        app_data = ApplicantListSerializer(app).data
        self.assertTrue(app_data["has_resume"])
        self.assertEqual(app_data["resume_download_url"], f"/api/applications/{app.id}/resume/")
        self.assertNotIn(resume.file.name, str(app_data))


class ResumeParseViewStorageTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.parse_url = "/api/accounts/profile/resume/parse/"
        self.student = User.objects.create_user(
            email="parse_test_student@example.com",
            password="Password123!",
            full_name="Parse Test Student",
            role=User.Role.STUDENT,
            is_verified=True,
        )
        StudentProfile.objects.get_or_create(user=self.student)
        self.client.force_authenticate(user=self.student)

    def test_parse_view_reads_through_file_object_and_returns_400_on_filenotfounderror(self):
        """When resume.file.open raises FileNotFoundError, parse view returns HTTP 400 with missing message."""
        resume_file = SimpleUploadedFile("my_resume.pdf", b"%PDF-1.4 test content", content_type="application/pdf")
        resume = Resume.objects.create(
            user=self.student,
            file=resume_file,
            original_filename="my_resume.pdf",
            file_size=len(b"%PDF-1.4 test content"),
            mime_type="application/pdf",
        )

        with patch.object(resume.file, "open", side_effect=FileNotFoundError("Missing S3 object")):
            with patch("apps.accounts.models.Resume.objects.filter", return_value=MagicMock(first=lambda: resume)):
                res = self.client.post(self.parse_url)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(res.json()["detail"], "Resume file not found on server storage.")


class S3SetupBucketCommandTests(TestCase):
    @patch("boto3.client")
    def test_s3_setup_bucket_creates_bucket_only_when_head_bucket_says_404(self, mock_boto_client):
        """s3_setup_bucket command calls create_bucket only on 404 and applies policy to profile_pics/* only."""
        mock_s3 = MagicMock()
        mock_boto_client.return_value = mock_s3

        # Scenario 1: Bucket does not exist (head_bucket raises 404 ClientError)
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadBucket",
        )

        custom_storages = {
            "default": {
                "BACKEND": "storages.backends.s3.S3Storage",
                "OPTIONS": {
                    "bucket_name": "nextgig-media",
                    "access_key": "test-key",
                    "secret_key": "test-secret",
                    "endpoint_url": "http://minio:9000",
                    "region_name": "us-east-1",
                },
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }

        with override_settings(STORAGES=custom_storages):
            call_command("s3_setup_bucket")

        mock_s3.create_bucket.assert_called_once_with(Bucket="nextgig-media")
        mock_s3.put_bucket_policy.assert_called_once()
        policy_call_kwargs = mock_s3.put_bucket_policy.call_args.kwargs
        self.assertEqual(policy_call_kwargs["Bucket"], "nextgig-media")
        policy = json.loads(policy_call_kwargs["Policy"])

        # Policy assertions: only profile_pics/* is public-read
        statements = policy["Statement"]
        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0]["Effect"], "Allow")
        self.assertEqual(statements[0]["Principal"], "*")
        self.assertEqual(statements[0]["Action"], "s3:GetObject")
        self.assertTrue(statements[0]["Resource"].endswith("/profile_pics/*"))
        self.assertNotIn("resumes", json.dumps(policy))

        # Scenario 2: Bucket already exists (head_bucket succeeds) -> create_bucket not called
        mock_s3.reset_mock()
        mock_s3.head_bucket.side_effect = None
        mock_s3.head_bucket.return_value = {}

        with override_settings(STORAGES=custom_storages):
            call_command("s3_setup_bucket")

        mock_s3.create_bucket.assert_not_called()
        mock_s3.put_bucket_policy.assert_called_once()
