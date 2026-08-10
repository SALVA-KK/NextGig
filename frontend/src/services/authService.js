import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

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
      const data = error.response.data;
      let errorMsg = 'Login failed. Please check your credentials.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.non_field_errors) {
        errorMsg = Array.isArray(data.non_field_errors)
          ? data.non_field_errors[0]
          : data.non_field_errors;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.email) {
        errorMsg = Array.isArray(data.email) ? data.email[0] : data.email;
      } else if (data.password) {
        errorMsg = Array.isArray(data.password) ? data.password[0] : data.password;
      } else if (data.error) {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
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
      const data = error.response.data;
      let errorMsg = 'Failed to request OTP. Please check the phone number.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.phone_number) {
        errorMsg = Array.isArray(data.phone_number) ? data.phone_number[0] : data.phone_number;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.non_field_errors) {
        errorMsg = Array.isArray(data.non_field_errors)
          ? data.non_field_errors[0]
          : data.non_field_errors;
      } else if (data.error) {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
    }
  },

  /**
   * Verify phone login OTP against Django REST backend (/api/accounts/phone-login/verify-otp/)
   */
  verifyPhoneLoginOTP: async (phone_number, otp) => {
    try {
      const response = await api.post('/accounts/phone-login/verify-otp/', {
        phone_number,
        otp,
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
      let errorMsg = 'Invalid or expired OTP.';

      if (typeof data === 'string') {
        errorMsg = data;
      } else if (data.detail) {
        errorMsg = data.detail;
      } else if (data.otp) {
        errorMsg = Array.isArray(data.otp) ? data.otp[0] : data.otp;
      } else if (data.phone_number) {
        errorMsg = Array.isArray(data.phone_number) ? data.phone_number[0] : data.phone_number;
      } else if (data.non_field_errors) {
        errorMsg = Array.isArray(data.non_field_errors)
          ? data.non_field_errors[0]
          : data.non_field_errors;
      } else if (data.error) {
        errorMsg = data.error;
      }

      throw new Error(errorMsg);
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
   * Remove stored authentication tokens and user data from localStorage
   */
  logout: () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user');
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
};

