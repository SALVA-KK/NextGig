import { useState, useEffect, useCallback } from 'react';
import { chatService } from '../services/chatService';

export function useChatUnreadCount() {
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchCount = useCallback(async () => {
    try {
      const data = await chatService.getUnreadCount();
      setUnreadCount(data.count ?? data.unread_total ?? 0);
    } catch {
      // Ignore network errors on background poll
    }
  }, []);

  useEffect(() => {
    fetchCount();

    const handleUpdate = () => {
      fetchCount();
    };

    window.addEventListener('chat:unread-updated', handleUpdate);

    const interval = setInterval(fetchCount, 45000);

    return () => {
      window.removeEventListener('chat:unread-updated', handleUpdate);
      clearInterval(interval);
    };
  }, [fetchCount]);

  return { unreadCount, refreshUnreadCount: fetchCount };
}

export default useChatUnreadCount;
