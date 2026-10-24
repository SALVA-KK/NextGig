import os
from django.core.exceptions import ImproperlyConfigured


def build_storage_config(env=None, testing=False):
    """
    Builds the Django STORAGES dictionary.

    When S3_STORAGE_ENABLED is False (or testing=True):
      - Returns standard FileSystemStorage for 'default' and StaticFilesStorage for 'staticfiles'.
      - Zero change from today's behavior.
      - Does not import or require django-storages.

    When S3_STORAGE_ENABLED is True:
      - Validates required S3 environment variables without leaking values in exceptions.
      - Configures storages.backends.s3.S3Storage for 'default'.
      - 'staticfiles' remains unchanged.
    """
    if env is None:
        env = os.environ

    raw_enabled = env.get("S3_STORAGE_ENABLED", "false").strip().lower()
    s3_enabled = (raw_enabled in ("true", "1", "yes")) and not testing

    if not s3_enabled:
        return {
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
            },
        }

    # Validate required S3 variables (naming ONLY the variable, never the value)
    bucket_name = env.get("S3_BUCKET_NAME")
    if not bucket_name or not str(bucket_name).strip():
        raise ImproperlyConfigured("S3_BUCKET_NAME must be set when S3 storage is enabled.")

    access_key = env.get("S3_ACCESS_KEY")
    if not access_key or not str(access_key).strip():
        raise ImproperlyConfigured("S3_ACCESS_KEY must be set when S3 storage is enabled.")

    secret_key = env.get("S3_SECRET_KEY")
    if not secret_key or not str(secret_key).strip():
        raise ImproperlyConfigured("S3_SECRET_KEY must be set when S3 storage is enabled.")

    endpoint_url = env.get("S3_ENDPOINT_URL")
    if endpoint_url and not str(endpoint_url).strip():
        endpoint_url = None
    elif endpoint_url:
        endpoint_url = str(endpoint_url).strip()

    region_name = env.get("S3_REGION", "us-east-1").strip() or "us-east-1"
    custom_domain = env.get("S3_PUBLIC_BASE")
    if custom_domain and str(custom_domain).strip():
        custom_domain = str(custom_domain).strip()
    else:
        custom_domain = None

    raw_protocol = env.get("S3_URL_PROTOCOL")
    if raw_protocol and str(raw_protocol).strip():
        url_protocol = str(raw_protocol).strip()
        if not url_protocol.endswith(":"):
            url_protocol = f"{url_protocol}:"
    else:
        url_protocol = "http:" if endpoint_url else "https:"

    options = {
        "bucket_name": str(bucket_name).strip(),
        "access_key": str(access_key).strip(),
        "secret_key": str(secret_key).strip(),
        "region_name": region_name,
        "querystring_auth": False,
        "file_overwrite": False,
        "default_acl": None,
        "url_protocol": url_protocol,
    }

    if endpoint_url:
        options["endpoint_url"] = endpoint_url
    if custom_domain:
        options["custom_domain"] = custom_domain

    return {
        "default": {
            "BACKEND": "storages.backends.s3.S3Storage",
            "OPTIONS": options,
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    }
