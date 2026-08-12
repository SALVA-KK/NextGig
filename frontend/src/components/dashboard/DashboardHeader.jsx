import React from 'react';
import { authService } from '../../services/authService';

export default function DashboardHeader({ title = 'Dashboard' }) {
  const user = authService.getCurrentUser();

  // Extract display name or fallback to email / username / User
  const displayName =
    user?.full_name ||
    user?.first_name ||
    user?.email ||
    user?.username ||
    'User';

  const displayEmail = user?.email && displayName !== user.email ? user.email : null;
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <header className="dashboard-header-bar">
      <h1 className="dashboard-header-title">{title}</h1>
      <div className="dashboard-header-user">
        <div className="user-avatar-badge">{initial}</div>
        <div className="user-info-text">
          <span className="user-name">{displayName}</span>
          {displayEmail && <span className="user-email">{displayEmail}</span>}
        </div>
      </div>
    </header>
  );
}
