import React from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';

export default function Sidebar({ isOpen, onClose, activeTab, setActiveTab }) {
  const navigate = useNavigate();
  const location = useLocation();
  const isAdmin = authService.isAdmin();

  const handleLogout = async () => {
    await authService.logout();
    navigate('/login', { replace: true });
  };

  return (
    <>
      {/* Backdrop for Mobile Sidebar Drawer */}
      {isOpen && <div className="sidebar-overlay" onClick={onClose}></div>}

      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-top">
          <div className="sidebar-brand-wrapper">
            <Link to={isAdmin ? '/admin' : '/dashboard'} className="sidebar-brand">
              <div className="brand-logo-sq">N</div>
              <div className="brand-text-block">
                <span className="brand-name">NextGig</span>
                <span className="brand-sub">Opportunity Hub</span>
              </div>
            </Link>
            <button className="sidebar-close-btn" onClick={onClose} aria-label="Close sidebar">×</button>
          </div>

          <nav className="sidebar-nav">
            <div className="nav-group-title">DISCOVERY</div>
            
            <button
              onClick={() => {
                if (setActiveTab) setActiveTab('opportunities');
                if (onClose) onClose();
              }}
              className={`sidebar-nav-btn ${activeTab === 'opportunities' ? 'active' : ''}`}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
              </svg>
              Explore Opportunities
            </button>

            <button
              onClick={() => {
                if (setActiveTab) setActiveTab('collaborations');
                if (onClose) onClose();
              }}
              className={`sidebar-nav-btn ${activeTab === 'collaborations' ? 'active' : ''}`}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
              </svg>
              Student Collaborations
            </button>

            <div className="nav-group-title">MY WORKSPACE</div>

            <button
              onClick={() => {
                if (setActiveTab) setActiveTab('saved');
                if (onClose) onClose();
              }}
              className={`sidebar-nav-btn ${activeTab === 'saved' ? 'active' : ''}`}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
              </svg>
              Saved Items
            </button>

            <button
              onClick={() => {
                if (setActiveTab) setActiveTab('applications');
                if (onClose) onClose();
              }}
              className={`sidebar-nav-btn ${activeTab === 'applications' ? 'active' : ''}`}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="16" y1="13" x2="8" y2="13"></line>
                <line x1="16" y1="17" x2="8" y2="17"></line>
              </svg>
              My Applications
            </button>

            <Link
              to="/profile"
              onClick={onClose}
              className={`sidebar-nav-btn ${location.pathname === '/profile' ? 'active' : ''}`}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              Profile & Resumes
            </Link>

            {isAdmin && (
              <Link to="/admin" onClick={onClose} className="sidebar-nav-btn admin-link">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                </svg>
                Admin Control
              </Link>
            )}
          </nav>
        </div>

        <div className="sidebar-footer">
          <button onClick={handleLogout} className="btn-sidebar-logout">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
              <polyline points="16 17 21 12 16 7"></polyline>
              <line x1="21" y1="12" x2="9" y2="12"></line>
            </svg>
            Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
