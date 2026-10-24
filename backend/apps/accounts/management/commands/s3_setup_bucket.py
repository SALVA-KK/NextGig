import json
import logging
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Idempotently create the NextGig S3/MinIO bucket and configure public access for profile pictures only."

    def handle(self, *args, **options):
        default_storage_opts = settings.STORAGES.get("default", {}).get("OPTIONS", {})

        bucket_name = default_storage_opts.get("bucket_name")
        endpoint_url = default_storage_opts.get("endpoint_url")
        access_key = default_storage_opts.get("access_key")
        secret_key = default_storage_opts.get("secret_key")
        region_name = default_storage_opts.get("region_name", "us-east-1")

        if not bucket_name or not access_key or not secret_key:
            raise CommandError("S3 storage is not configured. S3_BUCKET_NAME, S3_ACCESS_KEY, and S3_SECRET_KEY are required.")

        s3_client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
        )

        try:
            s3_client.head_bucket(Bucket=bucket_name)
            self.stdout.write(self.style.SUCCESS(f"S3 bucket '{bucket_name}' already exists."))
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in ("404", "NoSuchBucket"):
                create_kwargs = {"Bucket": bucket_name}
                if region_name and region_name != "us-east-1":
                    create_kwargs["CreateBucketConfiguration"] = {"LocationConstraint": region_name}
                s3_client.create_bucket(**create_kwargs)
                self.stdout.write(self.style.SUCCESS(f"Created S3 bucket '{bucket_name}'."))
            else:
                raise CommandError(f"Failed to access bucket: {error_code}") from exc

        # When running against real AWS (endpoint_url is empty/None), update the bucket's
        # Public Access Block so bucket policies can permit public read on profile pictures.
        # When an endpoint URL is configured (Moto/MinIO), skip this call.
        if not endpoint_url or not str(endpoint_url).strip():
            s3_client.put_public_access_block(
                Bucket=bucket_name,
                PublicAccessBlockConfiguration={
                    "BlockPublicAcls": True,
                    "IgnorePublicAcls": True,
                    "BlockPublicPolicy": False,
                    "RestrictPublicBuckets": False,
                },
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Configured bucket public access block on '{bucket_name}' (BlockPublicPolicy=False, RestrictPublicBuckets=False)."
                )
            )

        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "PublicReadProfilePictures",
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{bucket_name}/profile_pics/*",
                }
            ],
        }

        try:
            s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
            self.stdout.write(
                self.style.SUCCESS("Successfully configured bucket policy: 'profile_pics/*' is public-read; 'resumes/*' is private.")
            )
        except ClientError as exc:
            error_code = str(exc.response.get("Error", {}).get("Code", ""))
            if error_code in ("AccessDenied", "403"):
                err_msg = (
                    f"Failed to apply bucket policy to '{bucket_name}': AccessDenied. "
                    "Account-level Block Public Access may be enabled in your AWS account, "
                    "which overrides bucket-level public access settings. "
                    "Please check your account-level S3 Block Public Access settings in the AWS Console."
                )
                self.stderr.write(self.style.ERROR(err_msg))
                raise CommandError(err_msg) from exc
            raise CommandError(f"Failed to apply bucket policy: {error_code}") from exc
