import { api } from './authService';

/**
 * Service to interact with NextGig AI Assistant backend endpoint.
 */
export const assistantService = {
  /**
   * Send a chat message to the NextGig AI assistant.
   * @param {string} message - User message (1-500 chars)
   * @param {Array<{role: string, content: string}>} history - Previous message history (up to 50 items)
   * @returns {Promise<{reply: string, opportunities: Array}>}
   */
  sendMessage: async (message, history = []) => {
    try {
      const response = await api.post('/assistant/chat/', {
        message,
        history,
      });
      return response.data;
    } catch (error) {
      const status = error.response?.status || error.status;
      const detail = error.response?.data?.detail;

      let errorMessage = 'Something went wrong. Please try again.';
      if (status === 429) {
        errorMessage = "You're sending messages too quickly. Please wait a moment.";
      } else if (status === 400) {
        errorMessage = "Your message couldn't be sent. Try a shorter message.";
      } else if ((status === 502 || status === 503) && detail) {
        errorMessage = detail;
      } else if (detail) {
        errorMessage = detail;
      }

      const err = new Error(errorMessage);
      err.status = status;
      err.detail = detail;
      throw err;
    }
  },
};

export default assistantService;
