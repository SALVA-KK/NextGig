import React, { useState } from 'react';
import Sidebar from './Sidebar';
import DashboardHeader from './DashboardHeader';

/**
 * DashboardLayout - Master layout wrapper for Student Workspace.
 * Renders Sidebar + Header + responsive content area.
 */
export default function DashboardLayout({ children, activeTab, setActiveTab }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="dashboard-layout">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />
      
      <div className="dashboard-main-wrapper">
        <DashboardHeader
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onToggleSidebar={() => setSidebarOpen(prev => !prev)}
        />
        <main className="dashboard-content">{children}</main>
      </div>
    </div>
  );
}
