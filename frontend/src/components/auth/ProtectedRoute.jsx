import React from 'react';
import { Navigate } from 'react-router-dom';

/**
 * Route protection wrapper component.
 * Redirects unauthenticated users (missing access_token in localStorage) to /login.
 */
export default function ProtectedRoute({ children }) {
  const token = localStorage.getItem('access_token');

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
