# AWS RDS PostgreSQL Integration Note

> **Status:** Configured for RDS, not deployed.

This document describes how NextGig is configured to connect to an external AWS RDS PostgreSQL database instance while maintaining local development and Docker Compose compatibility.

---

## 1. Environment Variables

The database configuration in `backend/config/db_config.py` evaluates the following variables:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DB_NAME` | Database name | `nextgig_db` |
| `DB_USER` | Database username | `postgres` |
| `DB_PASSWORD` | Database user password. When `DB_SSLMODE` is set, must be explicitly provided. | `postgres` (local dev only) |
| `DB_HOST` | Database host | `localhost` (in direct shell) |
| `DB_PORT` | Database port (must be an integer; empty string falls back to default) | `5432` |
| `DB_SSLMODE` | PostgreSQL SSL connection mode (e.g. `require`, `verify-ca`, `verify-full`). When set, triggers SSL options and enforces explicit password. | *None* (disabled) |
| `DB_SSLROOTCERT` | Path to the CA certificate bundle. Populated into `OPTIONS['sslrootcert']` only when `DB_SSLMODE` is set. | *None* |
| `DB_CONNECT_TIMEOUT` | Connection timeout in seconds (must be an integer), passed to `OPTIONS['connect_timeout']`. | *None* |
| `DB_CONN_MAX_AGE` | Connection persistence lifetime in seconds (`CONN_MAX_AGE`). Must be kept at `0` under ASGI/Channels. | `0` |
| `DB_CONN_HEALTH_CHECKS` | Whether to perform health checks on existing connections before reuse (`CONN_HEALTH_CHECKS`). | `False` |
| `CONTAINER_DB_HOST` | Hostname override used by Docker Compose services (`web`, `celery_worker`, `celery_beat`, `lambda_poller`). | `db` |
| `CONTAINER_DB_PORT` | Port override used by Docker Compose services. | `5432` |

---

## 2. Pointing Docker Containers at RDS

To point the NextGig Docker Compose services at an AWS RDS instance:

1. **Root `.env` Configuration:**
   Set the container network targets in the root `.env`:
   ```bash
   CONTAINER_DB_HOST=<your-rds-endpoint>.rds.amazonaws.com
   CONTAINER_DB_PORT=5432
   ```

2. **Backend `.env` Configuration:**
   Set the connection credentials and SSL parameters in `backend/.env`:
   ```bash
   DB_NAME=nextgig_db
   DB_USER=nextgig_admin
   DB_PASSWORD=<secure-rds-password>
   DB_SSLMODE=require
   ```

3. **Recreate Containers:**
   Apply the environment variables by forcing recreation of the services:
   ```bash
   docker-compose up -d --force-recreate
   ```

---

## 3. Network Access & SSL Verification

- **Local Docker Reaching RDS:**
  For local Docker containers to reach AWS RDS directly, the RDS instance must be configured as **Publicly Accessible**, and its VPC Security Group inbound rules must be strictly limited to your current public IP address on TCP port `5432`.
- **SSL Verification (`verify-full`):**
  If using `DB_SSLMODE=verify-full`, the official AWS RDS root CA bundle (e.g. `global-bundle.pem`) must be mounted into the container (via `docker-compose.yml` volumes), and `DB_SSLROOTCERT` must point to the absolute path inside the container (e.g. `/app/certs/global-bundle.pem`).
- **Connection Persistence under Daphne / Channels:**
  `DB_CONN_MAX_AGE` should be kept at `0` when running under Daphne / Django Channels. ASGI worker threads and WebSocket consumer lifecycles can lead to connection leaks or stale connections if persistent database pooling is enabled without an external pooler (like AWS RDS Proxy).

---

## 4. Testing Warning

> **WARNING:**
> If RDS credentials (`DB_HOST`, `DB_NAME`, `DB_PASSWORD`, `DB_USER`) are placed into `backend/.env`, running `python manage.py test` locally or inside a container will cause Django's test runner to attempt creating a test database directly on your AWS RDS instance (`test_nextgig_db`).
> Automated test suites must always run against local database configurations.

---

## 5. pgvector Extension Requirements

NextGig utilizes PostgreSQL vector embeddings via the `pgvector` extension:
- Migration `0007_opportunityembedding` executes:
  ```sql
  CREATE EXTENSION IF NOT EXISTS vector;
  ```
- The RDS master user or provisioned database user must possess the privileges to create PostgreSQL extensions.
- The RDS PostgreSQL engine version must support `pgvector`; check AWS's current RDS documentation for supported versions.

---

## 6. Limitations

- **Local Development Database:** The `db` service running `pgvector/pgvector:pg16` remains in `docker-compose.yml` as the primary local development database.
- **Offline Configuration:** The codebase is configured for RDS, but no live RDS database connection was executed or validated in this environment.
