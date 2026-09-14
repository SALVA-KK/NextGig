import React from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import ProfileShell from '../../components/profile/ProfileShell';
import { authService } from '../../services/authService';

export default function Profile() {
  const userRole = authService.getUserRole() || 'student';

  return (
    <DashboardLayout activeTab="profile">
      <ProfileShell role={userRole} />
    </DashboardLayout>
  );
}
