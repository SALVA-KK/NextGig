import React from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import ChangePasswordCard from '../../components/profile/ChangePasswordCard';

export default function AdminDashboard() {
  return (
    <DashboardLayout title="Admin Dashboard">
      <div className="dashboard-welcome-section">
        <h2>Welcome back, Admin</h2>
        <p className="subtitle">Your administrator account is active.</p>
      </div>

      <div className="dashboard-cards-grid">
        <div className="dashboard-stat-card">
          <div className="stat-card-header">
            <span className="stat-label">Account Status</span>
            <span className="status-badge active">Active</span>
          </div>
          <p className="stat-value">Administrator Account</p>
        </div>

        <div className="dashboard-stat-card">
          <div className="stat-card-header">
            <span className="stat-label">MFA Status</span>
            <span className="status-badge enabled">Enabled</span>
          </div>
          <p className="stat-value">Multi-Factor Authentication Active</p>
        </div>
      </div>

      <div style={{ marginTop: '24px' }}>
        <ChangePasswordCard />
      </div>
    </DashboardLayout>
  );
}
