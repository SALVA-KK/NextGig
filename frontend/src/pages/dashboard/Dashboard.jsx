import React from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';

export default function Dashboard() {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();
  const token = localStorage.getItem('access_token');

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-card">
        {/* NextGig Branding Header & Logout Button */}
        <div className="dashboard-header">
          <div className="auth-brand" style={{ marginBottom: 0 }}>
            <div className="brand-logo">N</div>
            <span className="brand-name">NextGig</span>
          </div>
          <button onClick={handleLogout} className="btn-logout" id="logout-btn">
            Logout
          </button>
        </div>

        {/* Welcome Message */}
        <div className="dashboard-welcome">
          <h1 className="dashboard-title">Welcome to NextGig</h1>
          <p className="dashboard-subtitle">
            You are successfully authenticated and logged into your workspace.
          </p>
        </div>

        {/* Basic Authenticated-User Section */}
        <div className="user-profile-card">
          <div className="user-profile-header">
            <span className="badge-authenticated">Authenticated User</span>
          </div>
          <div className="user-profile-details">
            {user ? (
              <>
                {user.email && (
                  <div className="user-detail-row">
                    <span className="detail-label">Email:</span>
                    <span className="detail-value">{user.email}</span>
                  </div>
                )}
                {user.phone_number && (
                  <div className="user-detail-row">
                    <span className="detail-label">Phone:</span>
                    <span className="detail-value">{user.phone_number}</span>
                  </div>
                )}
                {user.username && (
                  <div className="user-detail-row">
                    <span className="detail-label">Username:</span>
                    <span className="detail-value">{user.username}</span>
                  </div>
                )}
                {user.first_name && (
                  <div className="user-detail-row">
                    <span className="detail-label">Name:</span>
                    <span className="detail-value">
                      {user.first_name} {user.last_name || ''}
                    </span>
                  </div>
                )}
              </>
            ) : (
              <div className="user-detail-row">
                <span className="detail-label">Session Status:</span>
                <span className="detail-value">Active JWT Session</span>
              </div>
            )}
            <div className="user-detail-row">
              <span className="detail-label">Access Token:</span>
              <span className="detail-value token-preview">
                {token ? `${token.substring(0, 20)}...` : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
