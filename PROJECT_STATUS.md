# Technical Audit & Project Status Report

---

### 1. TECH STACK

- **Backend Framework & Version**: Django `6.0.8`, Django REST Framework `3.17.2`
- **Frontend Framework & Version**: React `19.2.8`, Vite `8.2.0`, React Router DOM `7.18.2`
- **Database Used**: PostgreSQL (`django.db.backends.postgresql`, connected via `psycopg2-binary` `2.9.12`)
- **Backend Libraries/Packages**:
  - `djangorestframework_simplejwt` (`5.5.1`): JWT Authentication & Token Blacklisting
  - `drf-spectacular` (`0.30.0`): OpenAPI 3 schema & Swagger UI documentation
  - `django-cors-headers` (`4.9.0`): Cross-Origin Resource Sharing
  - `pyotp`: Base32 TOTP calculation for Admin MFA
  - `qrcode`: QR code image generation for TOTP authenticator setup
  - `pillow`: Image processing library
  - `PyJWT` (`2.13.0`): Low-level JWT operations
  - `python-dotenv` (`1.2.2`): Environment file loading
- **Frontend Libraries/Packages**:
  - `axios` (`1.19.0`): HTTP client with JWT request interceptors

---

### 2. PROJECT STRUCTURE

- **`backend/`**:
  - **`config/`**: Core project settings ([`settings.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py)), URL router ([`urls.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/urls.py)), WSGI ([`wsgi.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/wsgi.py)), and ASGI ([`asgi.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/asgi.py)) entrypoints.
  - **`apps/accounts/`**: The sole backend app; manages custom user authentication, email verification, password reset, MSG91 SMS phone OTP, TOTP Admin MFA, profiles, and invitation links.
- **`frontend/`**:
  - **`src/components/`**: Reusable UI components grouped by feature ([`auth/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/auth), [`dashboard/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/dashboard), [`home/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/home), [`profile/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/profile)).
  - **`src/pages/`**: Top-level page views ([`auth/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth), [`dashboard/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/dashboard), [`admin/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/admin), [`profile/`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/profile), [`Home.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/Home.jsx)).
  - **`src/services/`**: Client API services ([`authService.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js)).

---

### 3. AUTHENTICATION

- **Implemented Auth Methods**:
  - **Email / Password**: Registration, verification link sending, password authentication, password reset link, and password modification.
  - **Firebase Phone Auth**: **Implemented & Active**. Uses Firebase Web SDK (`signInWithPhoneNumber`, `RecaptchaVerifier`) on the client and server-side token verification (`verify_firebase_id_token`) via `firebase_admin.auth.verify_id_token` in [`apps/accounts/firebase.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/firebase.py).
  - **MSG91 Phone OTP**: **Dormant / Deprecated**. Code retained intact in [`utils.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py) and [`models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py) for fallback/reversibility; `MSG91_AUTHKEY` settings are preserved as unused.
  - **Google OAuth**: **Implemented & Active**. Uses `@react-oauth/google` on the client and server-side token verification (`verify_google_id_token`) via `google.oauth2.id_token.verify_oauth2_token` in [`apps/accounts/google_auth.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/google_auth.py) and [`GoogleLoginView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L727-L799). Supports seamless account-linking for existing email accounts and auto-registration for new users with `is_verified=True` and unusable passwords.
  - **reCAPTCHA**: **Not implemented** (0 backend or frontend code).
- **Backend vs Frontend Verification**:
  - **Email/Password**: Backend server-side verification in [`LoginView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L248-L300) using SimpleJWT.
  - **Firebase Phone Auth**: Client obtains ID token via Firebase Auth SDK; backend performs server-side verification in [`verify_firebase_id_token`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/firebase.py#L40-L75) and [`PhoneLoginVerifyOTPView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L654-L725) to issue SimpleJWT access & refresh tokens.
  - **Google OAuth**: Client obtains ID token via `@react-oauth/google`; backend performs server-side token verification in [`verify_google_id_token`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/google_auth.py#L9-L50) and [`GoogleLoginView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L727-L799) to issue SimpleJWT access & refresh tokens.
- **Verification Logic Locations**:
  - Email Token Verification: [`_generate_verification_url`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L24-L34) and [`VerifyEmailView.get`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L205-L245).
  - Password Reset Verification: [`_generate_password_reset_url`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L63-L74) and [`ResetPasswordView.post`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L448-L489).
  - Phone OTP Verification: [`verify_phone_otp`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L290-L349).
  - Admin MFA Verification: [`verify_totp_code`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L432-L463) and [`verify_and_consume_backup_code`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L476-L499) inside [`AdminMFAVerifyView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L734-L808) and [`AdminMFAConfirmView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L863-L939).
- **Session / Token Strategy**:
  - JWT (`rest_framework_simplejwt.authentication.JWTAuthentication`).
  - Access Token Lifetime: 15 minutes.
  - Refresh Token Lifetime: 7 days (`ROTATE_REFRESH_TOKENS: True`, `BLACKLIST_AFTER_ROTATION: True`).
  - Token blacklisting active on logout and refresh rotation.
  - Ephemeral Django `TimestampSigner` token (5-minute TTL) used during Admin MFA pre-authentication state.
- **Token Storage Strategy & Security Note**: Tokens (`access_token` and `refresh_token`) are currently stored in browser `localStorage`. *Technical Debt*: Storing JWTs in `localStorage` allows client-side JavaScript access and is vulnerable to Cross-Site Scripting (XSS) attacks. Storing tokens in `httpOnly`, `SameSite` cookies is a safer architecture to evaluate in future security refactoring.
- **Incomplete / Frontend-Only Auth Code**:
  - Google OAuth / Social Login UI components: None.
  - Firebase Auth integration: None.
  - reCAPTCHA widgets: None.
  - Provider-specific Registration Flow: Model supports `role="provider"`, but registration defaults to `student` with no separate provider registration view/form.

---

### 4. DATABASE MODELS / SCHEMA

- **`CustomUser`** (table `users` in [`models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py#L9-L100)):
  - Key Fields: `id`, `email` (unique index), `full_name`, `phone_number` (unique, nullable), `role` (`student`, `provider`, `admin`), `is_active`, `is_staff`, `is_verified`, `email_verified_at`, `date_joined`, `created_at`, `updated_at`, `password`.
  - Relationships: Base user model; referenced by `AdminMFA` and `Invitation`.
- **`PhoneOTP`** (table `phone_otps` in [`models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py#L102-L155)):
  - Key Fields: `id`, `phone_number`, `otp_hash`, `purpose` (`login`, `registration`, `password_reset`, `mfa`), `expires_at`, `is_used`, `created_at`.
  - Relationships: Standalone OTP verification store.
- **`AdminMFA`** (table `admin_mfa` in [`models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py#L157-L198)):
  - Key Fields: `id`, `user` (OneToOne to `CustomUser`), `totp_secret`, `is_enabled`, `backup_codes` (JSONField array of hashed codes), `created_at`, `updated_at`.
  - Relationships: OneToOne relationship to `CustomUser` (`user -> CustomUser.mfa_settings`).
- **`Invitation`** (table `invitations` in [`models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py#L200-L256)):
  - Key Fields: `id`, `inviter` (ForeignKey to `CustomUser`), `token` (unique), `is_used`, `invited_user` (ForeignKey to `CustomUser`, nullable), `expires_at`, `created_at`, `updated_at`.
  - Relationships: `inviter` -> `CustomUser` (`sent_invitations`), `invited_user` -> `CustomUser` (`received_invitation`).

---

### 5. API ENDPOINTS

- **Module: `accounts` (`/api/accounts/` in [`urls.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/urls.py))**:
  - `POST /api/accounts/register/` - Register new student account (No pagination)
  - `GET /api/accounts/verify-email/` - Verify email via `uid` & `token` query params (No pagination)
  - `POST /api/accounts/login/` - Email/password login (returns JWTs or MFA challenge) (No pagination)
  - `POST /api/accounts/token/refresh/` - Refresh JWT access token (No pagination)
  - `POST /api/accounts/logout/` - Blacklist refresh token (No pagination)
  - `POST /api/accounts/change-password/` - Change authenticated user password (No pagination)
  - `POST /api/accounts/forgot-password/` - Request password reset email (No pagination)
  - `POST /api/accounts/reset-password/` - Reset password via `uid` & `token` query params (No pagination)
  - `POST /api/accounts/request-otp/` - Request general SMS phone OTP (No pagination)
  - `POST /api/accounts/verify-otp/` - Verify general SMS phone OTP (No pagination)
  - `POST /api/accounts/phone-login/request-otp/` - Request phone login OTP (No pagination)
  - `POST /api/accounts/phone-login/verify-otp/` - Verify phone login OTP and return JWTs (No pagination)
  - `GET /api/accounts/profile/` - Retrieve authenticated user profile (No pagination)
  - `PATCH /api/accounts/profile/` - Partial update user profile (No pagination)
  - `PUT /api/accounts/profile/` - Full update user profile (No pagination)
  - `POST /api/accounts/admin/mfa/verify/` - Verify Admin MFA TOTP or backup code during pre-auth (No pagination)
  - `POST /api/accounts/admin/mfa/setup/` - Initiate Admin TOTP setup (No pagination)
  - `POST /api/accounts/admin/mfa/confirm/` - Confirm and activate Admin MFA (No pagination)
  - `POST /api/accounts/admin/mfa/disable/` - Disable Admin MFA (No pagination)
  - `GET /api/accounts/admin/mfa/status/` - Get Admin MFA status (No pagination)
  - `POST /api/accounts/invitations/` - Create platform invitation link (No pagination)
  - `GET /api/accounts/invitations/<str:token>/` - Get public invitation details (No pagination)
- **Module: Core & Documentation (`/api/` & `/admin/` in [`config/urls.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/urls.py))**:
  - `GET /admin/` - Django Admin interface
  - `GET /api/schema/` - OpenAPI 3 Schema
  - `GET /api/docs/` - Swagger UI
  - `GET /api/redoc/` - ReDoc UI
- **Pagination Summary**: **0 endpoints have pagination implemented.**

---

### 6. FEATURES STATUS

- **Student registration & profile**: **Done** (Registration view, email verification, profile retrieve/update API, and React frontend pages).
- **Provider registration & profile**: **Partially Done** (`Role.PROVIDER` exists in choices, but no provider-specific registration view, profile fields, or company models exist).
- **Opportunity CRUD**: **Not Started** (No models, serializers, endpoints, or UI).
- **Search & filters**: **Not Started** (No search or filtering logic implemented).
- **Location-based search**: **Not Started** (No geo-location fields or location query logic).
- **Resume upload**: **Not Started** (No file upload models or handlers).
- **Applications (apply/withdraw/track status)**: **Not Started** (No application models, views, or UI).
- **Saved opportunities**: **Not Started** (No saved opportunity models or views).
- **Reviews/ratings**: **Not Started** (No review models or endpoints).
- **Notifications**: **Not Started** (No notification models, tasks, or endpoints).
- **Direct contact / messaging**: **Not Started** (No chat or messaging models/views).
- **Admin panel/management**: **Partially Done** (Standard Django admin and Admin MFA TOTP setup/verify endpoints exist; React Admin Dashboard consists of placeholder cards with no administrative management tools).

---

### 7. TOOLING STATUS

- **Celery**: **Not implemented** (Not installed in `requirements.txt`, no `celery.py`, no tasks, no broker configured).
- **Celery Beat**: **Not implemented** (No scheduled tasks configured).
- **Docker**: **Not implemented** (No `Dockerfile` or `docker-compose.yml` present).
- **Unit Tests**:
  - Test file: [`backend/apps/accounts/tests.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/tests.py) (5 test methods in 2 TestCase classes: `MSG91PhoneOTPTestCase`, `InvitationTestCase`).
  - Scope: MSG91 phone format helper, phone OTP verify bad code response, invitation creation (auth vs unauth), public invitation GET, and registration with/without invite token.
  - Rough coverage estimate: **~15-20%** of the `accounts` app.
- **Pagination**: **Not implemented** (No `DEFAULT_PAGINATION_CLASS` in `settings.py`; no per-view pagination classes in any views).

---

### 8. KNOWN ISSUES / INCOMPLETE AREAS

- **Missing Business Core Apps**: The backend currently only has the `accounts` app. Applications, opportunities, notifications, messaging, and search apps are entirely uncreated.
- **Hardcoded Frontend API Base URL**: [`authService.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js#L3) hardcodes `API_BASE_URL = 'http://127.0.0.1:8000/api'` rather than reading from `import.meta.env`.
- **Dev Fallback Console OTP**: Phone OTP logs to server console in DEBUG mode when MSG91 API keys are unconfigured.
- **Placeholder Admin Dashboard UI**: React Admin Dashboard ([`AdminDashboard.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/admin/AdminDashboard.jsx)) has static UI cards and lacks administrative action controls.

---

### 9. ENVIRONMENT / CONFIG

- **Expected Environment Variables (`backend/.env` & [`settings.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py))**:
  - `SECRET_KEY`
  - `DEBUG`
  - `DB_NAME`
  - `DB_USER`
  - `DB_PASSWORD`
  - `DB_HOST`
  - `DB_PORT`
  - `EMAIL_BACKEND`
  - `EMAIL_HOST`
  - `EMAIL_PORT`
  - `EMAIL_HOST_USER`
  - `EMAIL_HOST_PASSWORD`
  - `EMAIL_USE_TLS`
  - `DEFAULT_FROM_EMAIL`
  - `FRONTEND_URL`
  - `MSG91_AUTHKEY`
  - `MSG91_WIDGET_ID`

---

### 10. RECENT FIXES

- **Bug 1: Validation Failures on Registration & Login (Fixed)**
  - *Issue*: Submitting invalid email formats or missing fields on registration/login forms resulted in silent submission blocking with no error feedback.
  - *Root Cause*: HTML5 native form validation on `<input type="email">` silently blocked form submits before React event handlers executed. `authService.js` error handling also only parsed specific hardcoded error key formats.
  - *Fix Implemented*: Added `noValidate` to frontend `<form>` elements in [`Login.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Login.jsx) and [`Register.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Register.jsx) so JavaScript submit handlers execute reliably. Enhanced [`authService.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js) with `formatErrorResponse` to dynamically format all DRF field validation errors into user-friendly error banners. Added explicit `error_messages` overrides in [`serializers.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py).

- **Bug 2: Browser Back Button Access to Authenticated Pages (Fixed)**
  - *Issue*: Hitting the browser Back button after logout or session invalidation displayed previously rendered authenticated pages (e.g. `/dashboard`, `/profile`).
  - *Root Cause*: Backend endpoints lacked anti-caching HTTP headers, allowing browsers to store API responses and page renders in HTTP cache and BFcache (Back/Forward cache). Route guards were also static on initial render.
  - *Fix Implemented*: Created `NoCacheHeadersMiddleware` in [`middleware.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/middleware.py) (registered in [`settings.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py)) to append `Cache-Control: no-store, no-cache, must-revalidate, max-age=0, private` to all `/api/` HTTP responses. Updated [`ProtectedRoute.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/components/auth/ProtectedRoute.jsx) to listen to `useLocation()` and window `pageshow` / `popstate` events, dynamically validating tokens and immediately redirecting unauthenticated users to `/login`.

- **Logout Token Removal Verification (Verified & Enhanced)**
  - *Verification*: Confirmed that [`authService.logout()`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js) purges `access_token`, `refresh_token`, and `user` from `localStorage`, and `admin_mfa_token` from `sessionStorage`. Updated `logout()` to also asynchronously call `POST /api/accounts/logout/` to blacklist the refresh token on the server side.

- **Google OAuth Login & Auto-Registration (Completed)**
  - *Goal*: Implemented Google OAuth authentication for login and registration on frontend and backend, matching the server-side ID token verification pattern of Firebase Phone Auth.
  - *Backend*: Installed `google-auth`. Created [`apps/accounts/google_auth.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/google_auth.py) exporting `verify_google_id_token(id_token)` using `google.oauth2.id_token.verify_oauth2_token`. Created [`GoogleLoginView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L727-L799) (`POST /api/accounts/google-login/`) with `throttle_scope = "login"`.
  - *Account Linking & Auto-Registration*: Existing accounts with matching email log in seamlessly; new emails auto-create a `CustomUser` with `is_verified=True`, `role="student"`, and an unusable password.
  - *Frontend*: Installed `@react-oauth/google`. Wrapped application with `<GoogleOAuthProvider>` in [`main.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/main.jsx). Integrated `<GoogleLogin>` component in both [`Login.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Login.jsx) and [`Register.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Register.jsx).

---

### 11. AUTH VALIDATION AUDIT

#### Registration Audit
- **Email Format Validation**: **Implemented**
  - *Location*: [`serializers.py:L20-L27`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L20-L27)
  - *Code*:
    ```python
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": "Email address is required.",
            "invalid": "Please enter a valid email address.",
            "blank": "Email address cannot be blank.",
        },
    )
    ```
  - *Behavior*: Returns `HTTP 400 Bad Request` `{"email": ["Please enter a valid email address."]}`.
- **Email Uniqueness Check & Anti-Enumeration**: **Implemented & Neutralized (Resolved)**
  - *Location*: [`serializers.py:L138-L148`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L138-L148), [`utils.py:L501-L528`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L501-L528), and [`views.py:L149-L167`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L149-L167)
  - *Resolution*: Duplicate email registration attempts return `HTTP 201 Created` with the exact same JSON response (`"Student account registered successfully. Please check your email to verify your account."`) as new registrations without creating duplicate records. Password hashing (`make_password`) is executed to maintain timing neutrality. An existing account notification email (`send_existing_account_email`) is dispatched to the account owner with links to log in or reset their password.
- **Password Strength Validation Across All Flows**: **Implemented & Consistently Enforced**
  - *Location*: Configured in [`settings.py:L113-L126`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L113-L126) (`UserAttributeSimilarityValidator`, `MinimumLengthValidator`, `CommonPasswordValidator`, `NumericPasswordValidator`) and explicitly invoked across all password-setting flows:
    1. **Registration**: `StudentRegistrationSerializer.validate()` calls `validate_password(password, user=user_instance)` ([`serializers.py:L115-L122`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L115-L122)).
    2. **Password Change**: `ChangePasswordSerializer.validate()` calls `validate_password(new_password, user=user)` ([`serializers.py:L291-L294`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L291-L294)).
    3. **Password Reset**: `ResetPasswordSerializer.validate()` calls `validate_password(new_password, user=user)` ([`serializers.py:L350-L353`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L350-L353)).
  - *Verification*: Confirmed via unit tests (`PasswordStrengthValidationTestCase` in [`tests.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/tests.py)) that weak passwords (e.g. `"password"`) are consistently rejected with `HTTP 400 Bad Request` across registration, password change, and password reset endpoints.
- **Required Field Validation**: **Partially Implemented**
  - *Location*: [`serializers.py:L28-L34`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L28-L34)
  - *Behavior*: Missing or empty strings return `HTTP 400 Bad Request`. Whitespace-only strings (e.g. `"   "`) are trimmed by DRF's default `trim_whitespace=True` and caught by `blank` validation.
- **Rate Limiting / Throttling**: **Implemented & Layered (Resolved)**
  - *Location*: Configured in [`settings.py:L153-L167`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L153-L167), defined in [`throttling.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/throttling.py), and applied in [`views.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py).
  - *Layered Throttling Policy*:
    1. **Login Endpoints**: `login: 5/minute` per IP (applied to `/login/`, `/phone-login/request-otp/`, `/phone-login/verify-otp/`, `/request-otp/`).
    2. **Registration Burst Throttle (`RegisterBurstRateThrottle`)**: `1/4s` (max 1 request per 4 seconds per IP). Instantly blocks rapid-fire bot requests without affecting human users.
    3. **Registration Sustained Throttle (`RegisterSustainedRateThrottle`)**: `20/hour` (max 20 requests per hour per IP). High enough safety net so genuine users fixing form errors never get blocked while stopping slow automated script abuse.
    4. **Forgot Password Endpoints (`ForgotPasswordIPRateThrottle` & `ForgotPasswordEmailRateThrottle`)**: Max `3/hour` per IP AND max `3/hour` per target email address. Prevents SMTP resource exhaustion and targeted user inbox email flooding even across distributed proxy networks.
  - *Frontend UX*: Submit button in [`Register.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Register.jsx) is disabled synchronously upon submission. HTTP 429 errors are formatted by [`authService.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js) into `"Too many attempts — please wait a moment and try again."`.

#### Login Audit
- **Uniform Error Message / Status Code ("User Not Found" vs "Wrong Password")**: **Implemented**
  - *Location*: [`serializers.py:L198-L202`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L198-L202)
  - *Code*:
    ```python
    request = self.context.get("request")
    user = authenticate(request=request, email=email, password=password)

    if not user:
        raise serializers.ValidationError("Invalid email or password.")
    ```
  - *Quoted Responses*:
    - *User Does Not Exist*: `HTTP 400 Bad Request` -> `{"non_field_errors": ["Invalid email or password."]}`
    - *Wrong Password*: `HTTP 400 Bad Request` -> `{"non_field_errors": ["Invalid email or password."]}`
  - *Behavior*: Uniform status code and error body for both non-existent users and bad passwords, preventing user enumeration via login errors.
- **Account Lockout or Rate Limiting on Failed Attempts**: **Implemented via IP Throttling (Resolved)**
  - *Location*: [`settings.py:L153-L161`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L153-L161) and [`views.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py) (`throttle_scope = "login"`).
  - *Resolution*: IP-based throttling limits login attempts to `5/minute` per IP, returning `HTTP 429 Too Many Requests` when exceeded. Per-user DB-tracked account lockout remains deferred as technical debt.
- **`is_active` Check Before Issuing Tokens**: **Implemented**
  - *Location*: [`serializers.py:L204-L205`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L204-L205)
  - *Code*:
    ```python
    if not user.is_active:
        raise serializers.ValidationError("This account has been disabled.")
    ```
  - *Behavior*: Inactive accounts return `HTTP 400 Bad Request` and are blocked from receiving tokens.
- **`is_verified` Check Before Allowing Login**: **Implemented**
  - *Location*: [`serializers.py:L207-L210`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L207-L210)
  - *Code*:
    ```python
    if not user.is_verified:
        raise serializers.ValidationError(
            "Please verify your email address before logging in."
        )
    ```
  - *Behavior*: Unverified accounts receive `HTTP 400 Bad Request` `{"non_field_errors": ["Please verify your email address before logging in."]}` and cannot log in.
- **Timing Differences ("User Not Found" vs "Wrong Password")**: **Partially Implemented / Minor Timing Side-Channel Risk**
  - *Location*: [`serializers.py:L199`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L199) calling Django's `authenticate()`.
  - *Analysis*: Django's default `ModelBackend` runs dummy password hashing when a user is not found to reduce timing gaps, but DB lookup latency vs. PBKDF2 hashing times may still exhibit minor microsecond-level timing differences under high-precision analysis.

---

### 12. PASSWORD & SECRETS AUDIT

1. **Password Hashing on Registration**: **Implemented**
   - *Location*: [`serializers.py:L149-L153`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L149-L153) and [`managers.py:L22-L24`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/managers.py#L22-L24)
   - *Code*:
     - `serializers.py`:
       ```python
       user = CustomUser.objects.create_user(
           email=email,
           password=password,
           **validated_data,
       )
       ```
     - `managers.py`:
       ```python
       user = self.model(email=email, **extra_fields)
       user.set_password(password)
       user.save(using=self._db)
       ```
   - *Analysis*: Uses `CustomUserManager.create_user()` which calls `user.set_password(password)`. Duplicate registration attempts also run `make_password(password)` for timing consistency. No raw passwords are ever assigned directly without hashing.

2. **Password Confirmation & Mismatch Validation**: **Implemented**
   - *Location*: [`serializers.py:L45-L54`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L45-L54) and [`serializers.py:L107-L112`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L107-L112)
   - *Code*:
     ```python
     confirm_password = serializers.CharField(
         write_only=True,
         required=True,
         style={"input_type": "password"},
         error_messages={
             "required": "Confirm password is required.",
             "blank": "Confirm password cannot be blank.",
         },
         help_text="Must match the password field.",
     )
     # ...
     if password != confirm_password:
         raise serializers.ValidationError(
             {"confirm_password": "Passwords do not match."}
         )
     ```
   - *Analysis*: `StudentRegistrationSerializer` explicitly defines `confirm_password` (`write_only=True`, `required=True`) and enforces password match in `validate()`.

3. **Password Change Endpoint Credentials**: **Implemented**
   - *Location*: [`serializers.py:L255-L260`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L255-L260) and [`views.py:L380-L384`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L380-L384)
   - *Code*:
     ```python
     old_password = serializer.validated_data["old_password"]
     new_password = serializer.validated_data["new_password"]

     user = request.user

     if not user.check_password(old_password):
         return Response(
             {"old_password": "Current password is incorrect."},
             status=status.HTTP_400_BAD_REQUEST,
         )
     ```
   - *Analysis*: `ChangePasswordView` requires `old_password` and validates it against `user.check_password(old_password)` before allowing a password update.

4. **Password Reset Token Expiry & Single-Use**: **Implemented**
   - *Location*: [`utils.py:L69`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L69) and [`views.py:L490-L504`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L490-L504)
   - *Code*:
     ```python
     # utils.py
     token = default_token_generator.make_token(user)

     # views.py
     if not default_token_generator.check_token(user, token):
         return Response(
             {"detail": "Password reset link is invalid or has expired."},
             status=status.HTTP_400_BAD_REQUEST,
         )
     # ...
     user.set_password(new_password)
     user.save()
     ```
   - *Analysis*: Uses Django's `default_token_generator` (`PasswordResetTokenGenerator`). Tokens are single-use because `default_token_generator` includes `user.password` in the token hash payload; calling `user.set_password(new_password)` immediately invalidates the token upon use. Tokens are time-limited via Django default `PASSWORD_RESET_TIMEOUT` (259,200 seconds / 3 days if unset).

5. **`SECRET_KEY` & JWT Signing Key Source**: **Implemented**
   - *Location*: [`settings.py:L31`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L31) and [`settings.py:L210`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L210)
   - *Code*:
     ```python
     SECRET_KEY = os.getenv("SECRET_KEY")
     # ...
     SIMPLE_JWT = {
         # ...
         "SIGNING_KEY": SECRET_KEY,
     }
     ```
   - *Analysis*: Read strictly from the `.env` environment variable via `os.getenv("SECRET_KEY")` with no hardcoded fallback strings. JWT signing uses `SECRET_KEY`.

6. **User Data Serializers Output Fields**: **Implemented**
   - *Location*: [`serializers.py:L422-L437`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L422-L437)
   - *Code*:
     ```python
     class UserProfileSerializer(serializers.ModelSerializer):
         class Meta:
             model = CustomUser
             fields = (
                 "email",
                 "full_name",
                 "phone_number",
                 "role",
                 "date_joined",
             )
     ```
   - *Analysis*: Profile serializers (`UserProfileSerializer`) exclude password fields entirely. `StudentRegistrationSerializer` explicitly marks `password` and `confirm_password` as `write_only=True`.

7. **Active Password Hasher**: **Implemented (Django Default)**
   - *Location*: Default in Django (`PASSWORD_HASHERS` is unset in [`settings.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py)).
   - *Active Hasher*: `django.contrib.auth.hashers.PBKDF2PasswordHasher` (PBKDF2 with SHA256).

8. **Custom Password Complexity Policy (`PasswordComplexityValidator`)**: **Implemented & Enforced**
   - *Location*: Defined in [`validators.py:L7-L58`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/validators.py#L7-L58) and registered in [`settings.py:L125-L127`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L125-L127).
   - *Policy Requirements*: 8-128 characters, uppercase (`A-Z`), lowercase (`a-z`), digit (`0-9`), and special character (`!@#$%^&*...`).
   - *Test Verification (`correcthorsebattery`) Response*: Submitting `"correcthorsebattery"` (missing uppercase letter) returns `HTTP 400 Bad Request` with `{"password": ["Password must contain at least one uppercase letter (A-Z)."]}` across `/register/`, `/change-password/`, and `/reset-password/`.
   - *Frontend Requirements Display*: Added clear password requirement helper text under password input in [`Register.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Register.jsx).

---

## 13. MSG91 Current Implementation Reference (Firebase Migration Reference)

This section documents the complete current MSG91 phone OTP implementation across `apps/accounts` and the frontend UI, serving as a blueprint for migrating to Firebase Phone Authentication.

### 1. MSG91 API Endpoints Called
- **Send OTP Widget API**:
  - *URL*: `https://control.msg91.com/api/v5/widget/sendOtp` (HTTP `POST`)
  - *Caller Function*: [`send_phone_otp(phone_number, otp, purpose)`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L233-L287) in [`backend/apps/accounts/utils.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py)
  - *Payload & Headers*:
    ```python
    url = "https://control.msg91.com/api/v5/widget/sendOtp"
    payload = {
        "mobile": formatted_phone, # e.g. "919207362507"
        "widgetId": widget_id,
    }
    headers = {
        "authkey": authkey,
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    ```
- **Verify OTP Widget API**:
  - *URL*: `https://control.msg91.com/api/v5/widget/verifyOtp` (HTTP `POST`)
  - *Caller Function*: [`verify_phone_otp(phone_number, otp, purpose)`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L290-L349) in [`backend/apps/accounts/utils.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py)
  - *Payload & Headers*:
    ```python
    url = "https://control.msg91.com/api/v5/widget/verifyOtp"
    payload = {
        "mobile": formatted_phone, # e.g. "919207362507"
        "otp": str(otp).strip(),
        "widgetId": widget_id,
    }
    headers = {
        "authkey": authkey,
        "Content-Type": "application/json",
        "accept": "application/json",
    }
    ```

### 2. MSG91 Environment Variables
- **`MSG91_AUTHKEY`**:
  - Read in [`backend/config/settings.py:L206`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L206): `MSG91_AUTHKEY = os.getenv("MSG91_AUTHKEY")`
  - Accessed in [`utils.py:L243`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L243) & [`L296`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L296): `authkey = getattr(settings, "MSG91_AUTHKEY", None) or os.getenv("MSG91_AUTHKEY")`
- **`MSG91_WIDGET_ID`**:
  - Read in [`backend/config/settings.py:L207`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L207): `MSG91_WIDGET_ID = os.getenv("MSG91_WIDGET_ID", "SecureOTPWidgetDKTD")`
  - Accessed in [`utils.py:L244`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L244) & [`L297`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L297): `widget_id = getattr(settings, "MSG91_WIDGET_ID", None) or os.getenv("MSG91_WIDGET_ID", "SecureOTPWidgetDKTD")`

### 3. `PhoneOTP` Database Model
- *Location*: [`PhoneOTP`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py#L102-L155) in [`backend/apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py) (Table: `phone_otps`)
- *Fields & Types*:
  ```python
  class PhoneOTP(models.Model):
      phone_number = models.CharField(max_length=20, db_index=True)
      otp_hash = models.CharField(max_length=128)
      purpose = models.CharField(max_length=20, choices=OTPPurpose.choices)
      expires_at = models.DateTimeField()
      is_used = models.BooleanField(default=False)
      created_at = models.DateTimeField(auto_now_add=True)
  ```
- *Generic vs. MSG91-Specific Classification*:
  - **Generic Fields**: All 6 fields (`phone_number`, `otp_hash`, `purpose`, `expires_at`, `is_used`, `created_at`) store generic OTP state.
  - **MSG91-Specific Fields**: **None**. No MSG91 response metadata (e.g. `req_id`, `widget_id`) is stored in the database. MSG91 handles verification sessions statelessly via its widget API, while Django relies on `PhoneOTP` for local verification fallback and auditing.

### 4. End-to-End Phone OTP View Workflows
1. **General OTP Request (`POST /api/accounts/request-otp/`)**:
   - *Location*: [`RequestOTPView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L525-L560)
   - *Flow*: Validates `phone_number` and `purpose` via `RequestOTPSerializer` -> Calls `create_phone_otp` (saves hashed 6-digit OTP in `PhoneOTP`) -> Calls `send_phone_otp` (dispatches HTTP POST to MSG91 `/sendOtp` or logs to dev console) -> Returns `HTTP 200 OK` `{"message": "If the phone number is eligible, an OTP has been sent."}`.
2. **Phone Login OTP Request (`POST /api/accounts/phone-login/request-otp/`)**:
   - *Location*: [`PhoneLoginRequestOTPView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L604-L651)
   - *Flow*: Throttled to 5/minute (`throttle_scope = "login"`) -> Validates `phone_number` -> Checks if verified `CustomUser` exists for phone -> If user exists, creates `PhoneOTP` record and calls `send_phone_otp` -> Returns `HTTP 200 OK` `{"message": "If the phone number is registered, an OTP has been sent."}`.
3. **General OTP Verification (`POST /api/accounts/verify-otp/`)**:
   - *Location*: [`VerifyOTPView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L562-L601)
   - *Flow*: Validates `phone_number`, `otp`, `purpose` via `VerifyOTPSerializer` -> Calls `verify_phone_otp` -> If MSG91 keys present, calls MSG91 `/verifyOtp` (marks `PhoneOTP.is_used = True` on success) -> If MSG91 keys absent, verifies against local `PhoneOTP` record in DB -> Returns `HTTP 200 OK` `{"message": "OTP verified successfully."}` or `HTTP 400 Bad Request` `{"detail": "Invalid or expired OTP."}`.
4. **Phone Login OTP Verification (`POST /api/accounts/phone-login/verify-otp/`)**:
   - *Location*: [`PhoneLoginVerifyOTPView`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L654-L725)
   - *Flow*: Throttled to 5/minute (`throttle_scope = "login"`) -> Calls `verify_phone_otp(...)` -> Retrieves active verified user -> Calls `update_last_login(None, user)` -> Generates SimpleJWT access & refresh tokens -> Returns `HTTP 200 OK` with `{ "message": "Phone login successful.", "access": "...", "refresh": "...", "user": {...} }`.

### 5. `DEBUG`-Mode Console Fallback Behavior
When `MSG91_AUTHKEY` or `MSG91_WIDGET_ID` is unconfigured (`None`/empty) and `settings.DEBUG` is `True`:
- **Dispatch Fallback ([`utils.py:L276-L285`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L276-L285))**:
  ```python
  if getattr(settings, "DEBUG", False):
      print("========================================")
      print("PHONE OTP (DEV MOCK)")
      print(f"Phone: {formatted_phone}")
      print(f"Purpose: {purpose}")
      print(f"OTP: {otp}")
      print("Valid For: 5 minutes")
      print("========================================")
      return True
  ```
- **Verification Fallback ([`utils.py:L329-L348`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L329-L348))**: Retrieves latest unexpired, unused `PhoneOTP` record from database, checks `check_password(otp, otp_record.otp_hash)`, sets `is_used = True`, and returns `True`.

### 6. Frontend Callers & Response Expectations
- **Caller UI Component**: [`frontend/src/pages/auth/Login.jsx:L81-L130`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Login.jsx#L81-L130)
- **API Service Layer**: [`frontend/src/services/authService.js:L128-L179`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js#L128-L179)
  - `authService.requestPhoneLoginOTP(phone)` -> Expects `{ "message": "..." }`
  - `authService.verifyPhoneLoginOTP(phone, otp)` -> Expects `{ "message": "...", "access": "...", "refresh": "...", "user": { "id": 1, ... } }`
- **Client Storage**: Upon verification, `authService.verifyPhoneLoginOTP` stores `access_token`, `refresh_token`, and `user` object in `localStorage` before role-based redirection.

### 7. Touch Points / Files Referencing MSG91 or Phone OTP
1. [`backend/config/settings.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/config/settings.py#L205-L208): `MSG91_AUTHKEY`, `MSG91_WIDGET_ID` configuration.
2. [`backend/apps/accounts/models.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/models.py#L102-L155): `PhoneOTP` model & `OTPPurpose` choices.
3. [`backend/apps/accounts/utils.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/utils.py#L218-L349): `format_phone_for_msg91`, `send_phone_otp`, `verify_phone_otp`, `create_phone_otp`.
4. [`backend/apps/accounts/serializers.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/serializers.py#L225-L250): `RequestOTPSerializer` & `VerifyOTPSerializer`.
5. [`backend/apps/accounts/views.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/views.py#L525-L725): `RequestOTPView`, `VerifyOTPView`, `PhoneLoginRequestOTPView`, `PhoneLoginVerifyOTPView`.
6. [`backend/apps/accounts/urls.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/urls.py#L22-L25): Endpoints `/request-otp/`, `/verify-otp/`, `/phone-login/request-otp/`, `/phone-login/verify-otp/`.
7. [`backend/apps/accounts/tests.py`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/backend/apps/accounts/tests.py#L5-L45): `MSG91PhoneOTPTestCase` unit test suite.
8. [`frontend/src/services/authService.js`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/services/authService.js#L128-L179): `requestPhoneLoginOTP`, `verifyPhoneLoginOTP`, `requestPhoneOtp`, `verifyPhoneOtp`.
9. [`frontend/src/pages/auth/Login.jsx`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/frontend/src/pages/auth/Login.jsx#L81-L130): Phone login UI tab handlers.
10. [`PROJECT_STATUS.md`](file:///c:/Users/ACM/Desktop/myprojects/NextGig/PROJECT_STATUS.md): Architectural status documentation.
