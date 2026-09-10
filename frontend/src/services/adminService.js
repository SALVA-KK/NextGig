import { api } from './authService';

export const adminService = {
  /**
   * Get list of pending provider profile verification requests
   */
  async getPendingProviders(params = {}) {
    const response = await api.get('/admin/providers/pending/', { params });
    const data = response.data;
    const results = Array.isArray(data) ? data : (data?.results || []);
    return {
      results,
      count: data.count ?? results.length,
      next: data.next || null,
      previous: data.previous || null,
    };
  },

  /**
   * Verify or un-verify a provider profile
   */
  async verifyProvider(id, isVerified = true) {
    const response = await api.patch(`/admin/providers/${id}/verify/`, { is_verified: isVerified });
    return response.data;
  },

  /**
   * Get paginated list of users with optional role and search filters
   */
  async getUsers(params = {}) {
    const response = await api.get('/admin/users/', { params });
    const data = response.data;
    const results = Array.isArray(data) ? data : (data?.results || []);
    return {
      results,
      count: data.count ?? results.length,
      next: data.next || null,
      previous: data.previous || null,
    };
  },

  /**
   * Toggle user active status (activate/deactivate)
   */
  async toggleUserActive(id) {
    const response = await api.patch(`/admin/users/${id}/toggle-active/`);
    return response.data;
  },

  /**
   * Get all opportunities regardless of status with optional status and search filters
   */
  async getOpportunities(params = {}) {
    const response = await api.get('/admin/opportunities/', { params });
    const data = response.data;
    const results = Array.isArray(data) ? data : (data?.results || []);
    return {
      results,
      count: data.count ?? results.length,
      next: data.next || null,
      previous: data.previous || null,
    };
  },

  /**
   * Force close an opportunity listing
   */
  async forceCloseOpportunity(id) {
    const response = await api.patch(`/admin/opportunities/${id}/force-close/`);
    return response.data;
  },

  /**
   * Reopen a closed or force-closed opportunity listing
   */
  async reopenOpportunity(id) {
    const response = await api.patch(`/admin/opportunities/${id}/reopen/`);
    return response.data;
  },

  /**
   * Delete an opportunity listing (moderation)
   */
  async deleteOpportunity(id) {
    const response = await api.delete(`/admin/opportunities/${id}/`);
    return response.data;
  },

  /**
   * Get paginated audit logs of administrative actions
   */
  async getAuditLog(params = {}) {
    const response = await api.get('/admin/audit-log/', { params });
    const data = response.data;
    const results = Array.isArray(data) ? data : (data?.results || []);
    return {
      results,
      count: data.count ?? results.length,
      next: data.next || null,
      previous: data.previous || null,
    };
  }
};
