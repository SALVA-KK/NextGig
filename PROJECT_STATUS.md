# Technical Audit & Comprehensive Project Status Report - NextGig

---

## 1. SESSION SUMMARY

Today's session delivered substantial architectural, security, database, API, UI/UX, AI/LLM integration, and performance enhancements across the NextGig platform. Below is a complete narrative of everything accomplished, all bugs diagnosed and resolved, and the current operational state of the codebase.

### Hardened Gemini Client & AI Resume Parsing Subsystem
- **Reusable Gemini Infrastructure**: Created `backend/apps/common/gemini_client.py` encapsulating production-hardened Google Gemini API interaction (`google-genai` SDK). Implements per-attempt timeout (20s / 20,000ms via `HttpOptions`), single-attempt configuration (`HttpRetryOptions(attempts=1)`), primary model (`gemini-3.1-flash-lite`) and fallback model (`GEMINI_FALLBACK_MODEL` setting default `gemini-3-flash-preview`). Automatically handles status code and message classification for transient server errors (429, 503, timeouts) with single fallback retry while avoiding retries on client errors (400, 401, 403, 404).
- **AI Resume Parse Endpoint & Sanitization**: Built `POST /api/accounts/profile/resume/parse-ai/` (`ResumeParseView`) in `backend/apps/accounts/views.py`. Extracts raw text from PDF (`pypdf`) or DOCX (`python-docx`), caps text input at 12,000 characters, sanitizes prompt text, and returns structured JSON suggestions (`skills`, `qualification_name`, `institution`).
- **Read-Only Review & Skill Merging Flow**: Designed a strictly read-only review flow in `<ResumeCard />` (`frontend/src/components/profile/ResumeCard.jsx`). AI suggestions are presented in a review modal (`showReviewModal`) and are **never** auto-saved. Saving executes a merge-not-replace algorithm (`handleSaveSuggestions`) preserving existing student skills.
- **Layered Rate Throttling & Test Coverage**: Protected the resume parse endpoint with `ResumeParseThrottle` (5 requests/hour per student). Comprehensive test suite (`ResumeAIParsingTestCase`) covers primary model success, 503 fallback execution, 404 non-retry, 401 unauthenticated, 403 non-student, and throttle enforcement.

### Student AI Chat Assistant Subsystem
- **Dedicated `apps.assistant` App**: Built and registered the `apps.assistant` Django app with zero database models. Implements `POST /api/assistant/chat/` (`AssistantChatView`) gated strictly to authenticated students (`IsAuthenticated` + `IsStudentRole`).
- **Server-Side Context Construction & Privacy Isolation**: Built `backend/apps/assistant/context.py` which extracts and sanitizes the student's own profile (`get_student_profile_context`) and ranks top 8 open platform opportunities matching skill overlap, city match, and recency (`get_candidate_opportunities_context`). Strict privacy isolation prevents access to other students' profiles or contact info (`phone_number`/`whatsapp_number`).
- **Untrusted Input Defense & Throttling**: System instructions (`constants.py`) treat user chat history and DATA blocks as untrusted input with anti-prompt-injection rules. Protected with `StudentChatThrottle` (5 requests/minute per student).
- **Floating UI Widget**: Built `<AssistantWidget />` (`frontend/src/components/assistant/AssistantWidget.jsx`) featuring a responsive drawer widget, session history management, unread badge counter, privacy notices, quick-prompt pills, and robust error handling.

### UI/UX Polish, Navigation & Component Bug Fixes
- **Skills Expand/Collapse Toggle**: Added an interactive "Show all (N)" / "Show less" toggle in `ProfileOverviewTab.jsx` for tag lists (skills, languages) exceeding 12 items.
- **Resume View vs Download Split**: Refactored `ResumeCard.jsx` to separate inline viewing (`handleView` creating a Blob URL and opening `_blank`) from disk saving (`handleDownload` triggering an anchor file download).
- **Avatar Rendering in Navbar & Applicants View**: Rendered `user?.profile_picture` in `DashboardHeader.jsx` dropdown and updated `ApplicantAvatar` in `ApplicantsView.jsx` to safely resolve relative `/media/` paths by prefixing backend host (`http://127.0.0.1:8000`), resolving broken applicant profile picture displays.
- **Provider Profile Picture Upload Fix**: Updated `providerProfileService.js` to set `headers: { 'Content-Type': 'multipart/form-data' }` when uploading `FormData`, resolving HTTP 400 validation errors.
- **Provider Social Links Visibility**: Fixed social links rendering in `ProfileOverviewTab.jsx` to properly display populated provider `social_links`.
- **Sitewide Friendly Error Audit**: Exported `formatErrorResponse` in `authService.js` and integrated DRF error formatting across all authentication, profile, resume, and opportunity service methods to ensure raw Axios/HTTP error strings never reach the UI.

### Accounts Migration `0010_alter_adminactionlog_action_type`
- Applied migration `accounts.0010_alter_adminactionlog_action_type` adding `user_deleted` choice to `AdminActionLog.action_type`. Schema no-op migration preserving audit logging compatibility.

---

## 2. TECH STACK

### Backend
- **Framework & Core**: Django `6.0.8`, Django REST Framework `3.17.2`
- **AI & LLM Integration**: `google-genai` (`^1.0.0` - official Google Gemini SDK)
- **Document Processing**: `pypdf` (`^5.0.0` - PDF text extraction), `python-docx` (`^1.1.0` - Word DOCX parsing)
- **Database Client**: PostgreSQL client via `psycopg2-binary` `2.9.12`
- **PostgreSQL Utilities**: `django.contrib.postgres.fields.ArrayField`
- **Authentication & Security**:
  - `djangorestframework_simplejwt` (`5.5.1`): JWT Access/Refresh tokens & token blacklisting
  - `firebase-admin` (`7.5.0`): Server-side Firebase Phone Auth ID Token verification
  - `google-auth` (`2.56.3`): Server-side Google OAuth ID Token verification
  - `pyotp` (`2.10.0`): Base32 TOTP calculation for Admin MFA
  - `qrcode` (`8.2`): QR code image generation for TOTP authenticator pairing
  - `pillow` (`12.3.0`): Image file processing & validation
  - `PyJWT` (`2.13.0`): Low-level JWT operations
- **Task Queue & Caching**:
  - `celery` (`5.6.3`): Distributed async task queue
  - `redis` (`8.1.0`): Celery message broker and result backend client
  - `django-celery-beat` (`2.9.0`): Database-backed periodic task scheduler
- **API Documentation & Utilities**:
  - `drf-spectacular` (`0.30.0`): OpenAPI 3 schema generator & Swagger UI
  - `django-cors-headers` (`4.9.0`): Cross-Origin Resource Sharing middleware
  - `python-dotenv` (`1.2.2`): Environment variable loader
  - `requests` (`2.34.2`): HTTP client library

### Frontend
- **Framework & Build**: React `19.2.8`, Vite `8.2.0`, `@vitejs/plugin-react` `6.0.4`
- **Routing**: React Router DOM `7.18.2`
- **Styling**: Tailwind CSS v4 (`tailwindcss` `^4.3.3`), `@tailwindcss/vite` (`^4.3.3`), Vanilla CSS design tokens
- **HTTP Client**: `axios` (`1.19.0`) with request/response JWT interceptors
- **Authentication SDKs**:
  - `@react-oauth/google` (`0.13.5`): Google OAuth client integration
  - `firebase` (`12.17.1`): Firebase Auth client SDK for Phone OTP verification
  - `react-google-recaptcha-v3` (`1.11.0`): Invisible reCAPTCHA v3 SDK

---

## 3. PROJECT STRUCTURE

```
NextGig/
├── .env                              # Docker Compose environment variables
├── .gitignore                        # Git exclusion rules
├── docker-compose.yml                # Multi-container service definitions (5 services)
├── PROJECT_STATUS.md                 # Master project documentation
│
├── backend/
│   ├── Dockerfile                    # Production/Dev Docker definition (python:3.12-slim)
│   ├── manage.py                     # Django management script
│   ├── requirements.txt              # Backend Python dependencies
│   │
│   ├── config/                       # Core Django Configuration
│   │   ├── celery.py                 # Celery app initialization & broker setup
│   │   ├── settings.py               # Settings, DB, JWT, Celery, REST_FRAMEWORK configs
│   │   └── urls.py                   # Global URL routing (accounts, opportunities, notifications, assistant, admin)
│   │
│   ├── apps/
│   │   ├── common/                   # Shared Platform Utilities
│   │   │   ├── __init__.py
│   │   │   └── gemini_client.py      # Hardened Google Gemini API client (timeout, retry, fallback, status classification)
│   │   │
│   │   ├── assistant/                # AI Chat Assistant Django App
│   │   │   ├── __init__.py
│   │   │   ├── admin.py
│   │   │   ├── apps.py
│   │   │   ├── constants.py          # System instructions & platform fact sheet
│   │   │   ├── context.py            # Student profile & candidate opportunity context builders
│   │   │   ├── serializers.py        # Chat request & response serializers
│   │   │   ├── tests.py              # Assistant unit tests
│   │   │   ├── throttling.py         # StudentChatThrottle (5/min)
│   │   │   ├── urls.py               # Assistant REST API endpoint router (/api/assistant/chat/)
│   │   │   └── views.py              # AssistantChatView
│   │   │
│   │   ├── accounts/                 # Custom User & Profile Management
│   │   │   ├── admin.py              # Django Admin interface
│   │   │   ├── admin_views.py        # Dedicated Admin API endpoints & action log handlers
│   │   │   ├── models.py             # CustomUser, PhoneOTP, AdminMFA, Invitation, StudentProfile, ProviderProfile, Resume, AdminActionLog
│   │   │   ├── permissions.py        # IsVerifiedUser, IsStudentRole, IsProviderUser, IsAdminRole
│   │   │   ├── serializers.py        # User, StudentProfile, ProviderProfile, Resume serializers
│   │   │   ├── tests.py              # Auth, profile, resume, AI parse, and permission test suite
│   │   │   ├── urls.py               # Accounts REST API endpoint router
│   │   │   └── views.py              # Auth, profile, resume, AI parse, and MFA API views
│   │   │
│   │   ├── opportunities/            # Opportunities, Bookmarking & Applications
│   │   │   ├── admin.py
│   │   │   ├── models.py             # Opportunity, SavedOpportunity, Application, RecommendedOpportunity
│   │   │   ├── serializers.py        # Opportunity, SavedOpportunity, Application serializers
│   │   │   ├── views.py              # Opportunity, bookmarking, apply, applicant list views
│   │   │
│   │   └── notifications/            # Database-Backed In-App Notifications
│   │       ├── models.py             # Notification model & NotificationType choices
│   │       ├── views.py              # NotificationListView, NotificationMarkReadView
│   │
└── frontend/
    ├── src/
        ├── App.jsx                   # React Router route definitions & AuthProvider context
        ├── services/
        │   ├── api.js                # Axios instance with JWT request/response interceptors
        │   ├── authService.js        # Auth API calls & formatErrorResponse utility
        │   ├── assistantService.js   # AI Assistant API calls
        │   ├── opportunityService.js # Opportunity, bookmarking, and application API calls
        │   ├── studentProfileService.js
        │   └── providerProfileService.js
        │
        ├── components/
        │   ├── assistant/            # AssistantWidget.jsx (Floating AI chat drawer)
        │   ├── dashboard/            # Navbar, Sidebar, DashboardHeader
        │   ├── provider/             # ApplicantsView.jsx (with ApplicantAvatar relative URL fix)
        │   └── profile/              # ProfileShell, ProfileHeader, ProfileTabs,
        │                             # ProfileOverviewTab (with tags toggle),
        │                             # ResumeCard (with AI review modal & View/Download split)
```

---

## 4. AUTHENTICATION AUDIT

| Mechanism | Client-Side Implementation | Server-Side Validation | Status | Security Controls |
|---|---|---|---|---|
| **Email / Password** | `Login.jsx`, `Register.jsx` | `StudentRegistrationSerializer`, DRF `TokenObtainPairView` | **Audited & Active** | Anti-enumeration responses (`"Invalid email or password."`), `PasswordComplexityValidator`, password reset token expiration, `{ replace: true }` history stack protection. |
| **Firebase Phone Auth** | `Login.jsx` (`signInWithPhoneNumber`, `RecaptchaVerifier`) | `apps/accounts/firebase.py` (`firebase_admin.auth.verify_id_token`) | **Audited & Active** | Token expiration check, issuer verification, automatic user lookup/creation via verified phone number. |
| **Google OAuth** | `@react-oauth/google` | `apps/accounts/google_auth.py` (`google.oauth2.id_token.verify_oauth2_token`) | **Audited & Active** | Google Client ID verification, email verification enforcement, user auto-creation. |
| **Admin MFA (TOTP)** | `AdminMFASetup.jsx`, `AdminMFAChallenge.jsx` | `apps/accounts/models.py` (`AdminMFA`), `PyOTP` | **Audited & Active** | Ephemeral 5-minute pre-auth token (`type='mfa_pending'`), Base32 TOTP verification, emergency recovery codes. |
| **reCAPTCHA v3** | `react-google-recaptcha-v3` | Google reCAPTCHA siteverify API | **Audited & Active** | Minimum score threshold `0.5` enforced across Registration, Login, and Password Reset endpoints. |
| **Session Protection** | `api.js` (Axios Interceptors) | `NoCacheHeadersMiddleware` | **Audited & Active** | `Cache-Control: no-store, no-cache, must-revalidate` header injected on all `/api/` endpoints. Automatic token refresh on 401 response. |

---

## 5. DATABASE MODELS / SCHEMA

### `AdminActionLog` (table: `admin_action_logs`)
- `id`: BigAutoField (Primary Key)
- `admin`: ForeignKey (`CustomUser`, on_delete=CASCADE, related_name=`admin_actions`)
- `action_type`: CharField (max_length=50, choices: `provider_verified`, `provider_unverified`, `user_activated`, `user_deactivated`, `opportunity_force_closed`, `opportunity_reopened`, `opportunity_deleted`, `user_deleted`)
- `target_description`: CharField (max_length=255)
- `timestamp`: DateTimeField (auto_now_add=True, db_index=True)

---

## 6. API ENDPOINTS

### Accounts App (`/api/accounts/`)
- `POST /api/accounts/register/` - Register new user (accepts `role`: `"student"` or `"provider"`)
- `POST /api/accounts/login/` - Email/password login (returns JWT pair or MFA pre-auth token)
- `GET /api/accounts/profile/` - Retrieve authenticated user profile
- `PATCH / PUT /api/accounts/profile/` - Update user base profile & `StudentProfile`
- `POST /api/accounts/profile/resume/upload/` - Upload student resume (PDF/DOCX, max 5MB, rate limited)
- `POST /api/accounts/profile/resume/parse-ai/` - Extract resume text & generate AI profile suggestions (`IsStudentRole`, rate limit 5/hour)
- `GET /api/accounts/profile/resume/download/` - Download owner student resume
- `DELETE /api/accounts/profile/resume/` - Delete student resume

### AI Assistant App (`/api/assistant/`)
- `POST /api/assistant/chat/` - Student AI platform assistant chat endpoint (`IsAuthenticated` + `IsStudentRole`, rate limit 5/min)

---

## 7. FEATURES STATUS

| Feature | Backend Status | Frontend Status | Verification / Notes |
|---|---|---|---|
| **Student Registration & Auth** | **Done** | **Done** | Full email, Google OAuth, Firebase phone login active with `{ replace: true }` history stack handling. |
| **Provider Registration & Auth** | **Done** | **Done** | Role option `"provider"` accepted during registration, provider dashboard active. |
| **Student Profile Management** | **Done** | **Done** | Complete tabbed UI (`ProfileShell`), profile picture upload, qualification, skills, languages, bio, privacy flags. |
| **Provider Profile Management** | **Done** | **Done** | Organization profile details, contact person, social links, privacy toggles, admin verification flag. |
| **Opportunity CRUD** | **Done** | **Done** | Full REST endpoints, category choices (including `"full_time"`), status management, `PostOpportunity.jsx` form. |
| **Saved Items (Bookmarking)** | **Done** | **Done** | `SavedOpportunity` model, idempotent save/unsave, user isolation, `SavedItemsTab` UI. |
| **Application Submission & Tracking** | **Done** | **Done** | Cover note submission, deadline enforcement, rate limits, status transition workflow (`applied` → `accepted`/`rejected`/`withdrawn`). |
| **Received Applicants (Provider)** | **Done** | **Done** | Combined `GET /api/applications/received/` overview endpoint, `ApplicantsView.jsx` card layout with applicant resume downloads and relative URL image resolution. |
| **Student Resume Upload** | **Done** | **Done** | OneToOne `Resume` model, magic-bytes PDF/DOCX validation, protected download endpoints, `<ResumeCard />` UI. |
| **AI Resume Parsing** | **Done** | **Done** | `ResumeParseView` (`apps/accounts/views.py`) using `gemini_client.py` (`gemini-3.1-flash-lite` primary, `gemini-3-flash-preview` fallback), suggestion review modal, skill merge-not-replace logic, 5/hour throttle. |
| **AI Chat Assistant** | **Done** | **Done** | `AssistantChatView` (`apps/assistant/views.py`), server-side student context & top 8 opportunity ranking, untrusted input defense, 5/min throttle, `<AssistantWidget />` drawer UI. |
| **In-App Notifications** | **Done** | **Done** | `Notification` model, REST endpoints, header bell icon badge dropdown with real-time unread counter. |
| **Admin Panel & Moderation** | **Done** | **Done** | Dedicated `AdminProfileView`, user activation/deactivation, provider verification, action logging, TOTP MFA UI. |
| **Verified Provider Badge Display** | **Done** | **Done** | `PosterPublicSerializer` `is_verified` field and `OpportunityDetail.jsx` render "Verified Provider" checkmark badge on opportunity detail page only. |
| **Opportunity Recommendations** | **Done** | **Done** | `RecommendedOpportunity` model, Celery Beat task (6:00 AM daily cron), `GET /api/opportunities/recommended/` endpoint, and student digest notification. |

---

## 8. UI/UX STATE

### Floating AI Chat Widget & Resume Parsing Review
- **AI Assistant Widget**: Renders as a floating button in the bottom-right corner for student users. Clicking opens a drawer UI (`AssistantWidget.jsx`) with quick prompt buttons, privacy notices, session history, markdown response formatting, and clear chat controls.
- **AI Resume Suggestions Modal**: Opened inside `ResumeCard.jsx` upon successful `POST /api/accounts/profile/resume/parse-ai/` response. Allows students to preview, add, or remove suggested skills, edit qualification and institution fields, and explicitly confirm before saving to their profile.

---

## 9. TOOLING & TEST SUITE

### Unit Test Suite Execution
- **Test Command**: `venv/Scripts/python.exe manage.py test apps.accounts.tests apps.accounts.test_admin_panel apps.opportunities.tests apps.notifications.tests apps.assistant.tests`
- **Status**: All tests passing cleanly (144+ unit tests passing).
- **Coverage**: Auth, profile, resume, AI resume parsing (`ResumeAIParsingTestCase`), AI assistant (`AssistantTestCase`), provider verification, opportunity CRUD, applications, notifications, and administrative actions.

---

## 10. KNOWN ISSUES / OUTSTANDING ITEMS

1. **Firebase SMS GCP Billing Account Block**: Real SMS delivery on Firebase blocked by Google Cloud billing error `OR_BACR2`. Phone Auth sandbox mode functions properly.
2. **Firebase Web API Key Restrictions**: Web API key in `firebase-credentials.json` lacks HTTP referrer restrictions in GCP Console.
3. **Navbar User Avatar Image URL Resolution**: `DashboardHeader.jsx` passes `user.profile_picture` directly to `<img src={user.profile_picture} />`. When `user.profile_picture` is a relative path (e.g. `/media/profile_pics/...`), it relies on browser host resolution or triggers the `onError` fallback to the initial letter.
4. **Assistant Output Contract**: `constants.py` system instruction instructs the model to return JSON `{"reply": "<text>", "opportunity_ids": [...]}` and limit replies to under 150 words. Wording tweak confirmed active.
5. **Hardcoded API Base URL Technical Debt**: `authService.js` contains a hardcoded API base URL (`http://127.0.0.1:8000/api`) instead of drawing from an environment variable (`import.meta.env.VITE_API_BASE_URL`).
6. **JWT Storage in localStorage Technical Debt**: JWT access and refresh tokens are stored in `localStorage` rather than HTTP-only secure cookies.
