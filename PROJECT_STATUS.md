# Technical Audit & Project Status Report - NextGig

---

### SESSION SUMMARY (Work Completed Today)

1. **Authentication Security & History Stack Fixes**:
   - Audited the full authentication subsystem across Email/Password, Google OAuth, Firebase Phone Auth, and Admin MFA (TOTP + 8-character hashed backup codes).
   - Fixed pre-authentication MFA redirect in `handleEmailSubmit` ([`Login.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Login.jsx)) so admins with active MFA are correctly directed to `/admin/mfa-verify`.
   - Updated all post-login, registration, and MFA challenge navigation calls in [`Login.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Login.jsx), [`AdminMFAChallenge.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/AdminMFAChallenge.jsx), and [`Register.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Register.jsx) to use `{ replace: true }`, preventing browser Back button navigation from landing on stale or blank authentication pages.
   - Implemented mount-time auto-redirects on `/login` and `/register` for authenticated users.

2. **Provider Registration & Profile Support**:
   - Updated registration serializer ([`StudentRegistrationSerializer`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py)) to accept optional `role` parameter (`"student"` or `"provider"`), explicitly rejecting `"admin"` with `HTTP 400 Bad Request`.
   - Built `ProviderProfile` model in [`backend/apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py) with organization types (`company`, `startup`, `cafe`, `restaurant`, `shop`, `ngo`, `educational_institution`, `freelancer`, `individual`, `event_organizer`, `other`), description, website, address, city, and `is_verified` boolean flag.
   - Created `ProviderProfileSerializer` with `is_verified` and `user` marked strictly `read_only=True` to prevent self-verification tampering via API.
   - Built `ProviderProfileView` (`GET / PATCH / PUT /api/accounts/provider-profile/`) gated by `IsAuthenticated` + `IsProviderUser` (`role='provider'`), returning `HTTP 403 Forbidden` for students.
   - Registered `ProviderProfile` in Django Admin with editable `is_verified` list view for administrator verification.
   - Applied migration `0005_providerprofile`.

3. **`opportunities` Django App & Saved Opportunities**:
   - Built and registered the `opportunities` Django app (`apps.opportunities`) with full CRUD REST APIs and Bookmarking.
   - Implemented `Opportunity` model in [`backend/apps/opportunities/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/opportunities/models.py) featuring `ArrayField` required skills, pay types, work modes, vacancies, location, deadline, status, ordering by `-created_at`, and compound index on `(status, category, city)`.
   - Implemented `SavedOpportunity` model (`user`, `opportunity`, `created_at`, `unique_together = ('user', 'opportunity')`, ordering by `-created_at`).
   - Built serializers (`OpportunityListSerializer`, `OpportunityDetailSerializer`, `OpportunityCreateUpdateSerializer`, and `SavedOpportunitySerializer` nesting opportunity details and `saved_at`).
   - Built permissions (`IsVerifiedUser`, `IsOwnerOrReadOnly`) in [`permissions.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/opportunities/permissions.py).
   - Implemented DRF generic and API views: `OpportunityListCreateView`, `OpportunityDetailView`, `OpportunitySaveView` (`POST`/`DELETE /api/opportunities/<id>/save/`), and `SavedOpportunityListView` (`GET /api/saved-opportunities/`).
   - Registered Django admin interfaces for `Opportunity` and `SavedOpportunity`.
   - Applied migrations `0001_initial` and `0002_savedopportunity`.
   - Test suite total: **52 passed unit tests** across `accounts` and `opportunities`.

---

### 1. TECH STACK

- **Backend Framework & Version**: Django `6.0.8`, Django REST Framework `3.17.2`
- **Frontend Framework & Version**: React `19.2.8`, Vite `8.2.0`, React Router DOM `7.18.2`
- **Database Used**: PostgreSQL (`django.db.backends.postgresql`, connected via `psycopg2-binary` `2.9.12`)
- **Backend Libraries/Packages**:
  - `django.contrib.postgres`: PostgreSQL specific fields (`ArrayField`)
  - `djangorestframework_simplejwt` (`5.5.1`): JWT Authentication & Token Blacklisting
  - `drf-spectacular` (`0.30.0`): OpenAPI 3 schema & Swagger UI documentation
  - `django-cors-headers` (`4.9.0`): Cross-Origin Resource Sharing
  - `firebase-admin` (`6.6.0`): Firebase ID Token server-side verification
  - `google-auth` (`2.38.0`): Google OAuth ID Token server-side verification
  - `pyotp`: Base32 TOTP calculation for Admin MFA
  - `qrcode`: QR code image generation for TOTP authenticator setup
  - `pillow`: Image processing library
  - `PyJWT` (`2.13.0`): Low-level JWT operations
  - `python-dotenv` (`1.2.2`): Environment file loading
- **Frontend Libraries/Packages**:
  - `axios` (`1.19.0`): HTTP client with JWT request interceptors
  - `@react-oauth/google`: Google OAuth client SDK
  - `firebase`: Firebase Auth client SDK
  - `react-google-recaptcha-v3`: Google reCAPTCHA v3 client SDK

---

### 2. PROJECT STRUCTURE

- **`backend/`**:
  - **`config/`**: Core project settings ([`settings.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py)), URL router ([`urls.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/urls.py)), WSGI ([`wsgi.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/wsgi.py)), and ASGI ([`asgi.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/asgi.py)) entrypoints.
  - **`apps/accounts/`**: Manages custom user authentication, email verification, password reset, MSG91 SMS fallback, Firebase Phone Auth, Google OAuth, TOTP Admin MFA, user profiles, provider profiles, and invitation links.
  - **`apps/opportunities/`**: Manages opportunity listings, CRUD REST APIs, saved opportunities (bookmarking), category/work-mode/city query filtering, owner/admin permissions, and creation throttling.
- **`frontend/`**:
  - **`src/components/`**: Reusable UI components grouped by feature ([`auth/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/auth), [`dashboard/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/dashboard), [`home/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/home), [`profile/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile)).
  - **`src/pages/`**: Top-level page views ([`auth/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth), [`dashboard/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/dashboard), [`admin/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/admin), [`profile/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/profile), [`Home.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/Home.jsx)).
  - **`src/services/`**: Client API services ([`authService.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js)).

---

### 3. AUTHENTICATION AUDIT

- **Implemented Auth Methods**:
  - **Email / Password**: Registration (role optional: `"student"` or `"provider"`, `"admin"` rejected), verification link sending, password authentication, password reset link, and password modification with custom complexity rules (`PasswordComplexityValidator`).
  - **Firebase Phone Auth**: Uses Firebase Web SDK (`signInWithPhoneNumber`, `RecaptchaVerifier`) on the client and server-side token verification (`verify_firebase_id_token`) via `firebase_admin.auth.verify_id_token` in [`apps/accounts/firebase.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/firebase.py).
  - **MSG91 Phone OTP**: Retained in [`utils.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py) as a legacy fallback mechanism.
  - **Google OAuth**: Uses `@react-oauth/google` on the client and server-side token verification (`verify_google_id_token`) via `google.oauth2.id_token.verify_oauth2_token` in [`apps/accounts/google_auth.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/google_auth.py).
  - **Admin MFA**: TOTP authenticator setup (QR code, Base32 secret) + 8-character single-use hashed backup codes. Ephemeral 5-minute pre-auth token gating. Opt-in for admins.
  - **reCAPTCHA v3**: Invisible protection across Registration, Email Login, and Forgot Password forms with a score threshold of `0.5`.
- **Anti-Enumeration Protection**:
  - Duplicate registration attempts return `HTTP 201 Created` with standard success text without creating duplicate users.
  - Invalid email vs. invalid password login attempts return uniform `HTTP 400 Bad Request` `"Invalid email or password."`.
- **Session & History Protection**:
  - All post-login, registration, and MFA verification navigations use `navigate(..., { replace: true })`.
  - `NoCacheHeadersMiddleware` injects `Cache-Control: no-store, no-cache, must-revalidate` on all `/api/` responses.
  - `Login.jsx` and `Register.jsx` automatically redirect authenticated users away from auth pages on mount.

---

### 4. DATABASE MODELS / SCHEMA

- **`CustomUser`** (table `users` in [`apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py)):
  - Fields: `id`, `email` (unique), `full_name`, `phone_number` (unique, nullable), `role` (`student`, `provider`, `admin`), `is_active`, `is_staff`, `is_verified`, `email_verified_at`, `date_joined`, `created_at`, `updated_at`, `password`.
- **`PhoneOTP`** (table `phone_otps` in [`apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py)):
  - Fields: `id`, `phone_number`, `otp_hash`, `purpose`, `expires_at`, `is_used`, `created_at`.
- **`AdminMFA`** (table `admin_mfa` in [`apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py)):
  - Fields: `id`, `user` (OneToOne to `CustomUser`), `totp_secret`, `is_enabled`, `backup_codes` (JSONField array of hashed codes), `created_at`, `updated_at`.
- **`Invitation`** (table `invitations` in [`apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py)):
  - Fields: `id`, `inviter` (FK to `CustomUser`), `token` (unique), `is_used`, `invited_user` (FK to `CustomUser`, nullable), `expires_at`, `created_at`, `updated_at`.
- **`ProviderProfile`** (table `provider_profiles` in [`apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py)):
  - Fields: `id`, `user` (OneToOne to `CustomUser`, related_name `'provider_profile'`), `organization_name`, `organization_type` (choices: `company`, `startup`, `cafe`, `restaurant`, `shop`, `ngo`, `educational_institution`, `freelancer`, `individual`, `event_organizer`, `other`), `description`, `contact_person`, `website`, `address`, `city` (db_index), `is_verified` (boolean, default False, editable only via Admin), `created_at`, `updated_at`.
- **`Opportunity`** (table `opportunities` in [`apps/opportunities/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/opportunities/models.py)):
  - Fields: `id`, `poster` (FK to `CustomUser`, related_name `'posted_opportunities'`), `title`, `description`, `category` (choices: `part_time`, `internship`, `freelance`, `startup_hiring`, `project_collaboration`, `tutoring`, `volunteer`, `event_based`), `required_skills` (`ArrayField`), `pay_type` (choices: `hourly`, `monthly`, `stipend`, `unpaid`), `pay_amount`, `duration`, `working_hours`, `work_mode` (choices: `remote`, `onsite`, `hybrid`), `location_text`, `city` (db_index), `latitude`, `longitude`, `vacancies`, `deadline`, `contact_info`, `status` (choices: `open`, `closed`, `draft`, default `'open'`), `created_at`, `updated_at`.
  - Indexes: Ordering by `-created_at`, compound index `opp_status_cat_city_idx` on `(status, category, city)`.
- **`SavedOpportunity`** (table `saved_opportunities` in [`apps/opportunities/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/opportunities/models.py)):
  - Fields: `id`, `user` (FK to `CustomUser`, related_name `'saved_opportunities'`, on_delete=CASCADE), `opportunity` (FK to `Opportunity`, related_name `'saved_by'`, on_delete=CASCADE), `created_at`.
  - Meta: `unique_together = ('user', 'opportunity')`, ordering by `-created_at`.

---

### 5. API ENDPOINTS

- **Module: `accounts` (`/api/accounts/`)**:
  - `POST /api/accounts/register/` - Register new user (accepts optional `role`: `"student"` or `"provider"`)
  - `GET /api/accounts/verify-email/` - Verify email via `uid` & `token`
  - `POST /api/accounts/login/` - Email/password login (JWTs or MFA challenge)
  - `POST /api/accounts/token/refresh/` - Refresh JWT access token
  - `POST /api/accounts/logout/` - Blacklist refresh token
  - `POST /api/accounts/change-password/` - Change password
  - `POST /api/accounts/forgot-password/` - Request password reset email
  - `POST /api/accounts/reset-password/` - Reset password via `uid` & `token`
  - `POST /api/accounts/request-otp/` - Request general phone OTP
  - `POST /api/accounts/verify-otp/` - Verify general phone OTP
  - `POST /api/accounts/phone-login/request-otp/` - Request phone login OTP
  - `POST /api/accounts/phone-login/verify-otp/` - Verify phone login OTP and return JWTs
  - `POST /api/accounts/google-login/` - Verify Google ID Token and return JWTs
  - `POST /api/accounts/firebase-phone-login/` - Verify Firebase ID Token and return JWTs
  - `GET /api/accounts/profile/` - Retrieve authenticated user profile
  - `PATCH / PUT /api/accounts/profile/` - Update user profile
  - `GET / PATCH / PUT /api/accounts/provider-profile/` - Retrieve or update provider organization profile (gated by `IsAuthenticated` + `IsProviderUser` `role='provider'`, returns HTTP 403 for students)
  - `POST /api/accounts/admin/mfa/verify/` - Verify Admin MFA TOTP or backup code
  - `POST /api/accounts/admin/mfa/setup/` - Initiate Admin TOTP setup
  - `POST /api/accounts/admin/mfa/confirm/` - Confirm and activate Admin MFA
  - `POST /api/accounts/admin/mfa/disable/` - Disable Admin MFA
  - `GET /api/accounts/admin/mfa/status/` - Get Admin MFA status
  - `POST /api/accounts/invitations/` - Create invitation link
  - `GET /api/accounts/invitations/<token>/` - Get public invitation details
- **Module: `opportunities` (`/api/opportunities/`)**:
  - `GET /api/opportunities/` - Public list view (`status='open'` by default; query params: `category`, `work_mode`, `city`, `status`; pagination `page_size=20`)
  - `POST /api/opportunities/` - Create opportunity (gated by `IsAuthenticated` + `IsVerifiedUser`, throttled at `10/hour`)
  - `GET /api/opportunities/<id>/` - Public detail view
  - `PUT / PATCH / DELETE /api/opportunities/<id>/` - Update/Delete (gated by `IsOwnerOrReadOnly`: poster or admin only)
  - `POST /api/opportunities/<id>/save/` - Save/bookmark an opportunity (gated by `IsAuthenticated` + `IsVerifiedUser`, idempotent)
  - `DELETE /api/opportunities/<id>/save/` - Unsave/remove bookmark from an opportunity (gated by `IsAuthenticated`)
  - `GET /api/saved-opportunities/` - Retrieve paginated list of authenticated user's saved opportunities (gated by `IsAuthenticated`, page_size=20)
- **Module: Documentation (`/api/`)**:
  - `GET /admin/` - Django Admin interface
  - `GET /api/schema/` - OpenAPI 3 Schema
  - `GET /api/docs/` - Swagger UI
  - `GET /api/redoc/` - ReDoc UI

---

### 6. FEATURES STATUS

- **Student registration & profile**: **Done**
- **Provider registration & profile**: **Done**
- **Opportunity CRUD**: **Done**
- **Saved opportunities (bookmarking)**: **Done** (`SavedOpportunity` model, `SavedOpportunitySerializer`, `OpportunitySaveView`, `SavedOpportunityListView`, user isolation, idempotent saving, CASCADE cleanup, unit tests)
- **Search & filters**: **Partially Done** (Query param filtering on `category`, `work_mode`, `city`, and `status` in `/api/opportunities/`)
- **Location-based search**: **Not Started** (Geo-distance calculation/bounding box queries not implemented)
- **Resume upload**: **Not Started**
- **Applications (apply/withdraw/track status)**: **Not Started**
- **Saved opportunities**: **Done**
- **Reviews/ratings**: **Not Started**
- **Notifications**: **Not Started**
- **Direct contact / messaging**: **Not Started**
- **Admin panel/management**: **Partially Done** (Django Admin registered for all models; Admin MFA setup active)

---

### 7. TOOLING STATUS

- **Celery / Celery Beat**: **Not implemented**
- **Docker**: **Not implemented**
- **Unit Tests**:
  - Test suites: [`apps/accounts/tests.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/tests.py) and [`apps/opportunities/tests.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/opportunities/tests.py).
  - Total tests: **52 unit tests passed** (`python manage.py test apps.accounts.tests apps.opportunities.tests`).
  - Coverage: Accounts auth flows, ProviderProfile CRUD & role validation, anti-enumeration, password complexity, phone OTP, invitations, Opportunity CRUD permissions/validation/filtering, and Saved Opportunity bookmarking/isolation/idempotency/CASCADE.
- **Pagination**: Implemented on `opportunities` list endpoint and `saved-opportunities` list endpoint (`OpportunityPagination`, `page_size=20`, `max_page_size=100`).

---

### 8. KNOWN ISSUES / OUTSTANDING ITEMS

1. **Firebase SMS Real Delivery Setup**:
   - Real SMS delivery on Firebase requires upgrading the Firebase project to the **Blaze (Pay-as-you-go)** billing plan and setting up SMS quota limits in GCP Console. Test phone numbers work in sandbox mode.
2. **Firebase Web API Key Restrictions**:
   - The Firebase Web API key (`apiKey` in `firebase-credentials.json`) currently lacks HTTP referrer restrictions and API scope restrictions in the Google Cloud Console. Referrer restrictions should be applied before production deployment.
3. **Hardcoded Frontend API Base URL**:
   - [`authService.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js#L3) hardcodes `API_BASE_URL = 'http://127.0.0.1:8000/api'` rather than reading from `import.meta.env.VITE_API_BASE_URL`.
4. **JWT Storage in `localStorage`**:
   - Tokens (`access_token`, `refresh_token`) are stored in `localStorage`. Migrating to `httpOnly`, `SameSite` cookies is recommended for enhanced XSS protection in future refactoring.

---

### 9. ENVIRONMENT / CONFIG

- **Expected Environment Variables (`backend/.env` & [`settings.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py))**:
  - `SECRET_KEY`
  - `DEBUG`
  - `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`
  - `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`
  - `FRONTEND_URL`
  - `GOOGLE_CLIENT_ID`
  - `FIREBASE_CREDENTIALS_PATH`
  - `MSG91_AUTHKEY`, `MSG91_WIDGET_ID`
