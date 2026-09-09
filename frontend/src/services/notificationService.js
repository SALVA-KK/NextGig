import { api } from './authService';

export const notificationService = {
  /**
   * Fetch paginated list of notifications for authenticated user
   */
  getNotifications: async (isRead = null, page = 1) => {
    try {
      const params = { page };
      if (isRead !== null) {
        params.is_read = isRead;
      }
      const response = await api.get('/notifications/', { params });
      return response.data;
    } catch (error) {
      console.error('[notificationService] getNotifications error:', error);
      throw error;
    }
  },

  /**
   * Fetch unread notification count
   */
  getUnreadCount: async () => {
    try {
      const response = await api.get('/notifications/unread-count/');
      return response.data;
    } catch (error) {
      console.error('[notificationService] getUnreadCount error:', error);
      throw error;
    }
  },

  /**
   * Mark a single notification as read (idempotent)
   */
  markAsRead: async (id) => {
    try {
      const response = await api.patch(`/notifications/${id}/read/`);
      return response.data;
    } catch (error) {
      console.error('[notificationService] markAsRead error:', error);
      throw error;
    }
  },

  /**
   * Bulk mark all notifications as read
   */
  markAllAsRead: async () => {
    try {
      const response = await api.post('/notifications/mark-all-read/');
      return response.data;
    } catch (error) {
      console.error('[notificationService] markAllAsRead error:', error);
      throw error;
    }
  },

  /**
   * Delete / dismiss a notification
   */
  deleteNotification: async (id) => {
    try {
      const response = await api.delete(`/notifications/${id}/`);
      return response.data;
    } catch (error) {
      console.error('[notificationService] deleteNotification error:', error);
      throw error;
    }
  },
};

export default notificationService;
