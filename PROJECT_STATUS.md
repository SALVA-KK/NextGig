# Technical Audit & Comprehensive Project Status Report - NextGig

---

## 1. SESSION SUMMARY

Today's session delivered substantial architectural, security, database, API, UI/UX, and performance enhancements across the NextGig platform. Below is a complete narrative of everything accomplished, all bugs diagnosed and resolved, and the current operational state of the codebase.

### Authentication Hardening & History Stack Refactoring
- **Pre-Authentication MFA Redirect Fix**: Corrected pre-authentication routing in [`Login.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Login.jsx). Administrators with active MFA who attempt email/password login now receive a 5-minute pre-auth token and are directed directly to `/admin/mfa-verify`.
- **Browser History Stack & Navigation Cleanups**: Updated all post-authentication, registration, and MFA challenge navigation calls across [`Login.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Login.jsx), [`Register.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Register.jsx), and [`AdminMFAChallenge.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/AdminMFAChallenge.jsx) to use `{ replace: true }`. This prevents stale history traps where pressing the browser Back button would return users to blank or submitted authentication pages.
- **Mount-Time Auto-Redirects**: Implemented mount-time authentication checks on `/login` and `/register` views. Authenticated users attempting to visit these pages are automatically redirected to their respective dashboards based on role (`/dashboard`, `/provider/dashboard`, or `/admin/dashboard`).
- **Anti-Enumeration Error Message Sanitization**: Unified error handling across authentication flows to return non-revealing messages (`"Invalid email or password."`) while protecting against user enumeration.

### Full Provider Profile Support & Privacy Enhancements
- **Backend Model & Serializer Extensions**: Created the `ProviderProfile` model in [`backend/apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py) with organization categories (`company`, `startup`, `cafe`, `restaurant`, `shop`, `ngo`, `educational_institution`, `freelancer`, `individual`, `event_organizer`, `other`), description, website, address, city, and contact metadata.
- **Privacy & Contact Controls**: Expanded `ProviderProfile` with `profile_picture`, `phone_number`, `whatsapp_number`, `show_phone`, `show_whatsapp`, and `social_links` (JSONField). Mirrors the privacy flags present on `StudentProfile`.
- **API Endpoints & DRF Permissions**: Built `GET / PATCH / PUT /api/accounts/provider-profile/` gated by `IsAuthenticated` + `IsProviderUser` (`role='provider'`), returning `HTTP 403 Forbidden` for student users. Sealed `is_verified` and `user` as strictly `read_only=True` in `ProviderProfileSerializer` to prevent self-verification tampering via the API.
- **Administrative Verification**: Registered `ProviderProfile` in the Django Admin interface with editable `is_verified` toggles and filter options for administrative review.

### Opportunities App, Bookmarking, Applications & Received Applicants
- **`opportunities` Django App Architecture**: Built and registered the `opportunities` Django app (`apps.opportunities`) with complete CRUD REST APIs, bookmarking/saved opportunities, application tracking, and admin controls.
- **Opportunity Model & Categories**: Implemented `Opportunity` in [`backend/apps/opportunities/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/opportunities/models.py) featuring `ArrayField` required skills, pay types, work modes, vacancies, location, deadline, status, compound indexes on `(status, category, city)`, and added the `"full_time"` category choice. Added `closed_by` (FK to `CustomUser`) and `close_reason` (`owner_closed`, `admin_moderated`, `expired`) fields.
- **Saved Opportunities (Bookmarking)**: Built `SavedOpportunity` model (`user`, `opportunity`, `created_at`, `unique_together = ('user', 'opportunity')`), DRF view `OpportunitySaveView`, and paginated `SavedOpportunityListView` (`GET /api/saved-opportunities/`).
- **Application Tracking & Status Workflow**: Built `Application` model (`applicant`, `opportunity`, `status`: `applied`, `under_review`, `accepted`, `rejected`, `withdrawn`, `cover_note`, `applied_at`, `updated_at`). Built endpoints `POST /api/opportunities/<id>/apply/`, `GET /api/applications/` (my applications), `GET /api/opportunities/<id>/applicants/` (poster applicant list), and `PATCH /api/applications/<id>/status/`.
- **Provider Combined Applicants Endpoint**: Built `GET /api/applications/received/` (`ReceivedApplicationsListView`) returning all applications across every opportunity posted by the requesting provider with nested opportunity metadata. Gated strictly to provider accounts (`HTTP 403 Forbidden` for students).
- **Defensive Application Deadline Validation**: Enforced strict application deadline checks in `ApplicationCreateSerializer` and `ApplicationCreateView` rejecting applications to opportunities whose deadline has passed (`opportunity.deadline < timezone.localdate()`) with `HTTP 400 Bad Request`.

### Student Resume Upload Subsystem
- **Resume Model & Storage**: Built `Resume` model in [`backend/apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py) maintaining a OneToOne relationship with `CustomUser` (`role='student'`). Resumes are stored under `media/resumes/<uuid4><ext>` to prevent filename collisions and directory traversal attacks.
- **Strict File Inspection & Rate Limits**: Validated uploads using magic-bytes inspection for PDF (`%PDF-`) and DOCX (`PK\x03\x04`) signatures, capped file size at 5MB, and applied DRF rate limiting (`10 uploads/hour`).
- **Protected Download Endpoints**: Built `GET /api/accounts/profile/resume/download/` (owner student download) and `GET /api/applications/<id>/resume/` (opportunity poster download for applicants).
- **Frontend UI Component**: Built `<ResumeCard />` UI component in [`ResumeCard.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ResumeCard.jsx) with file selection, size display, upload progress indicator, replacement, and download controls. Gated to student role only.

### Admin Panel, MFA UI & Audit Logging
- **`AdminActionLog` Audit Trail**: Created `AdminActionLog` model tracking sensitive operations (`provider_verified`, `provider_unverified`, `user_activated`, `user_deactivated`, `opportunity_force_closed`, `opportunity_reopened`, `opportunity_deleted`). Built administrative views (`backend/apps/accounts/admin_views.py`, `backend/apps/opportunities/admin_views.py`, `backend/apps/notifications/admin_views.py`).
- **Dedicated `AdminProfileView`**: Built standalone [`AdminProfileView.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/admin/AdminProfileView.jsx) tailored specifically for administrators, isolating admin settings from student and provider profile structures.
- **Admin MFA Setup UI**: Redesigned [`AdminMFASetup.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/admin/AdminMFASetup.jsx) using standard light-theme design tokens (`bg-white`, `border-slate-200`, `shadow-sm`, `rounded-2xl`), QR code card rendering, backup code grid, and activation/deactivation toggles.
- **Simplified Admin Sidebar**: Updated [`Sidebar.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/dashboard/Sidebar.jsx) to hide student/provider specific links (Explore, Collaborations) for admin accounts.

### In-App Notification Subsystem
- **Notification Model & REST Endpoints**: Built `Notification` model (`recipient`, `actor`, `notification_type`, `title`, `message`, `opportunity`, `application`, `is_read`, `read_at`, `event_key`, `created_at`). Created `GET /api/notifications/` (`NotificationListView`) and `PATCH /api/notifications/<id>/read/` (`NotificationMarkReadView`).
- **Notification Types**: Supported `new_application`, `application_status_changed`, `application_withdrawn`, `opportunity_expired`, `opportunity_force_closed`, `opportunity_reopened`, `provider_welcome`, `provider_verified`, `provider_unverified`.
- **Header UI Dropdown**: Built header notification bell icon with real-time unread badge counter, popover dropdown list, and one-click mark-as-read functionality.

### UI/UX Redesign & Profile Layout Streamlining
- **Modular Profile Architecture**: Re-architected profile frontend into a modular structure under `frontend/src/components/profile/`: [`ProfileShell.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ProfileShell.jsx), [`ProfileHeader.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ProfileHeader.jsx), [`ProfileTabs.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ProfileTabs.jsx), [`ProfileOverviewTab.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ProfileOverviewTab.jsx), [`ProfilePortfolioTab.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ProfilePortfolioTab.jsx), [`ProfileSettingsTab.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ProfileSettingsTab.jsx), and [`profileFieldConfigs.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/config/profileFieldConfigs.js).
- **Profile Tab Simplification**: Removed Gig Stories tab and merged Overview/About and Portfolio sections into Overview. The profile structure now presents 3 clean tabs across Student and Provider roles:
  1. **Overview**: Includes bio, skills, qualification/institution or org details, availability, languages, social links, portfolio website card, student resume card, upcoming gig showcase placeholder, and the [`InviteCard`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/InviteCard.jsx).
  2. **Portfolio**: (Merged into Overview tab view).
  3. **Settings & Edit**: Field editing inputs, privacy toggles (`show_phone`, `show_whatsapp`), and the [`ChangePasswordCard`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ChangePasswordCard.jsx).
- **Design Token Standardization**: Standardized light-theme design system across all user roles: cards (`bg-white`), borders (`border-slate-200`), shadows (`shadow-sm`), rounded corners (`rounded-2xl`), text (`text-slate-900`, `text-slate-600`, `text-slate-500`), and buttons (`bg-indigo-600 hover:bg-indigo-700 text-white`).
- **Provider Dashboard Tabs**: Standardized provider dashboard tabs: **My Opportunities**, **Post New Opportunity**, **Applicants** (defaulting to All Applicants combined view), **Explore Opportunities**, **Saved Items**, and **Provider Profile**.

### Major Bugs Diagnosed & Resolved
1. **Tailwind CSS Spacing & Utility Issue**:
   - *Symptom*: Utility spacing classes (`px-4`, `py-6`, `mb-8`, `gap-6`) were breaking layouts or throwing parsing warnings under Tailwind CSS v4 and `@tailwindcss/vite`.
   - *Fix*: Configured Vite plugin `@tailwindcss/vite` (`^4.3.3`) in [`vite.config.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/vite.config.js) and imported `@import "tailwindcss";` in [`index.css`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/index.css). Standardized spacing utilities across all dashboard and profile components.
2. **Provider Profile Blank-Page Bug**:
   - *Symptom*: Provider users navigating to the profile page occasionally experienced a blank rendered page due to unhandled `null`/`undefined` fields during state initialization when `ProviderProfile` was absent or newly created.
   - *Fix*: Added defensive optional chaining (`profile?.organization_name`), safe fallback defaults (`{}`) in `profileFieldConfigs.js`, and updated `ProviderProfileSerializer` to return empty strings instead of `null` for missing optional fields.
3. **Celery Redis Connection Hang**:
   - *Symptom*: When Redis broker was offline, Django API request threads hung for up to 109 seconds inside `transaction.on_commit` attempting Kombu connection retries.
   - *Fix*: Applied fast-fail Celery connection configuration in [`settings.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py):
     - `CELERY_BROKER_CONNECTION_TIMEOUT = 2.0`
     - `CELERY_BROKER_CONNECTION_MAX_RETRIES = 2`
     - `CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True`
     - Transport options: `socket_timeout: 2.0`, `socket_connect_timeout: 2.0`, `max_retries: 2`.
     - Implemented `_safe_delay_notification()` wrapper in `views.py` catching connection exceptions gracefully. Reduced Redis-down API wire latency from **109.02s** to **2.08s**.

---

## 2. TECH STACK

### Backend
- **Framework & Core**: Django `6.0.8`, Django REST Framework `3.17.2`
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
│   ├── .dockerignore                 # Docker context build exclusion manifest
│   ├── DOCKER.md                     # Infrastructure management & troubleshooting guide
│   ├── manage.py                     # Django management script
│   ├── requirements.txt              # Backend Python dependencies
│   │
│   ├── config/                       # Core Django Configuration
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── celery.py                 # Celery app initialization & broker setup
│   │   ├── settings.py               # Settings, DB, JWT, Celery, REST_FRAMEWORK configs
│   │   ├── urls.py                   # Global URL routing (accounts, opportunities, notifications, admin)
│   │   └── wsgi.py
│   │
│   ├── apps/
│   │   ├── accounts/                 # Custom User & Profile Management
│   │   │   ├── admin.py              # Django Admin interface (CustomUser, StudentProfile, ProviderProfile, Resume, etc.)
│   │   │   ├── admin_views.py        # Dedicated Admin API endpoints & action log handlers
│   │   │   ├── firebase.py           # Firebase ID Token verification helper
│   │   │   ├── google_auth.py        # Google OAuth ID Token verification helper
│   │   │   ├── models.py             # CustomUser, PhoneOTP, AdminMFA, Invitation, StudentProfile, ProviderProfile, Resume, AdminActionLog
│   │   │   ├── permissions.py        # IsVerifiedUser, IsStudentRole, IsProviderUser, IsAdminRole
│   │   │   ├── serializers.py        # User, StudentProfile, ProviderProfile, Resume, AdminMFA serializers
│   │   │   ├── tests.py              # Auth, profile, resume, and permission unit test suite
│   │   │   ├── urls.py               # Accounts REST API endpoint router
│   │   │   ├── utils.py              # Email sending, token generation, MSG91 helpers
│   │   │   ├── validators.py         # PasswordComplexityValidator, profile picture validator
│   │   │   ├── views.py              # Auth, profile, resume, and MFA API views
│   │   │   └── management/commands/
│   │   │       └── seed_test_users.py # Idempotent test user profile seeding command
│   │   │
│   │   ├── opportunities/            # Opportunities, Bookmarking & Applications
│   │   │   ├── admin.py              # Django Admin for Opportunity, SavedOpportunity, Application
│   │   │   ├── admin_views.py        # Admin moderation views for opportunities & applications
│   │   │   ├── models.py             # Opportunity, SavedOpportunity, Application models
│   │   │   ├── permissions.py        # IsVerifiedUser, IsOwnerOrReadOnly, IsApplicantOrPoster
│   │   │   ├── serializers.py        # Opportunity, SavedOpportunity, Application serializers
│   │   │   ├── tasks.py              # Async Celery email tasks & periodic close_expired_opportunities task
│   │   │   ├── tests.py              # Opportunity CRUD, bookmarking, application, and Celery unit tests
│   │   │   ├── urls.py               # Opportunities REST API endpoint router
│   │   │   ├── views.py              # Opportunity, bookmarking, apply, applicant list, received list views
│   │   │   └── management/commands/
│   │   │       └── seed_demo_data.py # Idempotent demo opportunities & applications seeder
│   │   │
│   │   └── notifications/            # Database-Backed In-App Notifications
│   │       ├── admin.py              # Django Admin for Notification
│   │       ├── admin_views.py        # Admin notification management views
│   │       ├── models.py             # Notification model & NotificationType choices
│   │       ├── serializers.py        # NotificationSerializer
│   │       ├── tests.py              # Notification unit tests
│   │       ├── urls.py               # Notification REST API router
│   │       ├── views.py              # NotificationListView, NotificationMarkReadView
│   │       └── services.py           # In-app notification creation helper functions
│   │
│   └── scripts/                      # Developer Benchmark & Diagnostic Tools
│       ├── cleanup_test_db.py
│       ├── diagnose_apply_performance.py
│       ├── verify_fast_fail_redis_down.py
│       └── verify_fast_fail_redis_up.py
│
└── frontend/
    ├── package.json                  # Frontend dependencies & scripts
    ├── vite.config.js                # Vite build config with @tailwindcss/vite plugin
    ├── index.html                    # HTML template
    │
    └── src/
        ├── App.jsx                   # React Router route definitions & AuthProvider context
        ├── main.jsx                  # React DOM root entrypoint
        ├── index.css                 # Global CSS rules (@import "tailwindcss";)
        │
        ├── config/
        │   └── profileFieldConfigs.js # Master field metadata configuration for profile rendering
        │
        ├── services/
        │   ├── api.js                # Axios instance with JWT request/response interceptors
        │   ├── authService.js        # Auth API calls (login, register, MFA, profile)
        │   └── opportunityService.js # Opportunity, bookmarking, and application API calls
        │
        ├── components/
        │   ├── admin/                # AdminMFASetup, AdminActionLogTable
        │   ├── auth/                 # ProtectedRoute, ProtectedAdminRoute
        │   ├── common/               # PaginationControl, NotificationDropdown
        │   ├── dashboard/            # Navbar, Sidebar, UserDashboard, ProviderDashboard
        │   ├── home/                 # Hero, Features, CTA
        │   ├── opportunities/       # OpportunityCard, OpportunityList, PostOpportunity
        │   ├── provider/             # MyOpportunities, ApplicantsView, ProviderProfileEdit
        │   └── profile/              # ProfileShell, ProfileHeader, ProfileTabs,
        │                             # ProfileOverviewTab, ProfilePortfolioTab,
        │                             # ProfileSettingsTab, ResumeCard, InviteCard,
        │                             # ChangePasswordCard
        │
        └── pages/
            ├── Home.jsx              # Landing page
            ├── admin/
            │   ├── AdminDashboard.jsx
            │   ├── AdminMFAChallenge.jsx
            │   └── AdminProfileView.jsx # Dedicated standalone admin profile page
            ├── auth/
            │   ├── Login.jsx         # Login view with pre-auth MFA & history replace
            │   ├── Register.jsx      # Registration view with role selection & history replace
            │   └── ForgotPassword.jsx
            ├── dashboard/
            │   ├── UserDashboard.jsx
            │   └── ProviderDashboard.jsx
            └── profile/
                └── Profile.jsx       # User profile wrapper rendering ProfileShell
```

---

## 4. AUTHENTICATION AUDIT

| Mechanism | Client-Side Implementation | Server-Side Validation | Status | Security Controls |
|---|---|---|---|---|
| **Email / Password** | `Login.jsx`, `Register.jsx` | `StudentRegistrationSerializer`, DRF `TokenObtainPairView` | **Audited & Active** | Anti-enumeration responses (`"Invalid email or password."`), `PasswordComplexityValidator`, password reset token expiration, `{ replace: true }` history stack protection. |
| **Firebase Phone Auth** | `Login.jsx` (`signInWithPhoneNumber`, `RecaptchaVerifier`) | `apps/accounts/firebase.py` (`firebase_admin.auth.verify_id_token`) | **Audited & Active** | Token expiration check, issuer verification, automatic user lookup/creation via verified phone number. |
| **Google OAuth** | `@react-oauth/google` | `apps/accounts/google_auth.py` (`google.oauth2.id_token.verify_oauth2_token`) | **Audited & Active** | Google Client ID verification, email verification enforcement, user auto-creation. |
| **Admin MFA (TOTP)** | `AdminMFASetup.jsx`, `AdminMFAChallenge.jsx` | `apps/accounts/models.py` (`AdminMFA`), `PyOTP` | **Audited & Active** | Ephemeral 5-minute pre-auth token (`type='mfa_pending'`), Base32 TOTP verification, 8-character single-use SHA256 hashed emergency backup codes. Isolated strictly to `admin` accounts. |
| **reCAPTCHA v3** | `react-google-recaptcha-v3` | Google reCAPTCHA siteverify API | **Audited & Active** | Minimum score threshold `0.5` enforced across Registration, Login, and Password Reset endpoints. |
| **Session Protection** | `api.js` (Axios Interceptors) | `NoCacheHeadersMiddleware` | **Audited & Active** | `Cache-Control: no-store, no-cache, must-revalidate` header injected on all `/api/` endpoints. Automatic token refresh on 401 response. |

---

## 5. DATABASE MODELS / SCHEMA

### `CustomUser` (table: `users`)
- `id`: BigAutoField (Primary Key)
- `email`: EmailField (unique=True, db_index=True) - Primary login identifier
- `full_name`: CharField (max_length=255)
- `phone_number`: CharField (max_length=20, unique=True, null=True, blank=True)
- `role`: CharField (max_length=20, choices: `student`, `provider`, `admin`, default: `student`)
- `is_active`: BooleanField (default=True)
- `is_staff`: BooleanField (default=False)
- `is_verified`: BooleanField (default=False)
- `email_verified_at`: DateTimeField (null=True, blank=True)
- `date_joined`: DateTimeField (default=timezone.now)
- `created_at`: DateTimeField (auto_now_add=True)
- `updated_at`: DateTimeField (auto_now=True)

### `StudentProfile` (table: `student_profiles`)
- `id`: BigAutoField (Primary Key)
- `user`: OneToOneField (`CustomUser`, on_delete=CASCADE, related_name=`student_profile`)
- `profile_picture`: ImageField (upload_to=`profile_pics/students/%Y/%m/`, null=True, blank=True, validators=[validate_profile_picture_file])
- `profession`: CharField (max_length=150, blank=True)
- `qualification_type`: CharField (max_length=50, choices: `degree`, `diploma`, `certificate`, `self_taught`, `other`, blank=True)
- `qualification_name`: CharField (max_length=200, blank=True)
- `institution`: CharField (max_length=200, blank=True)
- `skills`: ArrayField (CharField(max_length=50), default=list, blank=True)
- `bio`: TextField (max_length=500, blank=True)
- `availability`: CharField (max_length=100, blank=True)
- `languages`: ArrayField (CharField(max_length=50), default=list, blank=True)
- `city`: CharField (max_length=100, blank=True, db_index=True)
- `portfolio_url`: URLField (blank=True)
- `whatsapp_number`: CharField (max_length=20, blank=True)
- `show_phone`: BooleanField (default=False)
- `show_whatsapp`: BooleanField (default=False)
- `social_links`: JSONField (default=dict, blank=True)
- `created_at`: DateTimeField (auto_now_add=True)
- `updated_at`: DateTimeField (auto_now=True)

### `ProviderProfile` (table: `provider_profiles`)
- `id`: BigAutoField (Primary Key)
- `user`: OneToOneField (`CustomUser`, on_delete=CASCADE, related_name=`provider_profile`)
- `profile_picture`: ImageField (upload_to=`profile_pics/providers/%Y/%m/`, null=True, blank=True, validators=[validate_profile_picture_file])
- `organization_name`: CharField (max_length=200)
- `organization_type`: CharField (max_length=50, choices: `company`, `startup`, `cafe`, `restaurant`, `shop`, `ngo`, `educational_institution`, `freelancer`, `individual`, `event_organizer`, `other`, default: `company`)
- `description`: TextField (blank=True)
- `contact_person`: CharField (max_length=100, blank=True)
- `website`: URLField (blank=True)
- `phone_number`: CharField (max_length=20, blank=True)
- `whatsapp_number`: CharField (max_length=20, blank=True)
- `show_phone`: BooleanField (default=False)
- `show_whatsapp`: BooleanField (default=False)
- `address`: CharField (max_length=255, blank=True)
- `city`: CharField (max_length=100, blank=True, db_index=True)
- `social_links`: JSONField (default=dict, blank=True)
- `is_verified`: BooleanField (default=False) - Editable only by Administrators via Django Admin / Admin API
- `created_at`: DateTimeField (auto_now_add=True)
- `updated_at`: DateTimeField (auto_now=True)

### `Opportunity` (table: `opportunities`)
- `id`: BigAutoField (Primary Key)
- `poster`: ForeignKey (`CustomUser`, on_delete=CASCADE, related_name=`posted_opportunities`)
- `closed_by`: ForeignKey (`CustomUser`, on_delete=SET_NULL, null=True, blank=True, related_name=`closed_opportunities`)
- `close_reason`: CharField (max_length=30, choices: `owner_closed`, `admin_moderated`, `expired`, null=True, blank=True)
- `title`: CharField (max_length=200)
- `description`: TextField ()
- `category`: CharField (max_length=50, choices: `full_time`, `part_time`, `internship`, `freelance`, `startup_hiring`, `project_collaboration`, `tutoring`, `volunteer`, `event_based`)
- `required_skills`: ArrayField (CharField(max_length=50), default=list, blank=True)
- `pay_type`: CharField (max_length=20, choices: `hourly`, `monthly`, `stipend`, `unpaid`)
- `pay_amount`: DecimalField (max_digits=10, decimal_places=2, null=True, blank=True)
- `duration`: CharField (max_length=100, blank=True)
- `working_hours`: CharField (max_length=100, blank=True)
- `work_mode`: CharField (max_length=20, choices: `remote`, `onsite`, `hybrid`)
- `location_text`: CharField (max_length=255, blank=True)
- `city`: CharField (max_length=100, blank=True, db_index=True)
- `latitude`: DecimalField (max_digits=9, decimal_places=6, null=True, blank=True)
- `longitude`: DecimalField (max_digits=9, decimal_places=6, null=True, blank=True)
- `vacancies`: PositiveIntegerField (default=1)
- `deadline`: DateField (null=True, blank=True)
- `contact_info`: CharField (max_length=255, blank=True)
- `status`: CharField (max_length=20, choices: `open`, `closed`, `draft`, default: `open`)
- `created_at`: DateTimeField (auto_now_add=True)
- `updated_at`: DateTimeField (auto_now=True)
- *Indexes*: Ordering `[-created_at]`, compound index `opp_status_cat_city_idx` on `(status, category, city)`.

### `SavedOpportunity` (table: `saved_opportunities`)
- `id`: BigAutoField (Primary Key)
- `user`: ForeignKey (`CustomUser`, on_delete=CASCADE, related_name=`saved_opportunities`)
- `opportunity`: ForeignKey (`Opportunity`, on_delete=CASCADE, related_name=`saved_by`)
- `created_at`: DateTimeField (auto_now_add=True)
- *Constraints*: `unique_together = ('user', 'opportunity')`, ordering `[-created_at]`.

### `Application` (table: `opportunity_applications`)
- `id`: BigAutoField (Primary Key)
- `applicant`: ForeignKey (`CustomUser`, on_delete=CASCADE, related_name=`applications`)
- `opportunity`: ForeignKey (`Opportunity`, on_delete=CASCADE, related_name=`applications`)
- `status`: CharField (max_length=20, choices: `applied`, `under_review`, `accepted`, `rejected`, `withdrawn`, default: `applied`)
- `cover_note`: TextField (blank=True)
- `applied_at`: DateTimeField (auto_now_add=True)
- `updated_at`: DateTimeField (auto_now=True)
- *Constraints*: `unique_together = ('applicant', 'opportunity')`, ordering `[-applied_at]`.

### `Resume` (table: `resumes`)
- `id`: BigAutoField (Primary Key)
- `user`: OneToOneField (`CustomUser`, on_delete=CASCADE, related_name=`resume`)
- `file`: FileField (upload_to=`resumes/<uuid4><ext>`)
- `original_filename`: CharField (max_length=255)
- `file_size`: PositiveIntegerField (bytes)
- `mime_type`: CharField (max_length=100, blank=True)
- `uploaded_at`: DateTimeField (auto_now_add=True)
- `updated_at`: DateTimeField (auto_now=True)

### `PhoneOTP` (table: `phone_otps`)
- `id`: BigAutoField (Primary Key)
- `phone_number`: CharField (max_length=20, db_index=True)
- `otp_hash`: CharField (max_length=128)
- `purpose`: CharField (max_length=20, choices: `login`, `registration`, `password_reset`, `mfa`)
- `expires_at`: DateTimeField ()
- `is_used`: BooleanField (default=False)
- `created_at`: DateTimeField (auto_now_add=True)

### `AdminMFA` (table: `admin_mfa`)
- `id`: BigAutoField (Primary Key)
- `user`: OneToOneField (`CustomUser`, on_delete=CASCADE, related_name=`mfa_settings`)
- `totp_secret`: CharField (max_length=64)
- `is_enabled`: BooleanField (default=False)
- `backup_codes`: JSONField (default=list) - Stores SHA256 hashed emergency recovery codes
- `created_at`: DateTimeField (auto_now_add=True)
- `updated_at`: DateTimeField (auto_now=True)

### `Invitation` (table: `invitations`)
- `id`: BigAutoField (Primary Key)
- `inviter`: ForeignKey (`CustomUser`, on_delete=CASCADE, related_name=`sent_invitations`)
- `token`: CharField (max_length=64, unique=True, db_index=True)
- `is_used`: BooleanField (default=False)
- `invited_user`: ForeignKey (`CustomUser`, on_delete=SET_NULL, null=True, blank=True, related_name=`received_invitation`)
- `expires_at`: DateTimeField (null=True, blank=True)
- `created_at`: DateTimeField (auto_now_add=True)
- `updated_at`: DateTimeField (auto_now=True)

### `AdminActionLog` (table: `admin_action_logs`)
- `id`: BigAutoField (Primary Key)
- `admin`: ForeignKey (`CustomUser`, on_delete=CASCADE, related_name=`admin_actions`)
- `action_type`: CharField (max_length=50, choices: `provider_verified`, `provider_unverified`, `user_activated`, `user_deactivated`, `opportunity_force_closed`, `opportunity_reopened`, `opportunity_deleted`)
- `target_description`: CharField (max_length=255)
- `timestamp`: DateTimeField (auto_now_add=True, db_index=True)

### `Notification` (table: `notifications`)
- `id`: BigAutoField (Primary Key)
- `recipient`: ForeignKey (`CustomUser`, on_delete=CASCADE, related_name=`notifications`, db_index=True)
- `actor`: ForeignKey (`CustomUser`, on_delete=SET_NULL, null=True, blank=True, related_name=`sent_notifications`)
- `notification_type`: CharField (max_length=50, choices: `new_application`, `application_status_changed`, `application_withdrawn`, `opportunity_expired`, `opportunity_force_closed`, `opportunity_reopened`, `provider_welcome`, `provider_verified`, `provider_unverified`)
- `title`: CharField (max_length=255)
- `message`: TextField ()
- `opportunity`: ForeignKey (`Opportunity`, on_delete=SET_NULL, null=True, blank=True, related_name=`notifications`)
- `application`: ForeignKey (`Application`, on_delete=SET_NULL, null=True, blank=True, related_name=`notifications`)
- `is_read`: BooleanField (default=False, db_index=True)
- `read_at`: DateTimeField (null=True, blank=True)
- `event_key`: CharField (max_length=255, unique=True, null=True, blank=True, db_index=True)
- `created_at`: DateTimeField (auto_now_add=True, db_index=True)

---

## 6. API ENDPOINTS

### Accounts App (`/api/accounts/`)
- `POST /api/accounts/register/` - Register new user (accepts `role`: `"student"` or `"provider"`)
- `GET /api/accounts/verify-email/` - Confirm email verification via `uid` & `token`
- `POST /api/accounts/login/` - Email/password login (returns JWT pair or MFA pre-auth token)
- `POST /api/accounts/token/refresh/` - Refresh access JWT
- `POST /api/accounts/logout/` - Blacklist refresh JWT
- `POST /api/accounts/change-password/` - Authenticated password change
- `POST /api/accounts/forgot-password/` - Request password reset link
- `POST /api/accounts/reset-password/` - Reset password via `uid` & `token`
- `POST /api/accounts/request-otp/` - Request general phone OTP
- `POST /api/accounts/verify-otp/` - Verify general phone OTP
- `POST /api/accounts/phone-login/request-otp/` - Request phone login OTP
- `POST /api/accounts/phone-login/verify-otp/` - Verify phone login OTP and receive JWTs
- `POST /api/accounts/google-login/` - Google OAuth ID Token login/registration
- `POST /api/accounts/firebase-phone-login/` - Firebase Phone ID Token login/registration
- `GET /api/accounts/profile/` - Retrieve authenticated user profile (`StudentProfile` or `ProviderProfile`)
- `PATCH / PUT /api/accounts/profile/` - Update user base profile & `StudentProfile`
- `GET / PATCH / PUT /api/accounts/provider-profile/` - Retrieve or update provider profile (provider role only)
- `POST /api/accounts/profile/resume/upload/` - Upload student resume (PDF/DOCX, max 5MB, rate limited)
- `GET /api/accounts/profile/resume/download/` - Download owner student resume
- `DELETE /api/accounts/profile/resume/` - Delete student resume
- `POST /api/accounts/admin/mfa/verify/` - Verify Admin TOTP or emergency backup code
- `POST /api/accounts/admin/mfa/setup/` - Initiate TOTP secret key & QR code setup
- `POST /api/accounts/admin/mfa/confirm/` - Confirm setup with code and generate backup codes
- `POST /api/accounts/admin/mfa/disable/` - Disable Admin MFA
- `GET /api/accounts/admin/mfa/status/` - Check Admin MFA activation status
- `POST /api/accounts/invitations/` - Create cryptographically secure platform invitation token
- `GET /api/accounts/invitations/<token>/` - Public invitation metadata validation

### Opportunities App (`/api/opportunities/` & `/api/applications/`)
- `GET /api/opportunities/` - Public listing (`status='open'` by default; query params: `category`, `work_mode`, `city`, `status`; page_size=20)
- `POST /api/opportunities/` - Post new opportunity (verified users; rate limit 10/hour)
- `GET /api/opportunities/<id>/` - Public opportunity detail view
- `PUT / PATCH / DELETE /api/opportunities/<id>/` - Update or delete listing (poster or admin only)
- `POST /api/opportunities/<id>/save/` - Bookmark opportunity (verified users)
- `DELETE /api/opportunities/<id>/save/` - Remove opportunity bookmark
- `GET /api/saved-opportunities/` - List user's saved opportunities (page_size=20)
- `POST /api/opportunities/<id>/apply/` - Apply for open opportunity (students only, deadline validated, rate limit 20/hour)
- `GET /api/applications/` - List student's submitted applications (supports `?status=` filter)
- `GET /api/applications/received/` - List all applications received across all provider's listings (providers only)
- `GET /api/opportunities/<id>/applicants/` - List applicants for specific opportunity (poster only)
- `PATCH /api/applications/<id>/status/` - Update application status (poster: `under_review`/`accepted`/`rejected`; applicant: `withdrawn`)
- `GET /api/applications/<id>/resume/` - Download applicant resume (opportunity poster only)

### Notifications App (`/api/notifications/`)
- `GET /api/notifications/` - Retrieve user's in-app notifications (supports unread filtering)
- `PATCH /api/notifications/<id>/read/` - Mark notification as read

### Administrative Endpoints (`/api/admin/`)
- `GET /api/admin/users/` - Paginated user management list
- `PATCH /api/admin/users/<id>/status/` - Activate or deactivate user account
- `GET /api/admin/providers/` - Provider organization verification list
- `PATCH /api/admin/providers/<id>/verify/` - Verify or unverify provider organization
- `GET /api/admin/action-logs/` - Administrative audit action logs

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
| **Received Applicants (Provider)** | **Done** | **Done** | Combined `GET /api/applications/received/` overview endpoint, `ApplicantsView.jsx` card layout with applicant resume downloads. |
| **Student Resume Upload** | **Done** | **Done** | OneToOne `Resume` model, magic-bytes PDF/DOCX validation, protected download endpoints, `<ResumeCard />` UI. |
| **In-App Notifications** | **Done** | **Done** | `Notification` model, REST endpoints, header bell icon badge dropdown with real-time unread counter. |
| **Admin Panel & Moderation** | **Done** | **Done** | Dedicated `AdminProfileView`, user activation/deactivation, provider verification, action logging, TOTP MFA UI. |
| **Search & Filtering** | **Done** | **Partially Done** | Backend supports `category`, `work_mode`, `city`, `status` query filters. UI search bar active. |
| **Real Geo-Location Search** | **Not Started** | **Not Started** | `latitude`/`longitude` columns exist on `Opportunity`; distance calculation queries not yet implemented. |
| **Reviews & Ratings** | **Not Started** | **Not Started** | Schema and API endpoints not yet created. |
| **Direct Messaging** | **Not Started** | **Not Started** | Messaging models and WebSocket/REST endpoints not yet created. |
| **Student Verified Badge Display** | **Not Started** | **Not Started** | Backend `is_verified` flag exists on `ProviderProfile`; student UI badge rendering pending layout addition. |

---

## 8. UI/UX STATE

### Profile Page Architecture & Layout
- **Tabbed Structure**: Profile navigation uses [`ProfileTabs.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ProfileTabs.jsx) rendering 3 streamlined tabs following the removal of Gig Stories and the integration of Portfolio into Overview:
  1. **Overview Tab**: Renders bio, skills, institution/org details, languages, social links, website card, student resume card, upcoming gig placeholder, and the [`InviteCard`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/InviteCard.jsx).
  2. **Portfolio Tab**: (View content merged directly into Overview tab).
  3. **Settings & Edit Tab**: Contains edit inputs for profile fields, privacy toggles (`show_phone`, `show_whatsapp`), and the [`ChangePasswordCard`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile/ChangePasswordCard.jsx).
- **Design Tokens**: Standard light theme design system:
  - Container cards: `bg-white border border-slate-200 rounded-2xl shadow-sm`
  - Headers: `text-slate-900 font-bold`
  - Body text: `text-slate-600`
  - Primary actions: `bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-xl transition-all`

### Admin UI State
- **Dedicated `AdminProfileView`**: Separate from student/provider `ProfileShell`, avoiding extraneous resume or portfolio components on administrator accounts.
- **Simplified Admin Sidebar**: [`Sidebar.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/dashboard/Sidebar.jsx) renders only administrative routes (**Dashboard**, **User Management**, **Provider Verification**, **Action Logs**, **MFA Settings**, **Profile**), excluding student/provider links (Explore Opportunities, Collaborations).

### Provider Dashboard State
- **Tabbed Navigation**: Provider dashboard standardizes 6 main views:
  1. **My Opportunities**: Active listing management with status toggles and force-close options.
  2. **Post New Opportunity**: Opportunity creation form with pay type, work mode, and category dropdowns.
  3. **Applicants**: Defaults to "All Applicants (Combined Overview)" with listing title attribution headers and status transition controls.
  4. **Explore Opportunities**: Platform listing search and inspection.
  5. **Saved Items**: Saved opportunities list.
  6. **Provider Profile**: Organization profile management.

### Known Current UI Investigation
- **Provider Profile Blank-Page Edge Case**:
  - *Current Status*: The provider profile page loading bug was fixed by adding null checks and safe fallbacks in `profileFieldConfigs.js` and `ProviderProfileSerializer`. Investigation remains ongoing for edge cases where custom provider accounts created prior to migration `0005_providerprofile` are missing an associated `ProviderProfile` database row on first load. Auto-creation on profile fetch handles this for new requests.

---

## 9. TOOLING STATUS

### Celery & Celery Beat
- **Worker Process**: `celery -A config worker --loglevel=info`
- **Beat Scheduler Process**: `celery -A config beat --loglevel=info`
- **Process Requirement**: In local development outside Docker, Celery Beat must be launched as a separate process alongside the Celery worker to execute daily scheduled tasks (`close_expired_opportunities`). In Docker, `celery_worker` and `celery_beat` run as dedicated container services in `docker-compose.yml`.
- **Fast-Fail Fallback**: Celery broker timeouts are constrained to `2.0s`. If Redis is offline, API request threads skip async email dispatch without hanging or throwing 500 errors.

### Docker & Docker Compose
- **Configuration**: Orchestrates 5 services in [`docker-compose.yml`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/docker-compose.yml): `db` (PostgreSQL 16), `redis` (Redis 7), `web` (Django dev server), `celery_worker`, and `celery_beat`.
- **Documentation**: Fully documented in [`backend/DOCKER.md`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/DOCKER.md).

### Unit Test Suite Execution
- **Fresh Run Execution Date**: September 19, 2026
- **Test Command**: `python manage.py test apps.accounts.tests apps.accounts.test_admin_panel apps.opportunities.tests apps.notifications.tests`
- **Exact Test Result**: **131 passed unit tests in 546.42s (0 failures, 0 errors)**.
- **Coverage**: Email/Password Auth, Firebase Phone Auth, Google OAuth, Admin MFA TOTP & Backup Codes, Anti-enumeration responses, ProviderProfile CRUD & permissions, Opportunity CRUD & filtering, SavedOpportunity bookmarking & CASCADE deletion, Application submission, status transitions, deadline validation, Student Resume magic-bytes validation, Notification creation/fetching, Celery task execution, and Celery broker fast-fail resilience.

### Pagination
- **Global Default**: Configured in `settings.py` `REST_FRAMEWORK` setting: `DEFAULT_PAGINATION_CLASS: rest_framework.pagination.PageNumberPagination`, `PAGE_SIZE: 20`.
- **Custom View Override**: `OpportunityPagination` with `page_size=20`, `max_page_size=100` active on opportunity and applicant lists.
- **Frontend Component**: [`PaginationControl.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/common/PaginationControl.jsx) integrated across user and provider dashboards.

---

## 10. KNOWN ISSUES / OUTSTANDING ITEMS

1. **Firebase SMS GCP Billing Account Block**:
   - Real SMS delivery on Firebase is blocked by Google Cloud billing error `OR_BACR2`. Resolving requires upgrading the GCP project to the Blaze (Pay-as-you-go) plan in GCP Console. Phone Auth sandbox mode with registered test numbers functions properly.
2. **Firebase Web API Key Restrictions**:
   - The Web API key in `firebase-credentials.json` currently lacks HTTP referrer restrictions in Google Cloud Console. Referrer restrictions should be applied prior to production launch.
3. **Provider Profile Edge-Case Blank Page Status**:
   - Provider profiles load properly under standard conditions. Verification for legacy pre-migration accounts missing `ProviderProfile` rows is complete via auto-creation on fetch; edge-case monitoring continues.
4. **Reviews & Ratings System**:
   - Student and provider review submission and score calculation have not yet been built.
5. **Direct Messaging Subsystem**:
   - Real-time or REST direct messaging between students and providers has not yet been built.
6. **Real Geo-Location Search**:
   - Distance radius calculation based on `latitude` and `longitude` fields has not yet been built.
7. **Verified Provider Badge Visibility to Students**:
   - Backend `is_verified` flag exists on `ProviderProfile` and is editable in Django Admin, but student-facing UI listing cards do not yet render a visual "Verified" badge icon.
8. **Clarification on Reviewer "Snippet" Requirement**:
   - The specific format or contents of the "snippet" requirement referenced by the project reviewer was never clarified and remains pending product specification.

---

## 11. ENVIRONMENT / CONFIGURATION

### Complete Environment Variable Reference

```env
# ==========================================
# Core Django Settings
# ==========================================
SECRET_KEY=django-insecure-nextgig-development-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,web,0.0.0.0

# ==========================================
# Database Configuration (PostgreSQL)
# ==========================================
DB_NAME=nextgig_db
DB_USER=nextgig_user
DB_PASSWORD=nextgig_password
DB_HOST=db             # 'localhost' for local non-Docker development
DB_PORT=5432

# ==========================================
# Redis & Celery Configuration
# ==========================================
CELERY_BROKER_URL=redis://redis:6379/0  # 'redis://localhost:6379/0' for local
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ==========================================
# Email Configuration (SMTP)
# ==========================================
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=NextGig Team <noreply@nextgig.com>

# ==========================================
# Frontend Connection URL
# ==========================================
FRONTEND_URL=http://localhost:5173

# ==========================================
# Google OAuth Configuration
# ==========================================
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com

# ==========================================
# Google reCAPTCHA v3 Configuration
# ==========================================
RECAPTCHA_SECRET_KEY=your-recaptcha-v3-secret-key
VITE_RECAPTCHA_SITE_KEY=your-recaptcha-v3-site-key

# ==========================================
# Firebase Configuration
# ==========================================
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json

# ==========================================
# MSG91 SMS API Configuration (Legacy Fallback)
# ==========================================
MSG91_AUTHKEY=your-msg91-auth-key
MSG91_WIDGET_ID=your-msg91-widget-id
```

---

## 12. GIT COMMIT AUDIT LOG (Last 3 Commits)

```
commit 9c68c206e1faf5a7413099de62944d585ac8ddce
Author: Salva kk <salvakk852@gmail.com>
Date:   Thu Sep 17 12:52:08 2026 +0530

    Update PROJECT_STATUS.md with completed profile, privacy, Tailwind, and Celery fix work

commit bf5ba9242dad3e3c814be841bde79a19dfbae482
Author: Salva kk <salvakk852@gmail.com>
Date:   Thu Sep 17 11:53:18 2026 +0530

    Merge Portfolio into Overview, reduce profile to 2 tabs (Overview / Settings)

commit b0241ed40591056ac2548fa5217245141f054ede
Author: Salva kk <salvakk852@gmail.com>
Date:   Thu Sep 17 11:42:09 2026 +0530

    Fix provider profile blank page + simplify profile to 3 tabs
```

*Git Working Tree Status*: **Clean (0 uncommitted changes)**.
