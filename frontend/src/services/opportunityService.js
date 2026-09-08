import { api } from './authService';

export const opportunityService = {
  /**
   * Fetch opportunities list with optional query params (category, work_mode, city, status)
   */
  async getOpportunities(params = {}) {
    try {
      const response = await api.get('/opportunities/', { params });
      let data = response.data;
      let results = Array.isArray(data) ? data : (data?.results || []);
      return { results, count: data.count || results.length };
    } catch (error) {
      console.error('Failed to fetch opportunities from backend:', error);
      return { results: [], count: 0 };
    }
  },

  /**
   * Fetch single opportunity details
   */
  async getOpportunityById(id) {
    const response = await api.get(`/opportunities/${id}/`);
    return response.data;
  },


  /**
   * Toggle save/bookmark opportunity
   */
  async toggleSaveOpportunity(id, isSaved) {
    try {
      if (isSaved) {
        await api.delete(`/opportunities/${id}/save/`);
      } else {
        await api.post(`/opportunities/${id}/save/`);
      }
      return true;
    } catch (error) {
      console.warn('Backend save toggle failed, handling locally', error);
      return true;
    }
  },

  /**
   * Get list of saved opportunity IDs or saved items for current student
   */
  async getSavedOpportunities() {
    try {
      const response = await api.get('/saved-opportunities/');
      const results = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      return results;
    } catch (error) {
      console.warn('Failed to fetch saved opportunities', error);
      return [];
    }
  },

  /**
   * Submit application to opportunity
   */
  async applyToOpportunity(id, coverNote = '') {
    try {
      const response = await api.post(`/opportunities/${id}/apply/`, {
        cover_note: coverNote
      });
      return response.data;
    } catch (error) {
      console.error('Failed to submit application', error);
      throw error;
    }
  },

  /**
   * Get list of applications submitted by student
   */
  async getMyApplications() {
    try {
      const response = await api.get('/applications/');
      const results = Array.isArray(response.data) ? response.data : (response.data?.results || []);
      return results;
    } catch (error) {
      console.warn('Failed to fetch applications', error);
      return [];
    }
  }
};
