import { useEffect, useRef } from 'react';

/**
 * Custom React hook for real-time notification push over WebSocket.
 * 
 * Requirements:
 * - Native browser WebSocket only (zero new npm packages).
 * - Reads access token from localStorage at EACH (re)connect attempt.
 * - On close code 4401: stops reconnect loop until the token changes or user re-authenticates.
 * - Exponential backoff capped at 30 seconds for network disconnects.
 * - Clean teardown on unmount to prevent React StrictMode duplicate connections.
 * 
 * @param {Function} onNotification - Callback invoked when a new notification is pushed.
 * @param {Function} [onChatMessage] - Optional callback invoked when a real-time chat message is pushed.
 */
export function useNotificationSocket(onNotification, onChatMessage) {
  const onNotificationRef = useRef(onNotification);
  const onChatMessageRef = useRef(onChatMessage);
  const socketRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const retryCountRef = useRef(0);
  const stoppedDueTo4401Ref = useRef(false);
  const lastFailedTokenRef = useRef(null);

  // Keep latest callback ref without restarting effect
  useEffect(() => {
    onNotificationRef.current = onNotification;
  }, [onNotification]);

  useEffect(() => {
    onChatMessageRef.current = onChatMessage;
  }, [onChatMessage]);

  useEffect(() => {
    let isUnmounted = false;

    const buildWsUrl = (token) => {
      const apiBase = import.meta.env.VITE_API_BASE_URL || window.location.origin;
      let urlObj;
      try {
        urlObj = new URL(apiBase);
      } catch {
        urlObj = new URL(apiBase, window.location.origin);
      }
      const wsProto = urlObj.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProto}//${urlObj.host}/ws/notifications/?token=${encodeURIComponent(token)}`;
    };

    const connect = () => {
      if (isUnmounted) return;

      // Read fresh token from localStorage at EACH connect attempt
      const currentToken = localStorage.getItem('access_token');

      if (!currentToken) {
        // No token available; do not connect
        return;
      }

      // If we previously stopped due to 4401, only resume if token has changed
      if (stoppedDueTo4401Ref.current && currentToken === lastFailedTokenRef.current) {
        return;
      }

      // Reset 4401 halt if token changed
      if (stoppedDueTo4401Ref.current && currentToken !== lastFailedTokenRef.current) {
        stoppedDueTo4401Ref.current = false;
        lastFailedTokenRef.current = null;
        retryCountRef.current = 0;
      }

      try {
        const wsUrl = buildWsUrl(currentToken);
        const ws = new WebSocket(wsUrl);
        socketRef.current = ws;

        ws.onopen = () => {
          if (isUnmounted) {
            ws.close(1000, 'Unmounted');
            return;
          }
          retryCountRef.current = 0;
          stoppedDueTo4401Ref.current = false;
          lastFailedTokenRef.current = null;
        };

        ws.onmessage = (event) => {
          if (isUnmounted) return;
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'notification' && data.notification && onNotificationRef.current) {
              onNotificationRef.current(data.notification);
            } else if (
              (data.type === 'chat_message' || data.type === 'chat_message_deleted') &&
              data.message &&
              onChatMessageRef.current
            ) {
              onChatMessageRef.current(data.message, data.type);
            }
          } catch (err) {
            console.error('[NotificationWS] Failed to parse message JSON:', err);
          }
        };

        ws.onerror = () => {
          // Handled via onclose
        };

        ws.onclose = (event) => {
          if (isUnmounted) return;

          // Requirement 3: On close code 4401, stop looping and do not reconnect
          // until the token changes or the user logs in again.
          if (event.code === 4401) {
            stoppedDueTo4401Ref.current = true;
            lastFailedTokenRef.current = currentToken;
            console.warn('[NotificationWS] Connection rejected with 4401 (invalid/expired token). Reconnect halted until token refresh.');
            return;
          }

          // If closed cleanly (1000) by client or normal shutdown, do not automatically retry
          if (event.code === 1000) {
            return;
          }

          // Exponential backoff capped at 30 seconds
          const backoffDelay = Math.min(1000 * Math.pow(2, retryCountRef.current), 30000);
          retryCountRef.current += 1;

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, backoffDelay);
        };
      } catch (err) {
        console.error('[NotificationWS] Connection attempt failed:', err);
      }
    };

    // Initial connection attempt
    connect();

    // Listen to storage events so when a new access token is written,
    // we automatically attempt to connect if previously halted by 4401
    const handleStorageChange = (e) => {
      if (e.key === 'access_token' && e.newValue) {
        if (stoppedDueTo4401Ref.current || !socketRef.current || socketRef.current.readyState === WebSocket.CLOSED) {
          stoppedDueTo4401Ref.current = false;
          lastFailedTokenRef.current = null;
          retryCountRef.current = 0;
          if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
          connect();
        }
      }
    };
    window.addEventListener('storage', handleStorageChange);

    // Periodic check (every 10s) to see if token changed in same tab after 4401
    const tokenCheckInterval = setInterval(() => {
      const token = localStorage.getItem('access_token');
      if (token && stoppedDueTo4401Ref.current && token !== lastFailedTokenRef.current) {
        stoppedDueTo4401Ref.current = false;
        lastFailedTokenRef.current = null;
        retryCountRef.current = 0;
        connect();
      }
    }, 10000);

    return () => {
      isUnmounted = true;
      window.removeEventListener('storage', handleStorageChange);
      clearInterval(tokenCheckInterval);
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (socketRef.current) {
        socketRef.current.close(1000, 'Unmounted');
      }
    };
  }, []);
}

export default useNotificationSocket;
