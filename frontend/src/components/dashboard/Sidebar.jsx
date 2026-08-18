import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = authService.isAdmin();

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login', { replace: true });
  };

  const adminNavItems = [
    { label: 'Dashboard', path: '/admin' },
    { label: 'Users', path: '/admin/users' },
    { label: 'Security', path: '/admin/security' },
    { label: 'Settings', path: '/admin/settings' },
  ];

  const userNavItems = [
    { label: 'Dashboard', path: '/dashboard' },
    { label: 'Profile', path: '/profile' },
    { label: 'Settings', path: '/settings' },
  ];

  const navItems = isAdmin ? adminNavItems : userNavItems;

  return (
    <aside className="sidebar">
      <div className="sidebar-top">
        {/* NextGig Branding */}
        <Link to={isAdmin ? '/admin' : '/dashboard'} className="sidebar-brand">
          <div className="brand-logo">N</div>
          <span className="brand-name">NextGig</span>
        </Link>

        {/* Minimal Navigation Items */}
        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.label}
                to={item.path}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Logout Button reusing existing authService.logout() */}
      <div className="sidebar-footer">
        <button onClick={handleLogout} className="btn-sidebar-logout" id="sidebar-logout-btn">
          Logout
        </button>
      </div>
    </aside>
  );
}
