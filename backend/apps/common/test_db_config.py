from unittest import TestCase
from django.core.exceptions import ImproperlyConfigured

from config.db_config import build_database_config


class DatabaseConfigTests(TestCase):
    def test_defaults_unchanged_with_empty_env(self):
        """Calling build_database_config with empty env returns all local defaults."""
        config = build_database_config({})
        self.assertEqual(config["ENGINE"], "django.db.backends.postgresql")
        self.assertEqual(config["NAME"], "nextgig_db")
        self.assertEqual(config["USER"], "postgres")
        self.assertEqual(config["PASSWORD"], "postgres")
        self.assertEqual(config["HOST"], "localhost")
        self.assertEqual(config["PORT"], "5432")
        self.assertEqual(config["CONN_MAX_AGE"], 0)
        self.assertIs(config["CONN_HEALTH_CHECKS"], False)

    def test_no_options_key_by_default(self):
        """When neither SSL nor connect_timeout are configured, no OPTIONS key exists."""
        config = build_database_config({})
        self.assertNotIn("OPTIONS", config)

    def test_options_appear_when_configured(self):
        """OPTIONS contains sslmode, sslrootcert, and connect_timeout when set."""
        env = {
            "DB_SSLMODE": "require",
            "DB_PASSWORD": "valid-rds-password",
            "DB_SSLROOTCERT": "/certs/global-bundle.pem",
            "DB_CONNECT_TIMEOUT": "10",
        }
        config = build_database_config(env)
        self.assertIn("OPTIONS", config)
        self.assertEqual(
            config["OPTIONS"],
            {
                "sslmode": "require",
                "sslrootcert": "/certs/global-bundle.pem",
                "connect_timeout": 10,
            },
        )

    def test_sslrootcert_ignored_without_sslmode(self):
        """DB_SSLROOTCERT is ignored if DB_SSLMODE is not configured."""
        env = {
            "DB_SSLROOTCERT": "/certs/global-bundle.pem",
        }
        config = build_database_config(env)
        self.assertNotIn("OPTIONS", config)

    def test_guard_raises_without_password_when_sslmode_set(self):
        """When DB_SSLMODE is set but DB_PASSWORD is missing, ImproperlyConfigured is raised."""
        env = {
            "DB_SSLMODE": "require",
        }
        with self.assertRaises(ImproperlyConfigured) as ctx:
            build_database_config(env)
        self.assertIn("DB_PASSWORD", str(ctx.exception))

    def test_guard_raises_with_empty_password_when_sslmode_set(self):
        """When DB_SSLMODE is set but DB_PASSWORD is empty, ImproperlyConfigured is raised."""
        env = {
            "DB_SSLMODE": "require",
            "DB_PASSWORD": "   ",
        }
        with self.assertRaises(ImproperlyConfigured) as ctx:
            build_database_config(env)
        self.assertIn("DB_PASSWORD", str(ctx.exception))

    def test_no_guard_when_ssl_unset(self):
        """When DB_SSLMODE is unset, DB_PASSWORD defaults to 'postgres' without raising."""
        config = build_database_config({})
        self.assertEqual(config["PASSWORD"], "postgres")

    def test_db_port_empty_string_falls_back_to_default(self):
        # When DB_PORT is set to an empty string (""), it falls back to default "5432"
        env = {"DB_PORT": ""}
        config = build_database_config(env)
        self.assertEqual(config["PORT"], "5432")

    def test_conn_max_age_and_health_checks_parsing(self):
        """CONN_MAX_AGE and CONN_HEALTH_CHECKS parse positive integers and booleans correctly."""
        env_true = {
            "DB_CONN_MAX_AGE": "60",
            "DB_CONN_HEALTH_CHECKS": "true",
        }
        config = build_database_config(env_true)
        self.assertEqual(config["CONN_MAX_AGE"], 60)
        self.assertIs(config["CONN_HEALTH_CHECKS"], True)

        for true_val in ("1", "yes", "True", "TRUE"):
            cfg = build_database_config({"DB_CONN_HEALTH_CHECKS": true_val})
            self.assertIs(cfg["CONN_HEALTH_CHECKS"], True)

        for false_val in ("false", "0", "no", "False", "anything_else"):
            cfg = build_database_config({"DB_CONN_HEALTH_CHECKS": false_val})
            self.assertIs(cfg["CONN_HEALTH_CHECKS"], False)

    def test_invalid_integers_raise_improperly_configured(self):
        """Invalid integer strings raise ImproperlyConfigured naming the variable."""
        invalid_cases = [
            ("DB_PORT", "not-a-port"),
            ("DB_CONN_MAX_AGE", "abc"),
            ("DB_CONNECT_TIMEOUT", "invalid-timeout"),
        ]
        for var_name, bad_value in invalid_cases:
            with self.subTest(var=var_name, val=bad_value):
                with self.assertRaises(ImproperlyConfigured) as ctx:
                    build_database_config({var_name: bad_value})
                self.assertIn(var_name, str(ctx.exception))
                self.assertNotIn(bad_value, str(ctx.exception))

    def test_no_leak_of_password_in_exception_messages(self):
        """
        The fake password 's3cret-xyz' must never appear in str(exception)
        across all ImproperlyConfigured error cases.
        """
        fake_secret = "s3cret-xyz"

        # Case 1: Invalid DB_PORT while fake password is in env
        with self.assertRaises(ImproperlyConfigured) as ctx1:
            build_database_config({"DB_PORT": "invalid", "DB_PASSWORD": fake_secret})
        self.assertNotIn(fake_secret, str(ctx1.exception))

        # Case 2: Invalid DB_CONN_MAX_AGE while fake password is in env
        with self.assertRaises(ImproperlyConfigured) as ctx2:
            build_database_config({"DB_CONN_MAX_AGE": "invalid", "DB_PASSWORD": fake_secret})
        self.assertNotIn(fake_secret, str(ctx2.exception))

        # Case 3: Invalid DB_CONNECT_TIMEOUT while fake password is in env
        with self.assertRaises(ImproperlyConfigured) as ctx3:
            build_database_config({"DB_CONNECT_TIMEOUT": "invalid", "DB_PASSWORD": fake_secret})
        self.assertNotIn(fake_secret, str(ctx3.exception))

        # Case 4: Missing password when DB_SSLMODE is set
        with self.assertRaises(ImproperlyConfigured) as ctx4:
            build_database_config({"DB_SSLMODE": "require"})
        self.assertNotIn(fake_secret, str(ctx4.exception))

        # Case 5: Empty password when DB_SSLMODE is set
        with self.assertRaises(ImproperlyConfigured) as ctx5:
            build_database_config({"DB_SSLMODE": "require", "DB_PASSWORD": ""})
        self.assertNotIn(fake_secret, str(ctx5.exception))
