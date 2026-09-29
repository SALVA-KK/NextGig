import { api, formatErrorResponse } from './authService';

export const providerService = {
  /**
   * Fetch authenticated user's ProviderProfile
   */
  async getProviderProfile() {
    try {
      const response = await api.get('/accounts/provider-profile/');
      return response.data;
    } catch (error) {
      console.error('[providerService] getProviderProfile error:', error);
      throw error;
    }
  },

  /**
   * Update authenticated user's ProviderProfile
   */
  async updateProviderProfile(profileData) {
    try {
      const isFormData = typeof FormData !== 'undefined' && profileData instanceof FormData;
      const headers = isFormData ? { 'Content-Type': 'multipart/form-data' } : {};
      const response = await api.patch('/accounts/provider-profile/', profileData, { headers });
      return response.data;
    } catch (error) {
      console.error('[providerService] updateProviderProfile error:', error);
      if (!error.response) {
        throw new Error('Something went wrong. Please check your internet connection and try again.');
      }
      throw new Error(
        formatErrorResponse(
          error.response.data,
          "Couldn't update your profile picture. Please try a different image.",
          error.response.status
        )
      );
    }
  },
};

export default providerService;
