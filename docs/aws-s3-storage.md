# S3 Storage - Architecture & Implementation Note

Status: Implemented behind a flag (S3_STORAGE_ENABLED, default false), emulated with moto, not deployed to AWS. A MinIO image could not be pulled in the development environment, so the existing moto container is used as the S3 API emulator.

## 1. Current Behavior & Security Boundaries
- Three file fields in `apps.accounts`: `StudentProfile.profile_picture`, `ProviderProfile.profile_picture` (`ImageField`), and `Resume.file` (`FileField`).
- Resumes are served exclusively via authenticated views (`StudentResumeDownloadView` for owners; `ApplicationResumeDownloadView` for opportunity posters and admins) and are never exposed by URL.
- Profile pictures are public-read through a bucket policy applied to `profile_pics/*` only; `resumes/*` remains private.
- File validation is unchanged (resumes: max 5 MB, `.pdf`/`.docx`, magic bytes, UUID storage keys; profile pictures: max 2 MB, `.jpg`/`.jpeg`/`.png`/`.webp`, magic bytes).

## 2. How It Works
- Powered by `django-storages==1.14.6` and configured via `build_storage_config` in `backend/config/storage_config.py`.
- Storage is forced off under automated tests (`testing=True`), falling back to local `FileSystemStorage`.
- `ResumeParseView` now reads via `resume.file.open("rb")`, preserving error codes and messages.
- `python manage.py s3_setup_bucket` is idempotent and configures the bucket and public policy on `profile_pics/*`. It must be re-run after moto restarts (alongside `aws_setup_resources`) because moto state is in memory and uploads vanish on restart.

## 3. Environment Variables
Configuration variable names:
- `S3_STORAGE_ENABLED`
- `S3_ENDPOINT_URL`
- `S3_BUCKET_NAME`
- `S3_ACCESS_KEY`
- `S3_SECRET_KEY`
- `S3_REGION`
- `S3_PUBLIC_BASE`

Values must be set in the repository root `.env` file because `docker-compose.yml` environment blocks override `backend/.env`.

## 4. Limitations
- Existing local files are not migrated (they return `NoSuchKey` / not found when the flag is on).
- Moto is in-memory; uploaded files vanish on container restart.
- Not tested against real AWS or MinIO.
- The `DEBUG=True` `/media/` route still serves local `MEDIA_ROOT` when the flag is off.

## 5. Switching to Real AWS
To switch to real AWS S3:
- Remove `S3_ENDPOINT_URL` (or leave it unset).
- Configure real AWS IAM credentials (`S3_ACCESS_KEY`, `S3_SECRET_KEY`).
- Set target `S3_BUCKET_NAME`, `S3_REGION`, and production `S3_PUBLIC_BASE`.
