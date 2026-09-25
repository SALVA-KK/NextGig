import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';
import { getNavPermissions } from '../../utils/navigationConfig';

export default function Sidebar({ isOpen, onClose, activeTab, setActiveTab }) {
  const navigate = useNavigate();
  const location = useLocation();
  const rawAdmin = authService.isAdmin();
  const userRole = authService.getUserRole();
  const { isStudent, isProvider, isAdmin, canViewApplications, canViewSavedItems, profileLabel } =
    getNavPermissions(userRole, rawAdmin);

  const [studentOppOpen, setStudentOppOpen] = useState(true);
  const [providerOppOpen, setProviderOppOpen] = useState(true);

  const searchParams = new URLSearchParams(location.search);
  const currentSubTab = searchParams.get('subTab') || searchParams.get('tab') || 'all';

  const brandLink = isAdmin ? '/admin' : isProvider ? '/provider-dashboard' : '/dashboard';

  const handleTabClick = (tabName) => {
    if (setActiveTab) setActiveTab(tabName);
    const targetPath = isAdmin ? '/admin' : isProvider ? '/provider-dashboard' : '/dashboard';
    if (location.pathname !== targetPath) {
      navigate(targetPath);
    }
    if (onClose) onClose();
  };

  const handleStudentSubTabClick = (subTabVal) => {
    if (setActiveTab) setActiveTab('opportunities');
    const targetPath = `/dashboard?subTab=${subTabVal}`;
    navigate(targetPath);
    if (onClose) onClose();
  };

  return (
    <>
      {/* Backdrop for Mobile Sidebar Drawer */}
      {isOpen && <div className="sidebar-overlay" onClick={onClose}></div>}

      <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
        <div className="sidebar-top">
          <div className="sidebar-brand-wrapper">
            <Link to={brandLink} className="sidebar-brand">
              <div className="brand-logo-sq">N</div>
              <div className="brand-text-block">
                <span className="brand-name">NextGig</span>
                <span className="brand-sub">
                  {isAdmin ? 'Admin Hub' : isProvider ? 'Provider Hub' : 'Opportunity Hub'}
                </span>
              </div>
            </Link>
            <button className="sidebar-close-btn" onClick={onClose} aria-label="Close sidebar">×</button>
          </div>

          <nav className="sidebar-nav">
            {isAdmin ? (
              <>
                <div className="nav-group-title">ADMIN PANEL</div>

                <button
                  onClick={() => handleTabClick('dashboard')}
                  className={`sidebar-nav-btn ${activeTab === 'dashboard' || (!activeTab && location.pathname === '/admin') ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="7" height="7"></rect>
                    <rect x="14" y="3" width="7" height="7"></rect>
                    <rect x="14" y="14" width="7" height="7"></rect>
                    <rect x="3" y="14" width="7" height="7"></rect>
                  </svg>
                  Dashboard
                </button>

                <button
                  onClick={() => handleTabClick('providers')}
                  className={`sidebar-nav-btn ${activeTab === 'providers' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                  </svg>
                  Provider Verification
                </button>

                <button
                  onClick={() => handleTabClick('users')}
                  className={`sidebar-nav-btn ${activeTab === 'users' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                    <circle cx="9" cy="7" r="4"></circle>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                  </svg>
                  User Management
                </button>

                <button
                  onClick={() => handleTabClick('opportunities')}
                  className={`sidebar-nav-btn ${activeTab === 'opportunities' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                    <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
                  </svg>
                  Opportunity Moderation
                </button>

                <button
                  onClick={() => handleTabClick('audit')}
                  className={`sidebar-nav-btn ${activeTab === 'audit' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                    <polyline points="14 2 14 8 20 8"></polyline>
                  </svg>
                  Audit Trail
                </button>

                <button
                  onClick={() => handleTabClick('overview')}
                  className={`sidebar-nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                  </svg>
                  Account Settings
                </button>
              </>
            ) : isProvider ? (
              <>
                <div className="nav-group-title">PROVIDER PORTAL</div>

                <div className="nav-dropdown-group">
                  <button
                    onClick={() => setProviderOppOpen(prev => !prev)}
                    className={`sidebar-nav-btn w-full flex items-center justify-between ${
                      ['my-opportunities', 'post-opportunity', 'explore'].includes(activeTab) ? 'active' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
                      </svg>
                      <span>Opportunities</span>
                    </div>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      style={{ transform: providerOppOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
                    >
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </button>

                  {providerOppOpen && (
                    <div className="pl-6 flex flex-col gap-1 mt-1">
                      <button
                        onClick={() => handleTabClick('my-opportunities')}
                        className={`sidebar-nav-btn text-xs py-1.5 ${
                          activeTab === 'my-opportunities' ? 'font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-gray-800' : ''
                        }`}
                      >
                        My Opportunities
                      </button>

                      <button
                        onClick={() => handleTabClick('post-opportunity')}
                        className={`sidebar-nav-btn text-xs py-1.5 ${
                          activeTab === 'post-opportunity' ? 'font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-gray-800' : ''
                        }`}
                      >
                        Post Opportunity
                      </button>

                      <button
                        onClick={() => handleTabClick('explore')}
                        className={`sidebar-nav-btn text-xs py-1.5 ${
                          activeTab === 'explore' ? 'font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-gray-800' : ''
                        }`}
                      >
                        Other Opportunities
                      </button>
                    </div>
                  )}
                </div>

                <button
                  onClick={() => handleTabClick('applicants')}
                  className={`sidebar-nav-btn ${activeTab === 'applicants' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                    <circle cx="9" cy="7" r="4"></circle>
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                    <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                  </svg>
                  Applicants
                </button>

                <button
                  onClick={() => handleTabClick('saved')}
                  className={`sidebar-nav-btn ${activeTab === 'saved' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                  </svg>
                  Saved Items
                </button>

                <button
                  onClick={() => handleTabClick('profile')}
                  className={`sidebar-nav-btn ${activeTab === 'profile' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                  </svg>
                  Provider Profile
                </button>
              </>
            ) : (
              <>
                <div className="nav-group-title">DISCOVERY</div>

                <div className="nav-dropdown-group">
                  <button
                    onClick={() => setStudentOppOpen(prev => !prev)}
                    className={`sidebar-nav-btn w-full flex items-center justify-between ${
                      activeTab === 'opportunities' ? 'active' : ''
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
                        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
                      </svg>
                      <span>Opportunities</span>
                    </div>
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      style={{ transform: studentOppOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
                    >
                      <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                  </button>

                  {studentOppOpen && (
                    <div className="pl-6 flex flex-col gap-1 mt-1">
                      <button
                        onClick={() => handleStudentSubTabClick('all')}
                        className={`sidebar-nav-btn text-xs py-1.5 ${
                          activeTab === 'opportunities' && (currentSubTab === 'all' || !currentSubTab)
                            ? 'font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-gray-800'
                            : ''
                        }`}
                      >
                        All
                      </button>

                      <button
                        onClick={() => handleStudentSubTabClick('recommended')}
                        className={`sidebar-nav-btn text-xs py-1.5 flex items-center gap-1.5 ${
                          activeTab === 'opportunities' && currentSubTab === 'recommended'
                            ? 'font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-gray-800'
                            : ''
                        }`}
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                        </svg>
                        Recommended
                      </button>

                      <button
                        onClick={() => handleStudentSubTabClick('collaborations')}
                        className={`sidebar-nav-btn text-xs py-1.5 flex items-center gap-1.5 ${
                          activeTab === 'opportunities' && currentSubTab === 'collaborations'
                            ? 'font-bold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-gray-800'
                            : ''
                        }`}
                      >
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                          <circle cx="9" cy="7" r="4"></circle>
                          <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                          <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                        </svg>
                        Collaborations
                      </button>
                    </div>
                  )}
                </div>

                <div className="nav-group-title">MY WORKSPACE</div>

                {/* Saved Items: student role ONLY */}
                {canViewSavedItems && (
                  <button
                    onClick={() => handleTabClick('saved')}
                    className={`sidebar-nav-btn ${activeTab === 'saved' ? 'active' : ''}`}
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                    </svg>
                    Saved Items
                  </button>
                )}

                {/* My Applications: student role ONLY */}
                {canViewApplications && (
                  <button
                    onClick={() => handleTabClick('applications')}
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
                )}

                <Link
                  to="/profile"
                  onClick={onClose}
                  className={`sidebar-nav-btn ${location.pathname === '/profile' ? 'active' : ''}`}
                >
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                    <circle cx="12" cy="7" r="4"></circle>
                  </svg>
                  {profileLabel}
                </Link>
              </>
            )}
          </nav>
        </div>
      </aside>
    </>
  );
}
