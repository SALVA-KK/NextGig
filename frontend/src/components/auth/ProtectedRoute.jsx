import React from 'react';
import { Navigate } from 'react-router-dom';
import { authService } from '../../services/authService';

/**
 * Route protection wrapper component.
 * Redirects unauthenticated users (missing access_token in localStorage) to /login.
 * Optional allowedRoles prop restricts access by user role (e.g. allowedRoles={['admin']}).
 * Non-authorized users are redirected to /dashboard.
 */
export default function ProtectedRoute({ children, allowedRoles }) {
  const token = localStorage.getItem('access_token');
  const user = authService.getCurrentUser();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && allowedRoles.length > 0) {
    const userRole = user?.role;
    if (!userRole || !allowedRoles.includes(userRole)) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return children;
}
