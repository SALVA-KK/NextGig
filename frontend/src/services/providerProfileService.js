import { api } from './authService.js';
import providerService from './providerService';

export const providerProfileService = {
  async getProviderProfile() {
    return await providerService.getProviderProfile();
  },

  async updateProviderProfile(profileData) {
    if (profileData instanceof FormData) {
      return await providerService.updateProviderProfile(profileData);
    }
    const response = await api.patch('/accounts/provider-profile/', profileData);
    return response.data;
  },

  async uploadProfilePicture(file) {
    const formData = new FormData();
    formData.append('profile_picture', file);
    return await providerService.updateProviderProfile(formData);
  }
};

export default providerProfileService;
