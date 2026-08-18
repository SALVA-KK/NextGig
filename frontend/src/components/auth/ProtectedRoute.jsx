import React, { useState, useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { authService } from '../../services/authService';

/**
 * Dynamic route protection wrapper component.
 * Validates authentication token on every render, location change, and browser back/forward navigation event.
 * Redirects unauthenticated users (missing access_token in localStorage) to /login.
 * Optional allowedRoles prop restricts access by user role (e.g. allowedRoles={['admin']}).
 */
export default function ProtectedRoute({ children, allowedRoles }) {
  const location = useLocation();
  const [authenticated, setAuthenticated] = useState(() => authService.isAuthenticated());

  useEffect(() => {
    // Re-check authentication status on location change or back/forward navigation
    const checkAuth = () => {
      const isAuth = authService.isAuthenticated();
      setAuthenticated(isAuth);
    };

    checkAuth();

    // Listen to browser back/forward navigation (pageshow & popstate)
    const handlePageShow = (event) => {
      // Re-validate session if restored from BFcache
      checkAuth();
    };

    window.addEventListener('pageshow', handlePageShow);
    window.addEventListener('popstate', checkAuth);

    return () => {
      window.removeEventListener('pageshow', handlePageShow);
      window.removeEventListener('popstate', checkAuth);
    };
  }, [location]);

  if (!authenticated || !authService.isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  const user = authService.getCurrentUser();
  if (allowedRoles && allowedRoles.length > 0) {
    const userRole = user?.role;
    if (!userRole || !allowedRoles.includes(userRole)) {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return children;
}
