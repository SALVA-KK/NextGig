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

  requestPhoneOtp: async (phone_number) => {
    throw new Error('API integration pending');
  },

  verifyPhoneOtp: async (phone_number, otp) => {
    throw new Error('API integration pending');
  },
};
