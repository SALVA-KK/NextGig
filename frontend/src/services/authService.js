import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// List of public endpoints that do NOT require an Authorization header
const PUBLIC_ENDPOINTS = [
  '/accounts/login/',
  '/accounts/register/',
  '/accounts/verify-email/',
  '/accounts/forgot-password/',
  '/accounts/reset-password/',
  '/accounts/request-otp/',
  '/accounts/verify-otp/',
  '/accounts/phone-login/request-otp/',
  '/accounts/phone-login/verify-otp/',
  '/accounts/google-login/',
  '/accounts/admin/mfa/verify/',
];

// Automatically attach JWT Access Token to outbound API requests for protected endpoints
api.interceptors.request.use((config) => {
  const isPublic =
    PUBLIC_ENDPOINTS.some((endpoint) => config.url?.includes(endpoint)) ||
    (config.url?.includes('/accounts/invitations/') && config.method?.toLowerCase() === 'get');

  if (!isPublic) {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

/**
 * Helper to extract human-readable error text from DRF error response payloads.
 * Handles strings, arrays, field error objects ({ email: [...], password: [...] }), and nested errors.
 */
const formatErrorResponse = (data, defaultFallback = 'Something went wrong. Please try again.', status = null) => {
  if (status === 401) {
    return 'Your session has expired. Please log in again.';
  }
  if (status === 429) {
    return 'Too many attempts — please wait a moment and try again.';
  }
  if (status && status >= 500) {
    return 'Something went wrong on our end. Please try again shortly.';
  }
  if (!data) return defaultFallback;

  if (typeof data === 'string') {
    if (data.toLowerCase().includes('throttled')) {
      return 'Too many attempts — please wait a moment and try again.';
    }
    if (data.includes('<!DOCTYPE html>') || data.includes('Traceback') || data.toLowerCase().includes('server error')) {
      return 'Something went wrong on our end. Please try again shortly.';
    }
    if (/backend|server running|localhost|connection refused/i.test(data)) {
      return 'Something went wrong. Please check your internet connection and try again.';
    }
    return data;
  }

  if (Array.isArray(data)) {
    return data.map((item) => (typeof item === 'string' ? item : JSON.stringify(item))).join(' ');
  }

  if (typeof data === 'object') {
    if (data.detail && typeof data.detail === 'string') {
      if (data.detail.toLowerCase().includes('throttled')) {
        return 'Too many attempts — please wait a moment and try again.';
      }
      if (data.detail.includes('<!DOCTYPE html>') || data.detail.includes('Traceback') || data.detail.toLowerCase().includes('server error')) {
        return 'Something went wrong on our end. Please try again shortly.';
      }
      if (/backend|server running|localhost|connection refused/i.test(data.detail)) {
        return 'Something went wrong. Please check your internet connection and try again.';
      }
      return data.detail;
    }
    if (data.non_field_errors) {
      const errText = Array.isArray(data.non_field_errors)
        ? data.non_field_errors.join(' ')
        : String(data.non_field_errors);
      if (/backend|server running|localhost|connection refused/i.test(errText)) {
        return 'Something went wrong. Please check your internet connection and try again.';
      }
      return errText;
    }
    if (data.error && typeof data.error === 'string') {
      if (/backend|server running|localhost|connection refused/i.test(data.error)) {
        return 'Something went wrong. Please check your internet connection and try again.';
      }
      return data.error;
    }
    if (data.message && typeof data.message === 'string') {
      if (/backend|server running|localhost|connection refused/i.test(data.message)) {
        return 'Something went wrong. Please check your internet connection and try again.';
      }
      return data.message;
    }

    const messages = [];
    for (const [key, val] of Object.entries(data)) {
      if (key === 'detail' || key === 'non_field_errors') continue;
      const formattedKey = key
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
      const valStr = Array.isArray(val) ? (val.length === 1 ? val[0] : val.join(' ')) : String(val);
      messages.push(`${formattedKey}: ${valStr}`);
    }

    if (messages.length > 0) {
      return messages.join(' | ');
    }
  }

  return defaultFallback;
};

export const authService = {
  /**
   * Authenticate user with Email + Password against Django REST backend (/api/accounts/login/)
   */
  loginEmail: async (email, password, recaptcha_token) => {
    try {
      const response = await api.post('/accounts/login/', {
        email,
        password,
        recaptcha_token,
      });

      const data = response.data;
      if (data.access && data.refresh) {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
        }
      }
      return data;
    } catch (error) {
      console.error('[authService] loginEmail error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Login failed. Please check your credentials.', error.response.status));
    }
  },

  /**
   * Request phone login OTP against Django REST backend (/api/accounts/phone-login/request-otp/)
   */
  requestPhoneLoginOTP: async (phone_number) => {
    try {
      const response = await api.post('/accounts/phone-login/request-otp/', {
        phone_number,
      });
      return response.data;
    } catch (error) {
      console.error('[authService] requestPhoneLoginOTP error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to request OTP. Please check the phone number.', error.response.status));
    }
  },

  /**
   * Verify phone login OTP against Django REST backend (/api/accounts/phone-login/verify-otp/)
   */
  verifyPhoneLoginOTP: async (phoneOrIdToken, otp = null) => {
    try {
      const payload =
        typeof phoneOrIdToken === 'object' && phoneOrIdToken.id_token
          ? { id_token: phoneOrIdToken.id_token }
          : typeof phoneOrIdToken === 'string' && phoneOrIdToken.length > 50
            ? { id_token: phoneOrIdToken }
            : { phone_number: phoneOrIdToken, otp };

      const response = await api.post('/accounts/phone-login/verify-otp/', payload);

      const data = response.data;
      if (data.access && data.refresh) {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
        }
      }
      return data;
    } catch (error) {
      console.error('[authService] verifyPhoneLoginOTP error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Invalid or expired OTP token.', error.response.status));
    }
  },

  // Alias helper methods for general OTP usage
  requestPhoneOtp: async (phone_number) => {
    return authService.requestPhoneLoginOTP(phone_number);
  },

  verifyPhoneOtp: async (phone_number, otp) => {
    return authService.verifyPhoneLoginOTP(phone_number, otp);
  },

  /**
   * Authenticate / auto-register user via Google OAuth ID token (/api/accounts/google-login/)
   */
  loginGoogle: async (id_token) => {
    try {
      const response = await api.post('/accounts/google-login/', {
        id_token,
      });

      const data = response.data;
      if (data.access && data.refresh) {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
        }
      }
      return data;
    } catch (error) {
      console.error('[authService] loginGoogle error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Google authentication failed.', error.response.status));
    }
  },

  /**
   * Verify user email address with Django REST backend (/api/accounts/verify-email/?uid=...&token=...)
   */
  verifyEmail: async (uid, token) => {
    try {
      const response = await api.get('/accounts/verify-email/', {
        params: { uid, token },
      });
      return response.data;
    } catch (error) {
      console.error('[authService] verifyEmail error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Invalid or expired verification link.', error.response.status));
    }
  },

  /**
   * Fetch authenticated user's profile (/api/accounts/profile/)
   */
  getProfile: async () => {
    try {
      const response = await api.get('/accounts/profile/');
      const data = response.data;
      if (data) {
        localStorage.setItem('user', JSON.stringify(data));
      }
      return data;
    } catch (error) {
      console.error('[authService] getProfile error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to fetch profile details.', error.response.status));
    }
  },

  /**
   * Update authenticated user's profile (/api/accounts/profile/)
   */
  updateProfile: async (profileData) => {
    try {
      const response = await api.patch('/accounts/profile/', profileData);
      const data = response.data;
      if (data) {
        localStorage.setItem('user', JSON.stringify(data));
      }
      return data;
    } catch (error) {
      console.error('[authService] updateProfile error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to update profile.', error.response.status));
    }
  },

  /**
   * Request password reset link via email (/api/accounts/forgot-password/)
   */
  forgotPassword: async (email, recaptcha_token) => {
    try {
      const response = await api.post('/accounts/forgot-password/', { email, recaptcha_token });
      return response.data;
    } catch (error) {
      console.error('[authService] forgotPassword error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to request password reset email.', error.response.status));
    }
  },

  /**
   * Reset password using uid and token query params (/api/accounts/reset-password/)
   */
  resetPassword: async (uid, token, newPassword, confirmPassword) => {
    try {
      const response = await api.post(
        '/accounts/reset-password/',
        {
          new_password: newPassword,
          confirm_password: confirmPassword,
        },
        {
          params: { uid, token },
        }
      );
      return response.data;
    } catch (error) {
      console.error('[authService] resetPassword error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to reset password.', error.response.status));
    }
  },

  /**
   * Change current password for authenticated user (/api/accounts/change-password/)
   */
  changePassword: async (oldPassword, newPassword, confirmPassword) => {
    try {
      const response = await api.post('/accounts/change-password/', {
        old_password: oldPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      return response.data;
    } catch (error) {
      console.error('[authService] changePassword error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to change password.', error.response.status));
    }
  },

  /**
   * Remove stored authentication tokens and user data from localStorage & sessionStorage,
   * and attempt server-side refresh token blacklisting.
   */
  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await api.post('/accounts/logout/', { refresh: refreshToken });
      } catch (e) {
        console.error('[authService] logout error:', e);
        // Ignore network or token expiration errors on logout
      }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
    sessionStorage.removeItem('admin_mfa_token');
  },

  /**
   * Retrieve stored user data
   */
  getCurrentUser: () => {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    try {
      return JSON.parse(userStr);
    } catch (e) {
      return null;
    }
  },

  /**
   * Check if user is authenticated (access token exists)
   */
  isAuthenticated: () => {
    return !!localStorage.getItem('access_token');
  },

  /**
   * Retrieve current user's role string
   */
  getUserRole: () => {
    const user = authService.getCurrentUser();
    return user ? user.role : null;
  },

  /**
   * Check if current user is an Admin
   */
  isAdmin: () => {
    return authService.getUserRole() === 'admin';
  },

  /**
   * Verify Admin MFA TOTP / Backup code during pre-auth state
   */
  verifyAdminMFA: async (mfaToken, otpCode) => {
    try {
      const response = await api.post('/accounts/admin/mfa/verify/', {
        mfa_token: mfaToken,
        otp_code: otpCode,
      });

      const data = response.data;
      if (data.access && data.refresh) {
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        if (data.user) {
          localStorage.setItem('user', JSON.stringify(data.user));
        }
      }
      return data;
    } catch (error) {
      console.error('[authService] verifyAdminMFA error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to verify MFA code.', error.response.status));
    }
  },

  /**
   * Initiate Admin MFA setup
   */
  setupAdminMFA: async () => {
    try {
      const response = await api.post('/accounts/admin/mfa/setup/');
      return response.data;
    } catch (error) {
      console.error('[authService] setupAdminMFA error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to initiate MFA setup.', error.response.status));
    }
  },

  /**
   * Confirm and activate Admin MFA setup
   */
  confirmAdminMFA: async (otpCode) => {
    try {
      const response = await api.post('/accounts/admin/mfa/confirm/', {
        otp_code: otpCode,
      });
      return response.data;
    } catch (error) {
      console.error('[authService] confirmAdminMFA error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to confirm MFA setup.', error.response.status));
    }
  },

  /**
   * Disable Admin MFA
   */
  disableAdminMFA: async (password, otpCode) => {
    try {
      const response = await api.post('/accounts/admin/mfa/disable/', {
        password: password,
        otp_code: otpCode,
      });
      return response.data;
    } catch (error) {
      console.error('[authService] disableAdminMFA error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to disable MFA.', error.response.status));
    }
  },

  /**
   * Get Admin MFA status
   */
  getAdminMFAStatus: async () => {
    try {
      const response = await api.get('/accounts/admin/mfa/status/');
      return response.data;
    } catch (error) {
      console.error('[authService] getAdminMFAStatus error:', error);
      return { is_enabled: false };
    }
  },

  /**
   * Generate platform invitation link (/api/accounts/invitations/)
   */
  createInvitation: async () => {
    try {
      const response = await api.post('/accounts/invitations/');
      return response.data;
    } catch (error) {
      console.error('[authService] createInvitation error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to generate invitation link.', error.response.status));
    }
  },

  /**
   * Retrieve public invitation details (/api/accounts/invitations/<token>/)
   */
  getInvitation: async (token) => {
    try {
      const response = await api.get(`/accounts/invitations/${token}/`);
      return response.data;
    } catch (error) {
      console.error('[authService] getInvitation error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      return { valid: false, detail: formatErrorResponse(error.response.data, 'Invalid or expired invitation link.', error.response.status) };
    }
  },

  /**
   * Register a new Student/User account against Django REST backend (/api/accounts/register/)
   */
  register: async ({ email, full_name, phone_number, password, confirm_password, invite_token, recaptcha_token }) => {
    try {
      const response = await api.post('/accounts/register/', {
        email,
        full_name,
        phone_number: phone_number ? phone_number.trim() : undefined,
        password,
        confirm_password,
        invite_token: invite_token || undefined,
        recaptcha_token,
      });
      return response.data;
    } catch (error) {
      console.error('[authService] register error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Registration failed. Please check the provided information.', error.response.status));
    }
  },
};

export default authService;


