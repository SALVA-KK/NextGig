import React from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import InviteCard from '../../components/dashboard/InviteCard';

export default function UserDashboard() {
  return (
    <DashboardLayout title="User Dashboard">
      <div className="dashboard-welcome-section">
        <h2>Welcome back</h2>
        <p className="subtitle">Your NextGig workspace is ready.</p>
      </div>

      <div className="dashboard-cards-grid">
        <div className="dashboard-stat-card">
          <div className="stat-card-header">
            <span className="stat-label">Account Status</span>
            <span className="status-badge active">Active</span>
          </div>
          <p className="stat-value">Workspace Active</p>
        </div>

        <InviteCard />
      </div>
    </DashboardLayout>
  );
}
