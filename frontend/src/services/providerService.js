import { api } from './authService';

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
      const response = await api.patch('/accounts/provider-profile/', profileData);
      return response.data;
    } catch (error) {
      console.error('[providerService] updateProviderProfile error:', error);
      throw error;
    }
  },
};

export default providerService;
