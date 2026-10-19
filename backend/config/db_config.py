from django.core.exceptions import ImproperlyConfigured


def build_database_config(env=None):
    """
    Builds the DATABASES['default'] configuration dictionary from an environment mapping.

    Maintains full backward-compatibility with local development defaults:
      - ENGINE: django.db.backends.postgresql
      - NAME: nextgig_db
      - USER: postgres
      - PASSWORD: postgres (when DB_SSLMODE is unset)
      - HOST: localhost
      - PORT: 5432
      - CONN_MAX_AGE: 0
      - CONN_HEALTH_CHECKS: False

    When DB_SSLMODE is configured:
      - DB_PASSWORD must be explicitly provided (no insecure fallback).
      - OPTIONS['sslmode'] is populated.
      - OPTIONS['sslrootcert'] is populated only if DB_SSLMODE is set.
      - OPTIONS['connect_timeout'] is populated if DB_CONNECT_TIMEOUT is set.
    """
    if env is None:
        env = {}

    db_name = env.get("DB_NAME", "nextgig_db")
    db_user = env.get("DB_USER", "postgres")
    db_host = env.get("DB_HOST", "localhost")

    # If DB_PORT is missing or empty string (""), fall back to default "5432"
    raw_port = env.get("DB_PORT")
    if raw_port is not None and str(raw_port).strip() != "":
        try:
            int(str(raw_port).strip())
            db_port = str(raw_port).strip()
        except (ValueError, TypeError) as exc:
            raise ImproperlyConfigured("DB_PORT must be an integer.") from exc
    else:
        db_port = "5432"

    raw_sslmode = env.get("DB_SSLMODE")
    sslmode = raw_sslmode.strip() if raw_sslmode and raw_sslmode.strip() else None

    # Password resolution and guard:
    # If DB_SSLMODE is set, DB_PASSWORD must be explicitly set and non-empty.
    # If DB_SSLMODE is not set, retain the local default "postgres".
    raw_password = env.get("DB_PASSWORD")
    if sslmode:
        if raw_password is None or str(raw_password).strip() == "":
            raise ImproperlyConfigured(
                "DB_PASSWORD must be explicitly configured when DB_SSLMODE is set."
            )
        db_password = str(raw_password)
    else:
        db_password = env.get("DB_PASSWORD", "postgres")

    # Parse CONN_MAX_AGE (default: 0)
    raw_conn_max_age = env.get("DB_CONN_MAX_AGE")
    if raw_conn_max_age is not None and str(raw_conn_max_age).strip() != "":
        try:
            conn_max_age = int(str(raw_conn_max_age).strip())
        except (ValueError, TypeError) as exc:
            raise ImproperlyConfigured("DB_CONN_MAX_AGE must be an integer.") from exc
    else:
        conn_max_age = 0

    # Parse CONN_HEALTH_CHECKS (default: False)
    raw_health_checks = env.get("DB_CONN_HEALTH_CHECKS")
    if raw_health_checks is not None and str(raw_health_checks).strip() != "":
        conn_health_checks = str(raw_health_checks).strip().lower() in ("true", "1", "yes")
    else:
        conn_health_checks = False

    # Build OPTIONS dictionary only when at least one option is present
    options = {}
    if sslmode:
        options["sslmode"] = sslmode
        raw_sslrootcert = env.get("DB_SSLROOTCERT")
        if raw_sslrootcert and str(raw_sslrootcert).strip():
            options["sslrootcert"] = str(raw_sslrootcert).strip()

    raw_timeout = env.get("DB_CONNECT_TIMEOUT")
    if raw_timeout is not None and str(raw_timeout).strip() != "":
        try:
            options["connect_timeout"] = int(str(raw_timeout).strip())
        except (ValueError, TypeError) as exc:
            raise ImproperlyConfigured("DB_CONNECT_TIMEOUT must be an integer.") from exc

    config = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": db_name,
        "USER": db_user,
        "PASSWORD": db_password,
        "HOST": db_host,
        "PORT": db_port,
        "CONN_MAX_AGE": conn_max_age,
        "CONN_HEALTH_CHECKS": conn_health_checks,
    }

    if options:
        config["OPTIONS"] = options

    return config
