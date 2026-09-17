import React from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import ProfileShell from '../../components/profile/ProfileShell';
import AdminProfileView from '../../components/profile/AdminProfileView';
import { authService } from '../../services/authService';

export default function Profile() {
  const userRole = authService.getUserRole() || 'student';

  if (userRole === 'admin') {
    return (
      <DashboardLayout activeTab="profile">
        <AdminProfileView />
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout activeTab="profile">
      <ProfileShell role={userRole} />
    </DashboardLayout>
  );
}
