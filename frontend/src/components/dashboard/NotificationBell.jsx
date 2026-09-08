import React, { useState, useEffect, useRef } from 'react';
import { notificationService } from '../../services/notificationService';

export default function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef(null);

  // Fetch unread count
  const fetchUnreadCount = async () => {
    try {
      const data = await notificationService.getUnreadCount();
      setUnreadCount(data.count || 0);
    } catch (err) {
      console.error('Failed to fetch unread notification count:', err);
    }
  };

  // Fetch notification list
  const fetchNotificationsList = async () => {
    setLoading(true);
    try {
      const data = await notificationService.getNotifications();
      // Django REST pagination returns results array or direct array
      const list = data.results || data;
      setNotifications(list);
    } catch (err) {
      console.error('Failed to fetch notifications list:', err);
    } finally {
      setLoading(false);
    }
  };

  // 45-second polling setup with clean teardown on unmount (Requirement 8)
  useEffect(() => {
    fetchUnreadCount();

    const intervalId = setInterval(() => {
      fetchUnreadCount();
    }, 45000);

    return () => {
      clearInterval(intervalId);
    };
  }, []);

  // Fetch list whenever dropdown opens
  useEffect(() => {
    if (isOpen) {
      fetchNotificationsList();
    }
  }, [isOpen]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  // Mark single item read
  const handleMarkAsRead = async (item) => {
    if (!item.is_read) {
      try {
        await notificationService.markAsRead(item.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === item.id ? { ...n, is_read: true } : n))
        );
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch (err) {
        console.error('Failed to mark notification as read:', err);
      }
    }
  };

  // Bulk mark all as read
  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  // Delete/dismiss notification
  const handleDelete = async (e, id, isRead) => {
    e.stopPropagation();
    try {
      await notificationService.deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      if (!isRead) {
        setUnreadCount((prev) => Math.max(0, prev - 1));
      }
    } catch (err) {
      console.error('Failed to delete notification:', err);
    }
  };

  const formatTimestamp = (isoString) => {
    if (!isoString) return '';
    const date = new Date(isoString);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="notification-bell-container" ref={dropdownRef}>
      <button
        type="button"
        className="notification-bell-btn"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Notifications"
      >
        <svg
          className="notification-icon"
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {unreadCount > 0 && (
          <span className="notification-badge">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="notification-dropdown">
          <div className="notification-dropdown-header">
            <h3 className="notification-title">Notifications</h3>
            {unreadCount > 0 && (
              <button
                type="button"
                className="mark-all-read-btn"
                onClick={handleMarkAllRead}
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="notification-dropdown-body">
            {loading ? (
              <div className="notification-loading">Loading notifications...</div>
            ) : notifications.length === 0 ? (
              <div className="notification-empty">No notifications yet.</div>
            ) : (
              notifications.map((item) => (
                <div
                  key={item.id}
                  className={`notification-item ${!item.is_read ? 'unread' : ''}`}
                  onClick={() => handleMarkAsRead(item)}
                >
                  <div className="notification-item-content">
                    <div className="notification-item-title-row">
                      <span className="item-title">{item.title}</span>
                      <span className="item-time">
                        {formatTimestamp(item.created_at)}
                      </span>
                    </div>
                    <p className="item-message">{item.message}</p>
                  </div>
                  <button
                    type="button"
                    className="notification-delete-btn"
                    onClick={(e) => handleDelete(e, item.id, item.is_read)}
                    title="Dismiss"
                  >
                    &times;
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
