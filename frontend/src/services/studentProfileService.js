import { api, authService } from './authService.js';

export const studentProfileService = {
  async getStudentProfile() {
    return await authService.getStudentProfile();
  },

  async updateStudentProfile(profileData) {
    if (profileData instanceof FormData) {
      return await authService.updateStudentProfile(profileData);
    }
    const response = await api.patch('/accounts/student-profile/', profileData);
    return response.data;
  },

  async uploadProfilePicture(file) {
    const formData = new FormData();
    formData.append('profile_picture', file);
    return await authService.updateStudentProfile(formData);
  }
};

export default studentProfileService;
