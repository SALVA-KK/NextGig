import { api } from './authService';

/**
 * Format DRF error response for resume API operations.
 */
const formatError = (error, fallbackMessage) => {
  if (!error.response) {
    return 'Something went wrong. Please check your internet connection and try again.';
  }
  const data = error.response.data;
  if (!data) return fallbackMessage;

  if (typeof data === 'string') return data;
  if (data.detail) return data.detail;
  if (data.file) {
    return Array.isArray(data.file) ? data.file.join(' ') : String(data.file);
  }
  if (data.non_field_errors) {
    return Array.isArray(data.non_field_errors) ? data.non_field_errors.join(' ') : String(data.non_field_errors);
  }
  if (typeof data === 'object') {
    const msgs = [];
    for (const [key, val] of Object.entries(data)) {
      const valStr = Array.isArray(val) ? val.join(' ') : String(val);
      msgs.push(`${key}: ${valStr}`);
    }
    if (msgs.length > 0) return msgs.join(' ');
  }
  return fallbackMessage;
};

export const resumeService = {
  /**
   * Get current authenticated student's resume metadata (/api/accounts/profile/resume/)
   */
  getResume: async () => {
    try {
      const response = await api.get('/accounts/profile/resume/');
      return response.data;
    } catch (error) {
      console.error('[resumeService] getResume error:', error);
      throw new Error(formatError(error, 'Failed to fetch resume details.'));
    }
  },

  /**
   * Upload or replace resume file (/api/accounts/profile/resume/)
   * Uses multipart/form-data payload.
   */
  uploadResume: async (file) => {
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await api.post('/accounts/profile/resume/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return response.data;
    } catch (error) {
      console.error('[resumeService] uploadResume error:', error);
      throw new Error(formatError(error, 'Resume upload failed. Please try again.'));
    }
  },

  /**
   * Delete current student's uploaded resume (/api/accounts/profile/resume/)
   */
  deleteResume: async () => {
    try {
      const response = await api.delete('/accounts/profile/resume/');
      return response.data;
    } catch (error) {
      console.error('[resumeService] deleteResume error:', error);
      throw new Error(formatError(error, 'Failed to delete resume.'));
    }
  },

  /**
   * Fetch resume file blob directly using authenticated Axios client
   */
  downloadResumeBlob: async () => {
    try {
      const response = await api.get('/accounts/profile/resume/download/', {
        responseType: 'blob',
      });
      return response;
    } catch (error) {
      console.error('[resumeService] downloadResumeBlob error:', error);
      throw new Error(formatError(error, 'Failed to download resume file.'));
    }
  },
};

export default resumeService;
