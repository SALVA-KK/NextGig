import { api } from './authService';

export const peopleService = {
  /**
   * Search people with optional query parameters (q, page).
   * @param {Object} params - Query parameters (e.g., { q, page }).
   * @param {Object} [config] - Optional Axios request config.
   * @returns {Promise<{ results: Array, count: number, next: string|null, previous: string|null }>}
   */
  async searchPeople(params = {}, config = {}) {
    const response = await api.get('/accounts/people/', { params, ...config });
    const data = response.data;
    const results = Array.isArray(data) ? data : (data?.results || []);
    return {
      results,
      count: data?.count ?? results.length,
      next: data?.next || null,
      previous: data?.previous || null,
    };
  },
};
