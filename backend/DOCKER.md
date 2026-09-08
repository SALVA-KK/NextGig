# NextGig Backend Docker Infrastructure

This guide details how to build, run, manage, and debug the NextGig backend infrastructure using Docker and Docker Compose.

---

## 🏗️ Architecture Overview

The multi-container Docker setup consists of five orchestrated services:

1. **`db`**: PostgreSQL 16 database server (`postgres:16`). Persistent volume `postgres_data` attached.
2. **`redis`**: Redis 7 message broker and cache (`redis:7`).
3. **`web`**: Django REST web application server running `python manage.py runserver 0.0.0.0:8000` (auto-runs migrations on startup).
4. **`celery_worker`**: Celery asynchronous worker process running `celery -A config worker --loglevel=info`.
5. **`celery_beat`**: Celery Beat periodic task scheduler running `celery -A config beat --loglevel=info`.

---

## 🚀 Daily Workflow & Cold Starts

### 1. Resuming Work (Cold Start)
To resume work without rebuilding images:
```bash
docker-compose up -d
```
Docker Compose re-uses existing compiled layers and starts all 5 containers in seconds.

### 2. First-Time Setup or Code Dependency Updates
To build or rebuild container images (e.g. after adding Python dependencies to `requirements.txt` or updating `Dockerfile`):
```bash
docker-compose up --build -d
```

### 3. Stopping Containers Gracefully
To stop running containers without removing data volumes:
```bash
docker-compose down
```

---

## 🔌 Port Conflict Prevention

Docker Compose binds three container ports to the host machine:
- **`8000`**: Django Web API (`web`)
- **`5432`**: PostgreSQL Database (`db`)
- **`6379`**: Redis Cache/Broker (`redis`)

### What happens if a port is already in use?
If local non-Docker services (such as host PostgreSQL, host Redis, or a local `python manage.py runserver`) are already running on port 8000, 5432, or 6379, Docker Compose will **fail explicitly** upon startup with an error like:
```text
Error response from daemon: driver failed programming external connectivity on endpoint nextgig_web:
Bind for 0.0.0.0:8000 failed: port is already allocated
```

### Resolution Strategy:
1. Identify and stop host processes using those ports before running `docker-compose up`:
   - **Stop local Django**: Press `Ctrl+C` in the local terminal running `manage.py runserver`.
   - **Stop local PostgreSQL (Windows)**: Stop the `postgresql-x64-16` Windows service in `services.msc` or run `net stop postgresql-x64-16`.
   - **Stop local Redis**: Stop any host Redis service or process.
2. Verify available ports:
   - **Windows (PowerShell)**: `Get-NetTCPConnection -LocalPort 8000,5432,6379`
   - **Linux/macOS**: `lsof -i :8000 -i :5432 -i :6379`

---

## 🔀 Concurrent Local vs. Docker Server Usage

> [!WARNING]
> Do **NOT** run local `python manage.py runserver` and `docker-compose up` simultaneously.

### Risks of Concurrent Execution:
1. **Port Collisions**: Both attempt to bind to `localhost:8000`. Whichever starts second will crash with a port binding error.
2. **Database Ambiguity**: Local Django connects to `localhost:5432` (host Postgres), whereas Docker Django connects to `db:5432` inside the Docker network (`nextgig_default`). Running both concurrently can lead to confusion about which database holds current data.

### How to tell which server is answering on port 8000:
- **Inspect active container logs**: Run `docker-compose logs -f web`. Refresh the browser; if HTTP logs appear in the terminal, the Docker container answered.
- **Inspect Host Process (Windows)**: Run `Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess, State`.
  - If process belongs to `com.docker.backend.exe` / `com.docker.proxy.exe`, Docker is serving port 8000.
  - If process belongs to `python.exe`, local host Django is serving port 8000.

---

## 🔄 Live Volume Sync & Migration Drift

The `web`, `celery_worker`, and `celery_beat` services mount the host codebase live via:
```yaml
volumes:
  - ./backend:/app
```

### Key Workflow Behaviors:
1. **Instant Code Updates**: Any edit to Python files, views, serializers, or tasks on host is instantly reflected inside running containers without rebuilding or restarting.
2. **Migration Drift Detection**: If you generate a new migration file locally (or pull down migrations from Git), the `web` container automatically runs `python manage.py migrate` every time it starts up via:
   ```yaml
   command: sh -c "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"
   ```
3. **Manual Migration Execution**: You can also manually apply new migrations inside the running container without restarting:
   ```bash
   docker-compose exec web python manage.py migrate
   ```

---

## 🔐 Environment Variables (`.env`) & Rebuilding Rules

### Do `.env` changes require a rebuild?
**NO.** `backend/.env` is injected at container runtime via `env_file: ./backend/.env`.

- **When changing `.env` values**: Simply restart/re-create containers:
  ```bash
  docker-compose up -d
  ```
- **When `--build` is required**: Rebuild is ONLY necessary when:
  1. Modifying `requirements.txt` (adding/updating Python packages).
  2. Modifying `Dockerfile` or system-level dependencies (`apt-get`).

---

## ⚠️ Database Credentials & Stale Volume Persistence

> [!WARNING]
> PostgreSQL initializes its database data directory inside the named volume `postgres_data` only during the **very first container startup**.
>
> If you alter database credentials (`DB_NAME`, `DB_USER`, `DB_PASSWORD`) in `.env` *after* the volume already exists, PostgreSQL will ignore the new credentials and continue using the old credentials stored in `postgres_data`. The `web` container will fail to connect with authentication errors.

### Solution (Reset Database Volume):
To purge the stale data volume and force PostgreSQL to re-initialize with updated `.env` credentials:
```bash
docker-compose down -v
docker-compose up -d
```
*(Note: `docker-compose down -v` permanently deletes the `postgres_data` volume and re-runs database initialization).*

---

## 🛠️ Essential Management Commands

| Action | Command |
|---|---|
| **View All Logs** | `docker-compose logs -f` |
| **View Web Logs** | `docker-compose logs -f web` |
| **View Worker Logs** | `docker-compose logs -f celery_worker` |
| **View Beat Logs** | `docker-compose logs -f celery_beat` |
| **Run Container Migrations** | `docker-compose exec web python manage.py migrate` |
| **Check Applied Migrations** | `docker-compose exec web python manage.py showmigrations` |
| **Create Superuser** | `docker-compose exec web python manage.py createsuperuser` |
| **Run Unit Tests** | `docker-compose exec web python manage.py test` |
| **Open Shell in Web** | `docker-compose exec web python manage.py shell` |
| **Stop All Containers** | `docker-compose down` |
| **Purge Containers & Volumes** | `docker-compose down -v` |
