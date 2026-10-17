import { api } from './authService';

export const chatService = {
  /**
   * Fetch paginated conversations for the current user.
   * @param {number} [page=1]
   */
  async getConversations(page = 1) {
    const response = await api.get('/chat/conversations/', { params: { page } });
    return response.data;
  },

  /**
   * Fetch single conversation details.
   * @param {number} conversationId
   */
  async getConversation(conversationId) {
    const response = await api.get(`/chat/conversations/${conversationId}/`);
    return response.data;
  },

  /**
   * Create or fetch an existing conversation tied to an application.
   * @param {number} applicationId
   */
  async getOrCreateConversation(applicationId) {
    const response = await api.post('/chat/conversations/', { application_id: applicationId });
    return response.data;
  },

  /**
   * Fetch paginated messages for a conversation.
   * @param {number} conversationId
   * @param {number} [page=1]
   * @param {string} [order='desc']
   */
  async getMessages(conversationId, page = 1, order = 'desc') {
    const params = { page };
    if (order) params.order = order;
    const response = await api.get(`/chat/conversations/${conversationId}/messages/`, { params });
    return response.data;
  },

  /**
   * Send a new message to a conversation.
   * @param {number} conversationId
   * @param {string} body
   */
  async sendMessage(conversationId, body) {
    const response = await api.post(`/chat/conversations/${conversationId}/messages/`, { body });
    return response.data;
  },

  /**
   * Mark all unread messages from the other user in this conversation as read.
   * @param {number} conversationId
   */
  async markAsRead(conversationId) {
    const response = await api.post(`/chat/conversations/${conversationId}/read/`);
    return response.data;
  },

  /**
   * Get total unread chat messages for the current user.
   */
  async getUnreadCount() {
    const response = await api.get('/chat/unread-count/');
    return response.data;
  },
};

export default chatService;
