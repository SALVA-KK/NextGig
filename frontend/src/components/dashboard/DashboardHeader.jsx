import { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import NotificationBell from './NotificationBell';

export default function DashboardHeader({
  activeTab = 'opportunities',
  setActiveTab,
  onToggleSidebar
}) {
  const navigate = useNavigate();
  const user = authService.getCurrentUser();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  const displayName =
    user?.full_name ||
    user?.first_name ||
    user?.email?.split('@')[0] ||
    user?.username ||
    'Student';

  const userEmail = user?.email || '';
  const initial = displayName.charAt(0).toUpperCase();

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };

    // Close dropdown on Escape key
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  const handleLogout = async () => {
    setDropdownOpen(false);
    await authService.logout();
    navigate('/login', { replace: true });
  };

  const handleDropdownNavigate = (tabName, routePath) => {
    setDropdownOpen(false);
    if (tabName && setActiveTab) {
      setActiveTab(tabName);
    }
    if (routePath) {
      navigate(routePath);
    }
  };

  const isProvider = user?.role === 'provider';
  const isAdmin = user?.role === 'admin';
  const brandLink = isAdmin ? '/admin' : isProvider ? '/provider-dashboard' : '/dashboard';

  const handleNavClick = (tabName) => {
    if (setActiveTab) setActiveTab(tabName);
    const targetPath = isProvider ? '/provider-dashboard' : '/dashboard';
    if (location.pathname !== targetPath) {
      navigate(targetPath);
    }
  };

  return (
    <header className="header-bar">
      <div className="header-left">
        <button 
          className="mobile-menu-toggle" 
          onClick={onToggleSidebar}
          aria-label="Toggle Navigation Menu"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>

        <Link to={brandLink} className="header-brand">
          <div className="header-logo">N</div>
          <span className="header-brand-title">NextGig</span>
        </Link>

        {setActiveTab && !isProvider && (
          <nav className="header-quick-nav">
            <button
              onClick={() => handleNavClick('opportunities')}
              className={`header-nav-btn ${activeTab === 'opportunities' ? 'active' : ''}`}
            >
              Explore
            </button>
            <button
              onClick={() => handleNavClick('collaborations')}
              className={`header-nav-btn ${activeTab === 'collaborations' ? 'active' : ''}`}
            >
              Find Students
            </button>
            <button
              onClick={() => handleNavClick('saved')}
              className={`header-nav-btn ${activeTab === 'saved' ? 'active' : ''}`}
            >
              Saved
            </button>
            <button
              onClick={() => handleNavClick('applications')}
              className={`header-nav-btn ${activeTab === 'applications' ? 'active' : ''}`}
            >
              Applications
            </button>
          </nav>
        )}
      </div>


      <div className="header-right">
        <NotificationBell />
        
        {/* User Account Dropdown Trigger */}
        <div className="header-user-dropdown-container" ref={dropdownRef}>
          <button 
            type="button"
            className={`header-user-profile-btn ${dropdownOpen ? 'open' : ''}`}
            onClick={() => setDropdownOpen(prev => !prev)}
            aria-expanded={dropdownOpen}
            aria-label="User Account Menu"
          >
            <div className="user-avatar">{initial}</div>
            <span className="user-name-text">{displayName}</span>
            <svg 
              className={`dropdown-caret ${dropdownOpen ? 'rotated' : ''}`} 
              width="14" 
              height="14" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke="currentColor" 
              strokeWidth="2"
            >
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </button>

          {/* Account Dropdown Menu */}
          {dropdownOpen && (
            <div className="user-dropdown-menu">
              <div className="dropdown-header-info">
                <span className="dropdown-user-name">{displayName}</span>
                {userEmail && <span className="dropdown-user-email">{userEmail}</span>}
              </div>

              <div className="dropdown-items-list">
                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => handleDropdownNavigate(null, '/profile')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                  </svg>
                  Profile & Resume
                </button>

                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => handleDropdownNavigate('applications', '/dashboard')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                  My Applications
                </button>

                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => handleDropdownNavigate('saved', '/dashboard')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                  </svg>
                  Saved Items
                </button>

                <button
                  type="button"
                  className="dropdown-item"
                  onClick={() => handleDropdownNavigate(null, '/profile')}
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                  </svg>
                  Account Settings
                </button>
              </div>

              <div className="dropdown-divider"></div>

              <button
                type="button"
                className="dropdown-item logout-item"
                onClick={handleLogout}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                  <polyline points="16 17 21 12 16 7"></polyline>
                  <line x1="21" y1="12" x2="9" y2="12"></line>
                </svg>
                Sign Out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
