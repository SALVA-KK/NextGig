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
    <div className="dashboard-layout min-h-screen bg-slate-50 flex flex-col md:flex-row">
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />
      
      <div className="dashboard-main-wrapper flex-1 flex flex-col min-w-0 md:pl-64 min-h-screen">
        <DashboardHeader
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onToggleSidebar={() => setSidebarOpen(prev => !prev)}
        />
        <main className="dashboard-content flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}

