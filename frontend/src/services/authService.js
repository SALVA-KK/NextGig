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
const formatErrorResponse = (data, defaultFallback = 'An error occurred. Please try again.', status = null) => {
  if (status === 429) {
    return 'Too many attempts — please wait a moment and try again.';
  }
  if (!data) return defaultFallback;

  if (typeof data === 'string') {
    if (data.toLowerCase().includes('throttled')) {
      return 'Too many attempts — please wait a moment and try again.';
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
      return data.detail;
    }
    if (data.non_field_errors) {
      return Array.isArray(data.non_field_errors)
        ? data.non_field_errors.join(' ')
        : String(data.non_field_errors);
    }
    if (data.error && typeof data.error === 'string') {
      return data.error;
    }
    if (data.message && typeof data.message === 'string') {
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
  loginEmail: async (email, password) => {
    try {
      const response = await api.post('/accounts/login/', {
        email,
        password,
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Login failed. Please check your credentials.'));
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Failed to request OTP. Please check the phone number.'));
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Invalid or expired OTP token.'));
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
   * Verify user email address with Django REST backend (/api/accounts/verify-email/?uid=...&token=...)
   */
  verifyEmail: async (uid, token) => {
    try {
      const response = await api.get('/accounts/verify-email/', {
        params: { uid, token },
      });
      return response.data;
    } catch (error) {
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      let errorMsg = 'Invalid or expired verification link.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.error) {
        errorMsg = data.error;
      } else if (data.message) {
        errorMsg = data.message;
      }

      throw new Error(errorMsg);
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      let errorMsg = 'Failed to fetch profile details.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.error) {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      let errorMsg = 'Failed to update profile.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.full_name) {
        errorMsg = Array.isArray(data.full_name) ? data.full_name[0] : data.full_name;
      } else if (data.phone_number) {
        errorMsg = Array.isArray(data.phone_number) ? data.phone_number[0] : data.phone_number;
      } else if (data.error) {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
    }
  },

  /**
   * Request password reset link via email (/api/accounts/forgot-password/)
   */
  forgotPassword: async (email) => {
    try {
      const response = await api.post('/accounts/forgot-password/', { email });
      return response.data;
    } catch (error) {
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      let errorMsg = 'Failed to request password reset email.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.email) {
        errorMsg = Array.isArray(data.email) ? data.email[0] : data.email;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.error) {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      let errorMsg = 'Failed to reset password.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.new_password) {
        errorMsg = Array.isArray(data.new_password) ? data.new_password[0] : data.new_password;
      } else if (data.confirm_password) {
        errorMsg = Array.isArray(data.confirm_password)
          ? data.confirm_password[0]
          : data.confirm_password;
      } else if (data.error) {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      let errorMsg = 'Failed to change password.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.old_password) {
        errorMsg = Array.isArray(data.old_password) ? data.old_password[0] : data.old_password;
      } else if (data.new_password) {
        errorMsg = Array.isArray(data.new_password) ? data.new_password[0] : data.new_password;
      } else if (data.confirm_password) {
        errorMsg = Array.isArray(data.confirm_password)
          ? data.confirm_password[0]
          : data.confirm_password;
      } else if (data.error) {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      throw new Error(data.detail || data.error || 'Failed to verify MFA code.');
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      throw new Error(data.detail || data.error || 'Failed to initiate MFA setup.');
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      throw new Error(data.detail || data.error || 'Failed to confirm MFA setup.');
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      throw new Error(data.detail || data.error || 'Failed to disable MFA.');
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      let errorMsg = data.detail || data.error || 'Failed to generate invitation link.';
      throw new Error(errorMsg);
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
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      const data = error.response.data;
      return data || { valid: false, detail: 'Invalid or expired invitation link.' };
    }
  },

  /**
   * Register a new Student/User account against Django REST backend (/api/accounts/register/)
   */
  register: async ({ email, full_name, phone_number, password, confirm_password, invite_token }) => {
    try {
      const response = await api.post('/accounts/register/', {
        email,
        full_name,
        phone_number: phone_number ? phone_number.trim() : undefined,
        password,
        confirm_password,
        invite_token: invite_token || undefined,
      });
      return response.data;
    } catch (error) {
      if (error.response && error.response.status === 429) {
        throw new Error('Too many attempts — please wait a moment and try again.');
      }
      if (!error.response) {
        throw new Error('Unable to connect to the server. Please ensure the backend is running.');
      }
      throw new Error(formatErrorResponse(error.response.data, 'Registration failed. Please check the provided information.', error.response.status));
    }
  },
};

export default authService;


