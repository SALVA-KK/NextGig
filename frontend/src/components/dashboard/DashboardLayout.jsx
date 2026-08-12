import React from 'react';
import Sidebar from './Sidebar';
import DashboardHeader from './DashboardHeader';

/**
 * DashboardLayout - Reusable foundation component.
 * Renders Sidebar + DashboardHeader + main children content area.
 */
export default function DashboardLayout({ children, title }) {
  return (
    <div className="dashboard-layout">
      <Sidebar />
      <div className="dashboard-main-wrapper">
        <DashboardHeader title={title} />
        <main className="dashboard-content">{children}</main>
      </div>
    </div>
  );
}
