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

        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))
        self.stdout.write(
            self.style.SUCCESS("Successfully configured bucket policy: 'profile_pics/*' is public-read; 'resumes/*' is private.")
        )
