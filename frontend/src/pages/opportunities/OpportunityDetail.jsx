import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import { opportunityService } from '../../services/opportunityService';
import { authService } from '../../services/authService';

export default function OpportunityDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [opportunity, setOpportunity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Application & Saved states
  const [coverNote, setCoverNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [applySuccess, setApplySuccess] = useState(false);
  const [applyError, setApplyError] = useState(null);
  const [existingApplication, setExistingApplication] = useState(null);
  const [isSaved, setIsSaved] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);

  const isAuthenticated = authService.isAuthenticated();
  const currentUser = authService.getCurrentUser();
  const userRole = authService.getUserRole();
  const isStudent = userRole === 'student';

  // Check if current logged in user is the poster of this opportunity
  const isPoster = currentUser && opportunity && (
    (opportunity.poster?.id && currentUser.id === opportunity.poster.id) ||
    (opportunity.poster?.email && currentUser.email === opportunity.poster.email) ||
    currentUser.id === opportunity.poster
  );

  useEffect(() => {
    let isMounted = true;

    async function fetchData() {
      setLoading(true);
      setError(null);

      try {
        // Fetch opportunity details
        const oppData = await opportunityService.getOpportunityById(id);
        if (!isMounted) return;
        setOpportunity(oppData);

        // If authenticated student, fetch user's applications and saved list
        if (authService.isAuthenticated() && authService.getUserRole() === 'student') {
          try {
            const [myApps, savedList] = await Promise.all([
              opportunityService.getMyApplications(),
              opportunityService.getSavedOpportunities()
            ]);

            if (!isMounted) return;

            // Check if student already applied
            const foundApp = myApps.find(app => {
              const oppId = app.opportunity?.id || app.opportunity_id || app.id;
              return String(oppId) === String(id);
            });
            if (foundApp) {
              setExistingApplication(foundApp);
              setApplySuccess(true);
            }

            // Check if saved
            const isOppSaved = savedList.some(item => {
              const oppId = item.opportunity?.id || item.opportunity_id || item.id;
              return String(oppId) === String(id);
            });
            setIsSaved(isOppSaved);
          } catch (e) {
            console.warn('Failed to load user application/saved state:', e);
          }
        }
      } catch (err) {
        console.error('Failed to load opportunity details:', err);
        if (isMounted) {
          setError('Opportunity not found or failed to load. It may have been closed or removed.');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchData();

    return () => {
      isMounted = false;
    };
  }, [id]);

  // Handle Application Submit
  const handleApply = async (e) => {
    e.preventDefault();
    if (!isStudent) return;

    setSubmitting(true);
    setApplyError(null);

    try {
      const appData = await opportunityService.applyToOpportunity(id, coverNote);
      setExistingApplication(appData);
      setApplySuccess(true);
    } catch (err) {
      console.error('Apply error:', err);
      const errMsg = err?.response?.data?.detail || err?.response?.data?.error || err?.message || 'Failed to submit application. Please try again.';
      setApplyError(errMsg);
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Save Toggle
  const handleSaveToggle = async () => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    setSaveLoading(true);
    try {
      await opportunityService.toggleSaveOpportunity(id, isSaved);
      setIsSaved(!isSaved);
    } catch (err) {
      console.error('Save toggle error:', err);
    } finally {
      setSaveLoading(false);
    }
  };

  // Helper for category formatting
  const formatCategory = (cat) => {
    if (!cat) return 'Opportunity';
    const mapping = {
      part_time: 'Part-Time',
      internship: 'Internship',
      freelance: 'Freelance',
      startup_hiring: 'Startup Hiring',
      project_collaboration: 'Project Collaboration',
      tutoring: 'Tutoring',
      volunteer: 'Volunteer',
      event_based: 'Event Based'
    };
    return mapping[cat.toLowerCase()] || cat.replace('_', ' ').toUpperCase();
  };

  // Helper for pay formatting
  const formatPay = (pay_type, pay_amount) => {
    if (pay_type === 'unpaid') return 'Unpaid';
    if (!pay_amount) return pay_type ? pay_type.toUpperCase() : 'Competitive';
    const amountStr = `₹${Number(pay_amount).toLocaleString('en-IN')}`;
    if (pay_type === 'hourly') return `${amountStr} / hr`;
    if (pay_type === 'monthly') return `${amountStr} / month`;
    if (pay_type === 'stipend') return `${amountStr} stipend`;
    return amountStr;
  };

  // Content Renderer
  const renderContent = () => {
    if (loading) {
      return (
        <div style={{ maxWidth: '840px', margin: '40px auto', padding: '0 20px' }}>
          <div className="skeleton-card" style={{ height: '360px' }}>
            <div className="skeleton-line title" style={{ width: '60%' }}></div>
            <div className="skeleton-line subtitle" style={{ width: '40%' }}></div>
            <div className="skeleton-line tags" style={{ marginTop: '24px' }}></div>
          </div>
        </div>
      );
    }

    if (error || !opportunity) {
      return (
        <div style={{ maxWidth: '840px', margin: '40px auto', padding: '0 20px' }}>
          <div className="discovery-error-box" style={{ background: '#fff', borderRadius: '12px', padding: '32px', textAlign: 'center' }}>
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2" style={{ margin: '0 auto 12px' }}>
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            <h3 style={{ fontSize: '18px', fontWeight: '700', marginBottom: '8px' }}>Opportunity Not Found</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '20px' }}>{error || 'Unable to display opportunity details.'}</p>
            <button onClick={() => navigate(-1)} className="btn-secondary">
              ← Go Back
            </button>
          </div>
        </div>
      );
    }

    const {
      title,
      description,
      category,
      pay_type,
      pay_amount,
      work_mode,
      city,
      location_text,
      required_skills = [],
      vacancies,
      members_needed,
      deadline,
      poster,
      created_at,
      is_student_project
    } = opportunity;

    const posterName = poster?.full_name || poster?.first_name || poster?.email || 'Opportunity Creator';
    const initial = posterName.charAt(0).toUpperCase();
    const locationDisplay = location_text || (city ? `${city} · ${work_mode || ''}` : work_mode || 'Remote');
    const openSlots = members_needed || vacancies || 1;

    return (
      <div style={{ maxWidth: '880px', margin: '24px auto', padding: '0 20px 60px' }}>
        
        {/* Back Navigation Bar */}
        <div style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button
            onClick={() => navigate(-1)}
            className="btn-secondary"
            style={{ padding: '8px 16px', fontSize: '13px' }}
          >
            ← Back to Opportunities
          </button>

          {isAuthenticated && isStudent && (
            <button
              onClick={handleSaveToggle}
              disabled={saveLoading}
              className={`btn-secondary ${isSaved ? 'saved' : ''}`}
              style={{
                padding: '8px 16px',
                fontSize: '13px',
                borderColor: isSaved ? 'var(--accent-indigo)' : 'var(--border-color)',
                color: isSaved ? 'var(--accent-indigo)' : 'var(--text-main)'
              }}
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill={isSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" style={{ marginRight: '6px' }}>
                <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
              </svg>
              {isSaved ? 'Saved to Wishlist' : 'Bookmark'}
            </button>
          )}
        </div>

        {/* Main Card Container */}
        <div className="auth-card" style={{ padding: '36px 32px', boxShadow: 'var(--shadow-card-hover)', borderRadius: '16px' }}>
          
          {/* Header Badges */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginBottom: '16px' }}>
            <span className={`opp-category-badge cat-${category}`}>
              {formatCategory(category)}
            </span>
            {is_student_project && (
              <span className="modal-student-tag">
                Student Project
              </span>
            )}
            {work_mode && (
              <span className="opp-workmode-badge">
                <span className={`workmode-dot ${work_mode}`}></span>
                {work_mode.charAt(0).toUpperCase() + work_mode.slice(1)}
              </span>
            )}
          </div>

          {/* Title */}
          <h1 style={{ fontSize: '26px', fontWeight: '800', color: 'var(--text-main)', lineHeight: '1.3', marginBottom: '16px' }}>
            {title}
          </h1>

          {/* Poster info strip */}
          <div className="opp-provider-row" style={{ padding: '12px 16px', background: 'var(--bg-canvas)', borderRadius: '10px', border: '1px solid var(--border-color)', marginBottom: '24px' }}>
            <div className="provider-avatar large">{initial}</div>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-main)' }}>{posterName}</span>
              <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                Posted {created_at ? new Date(created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : 'Recently'}
              </span>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="modal-metrics-grid" style={{ marginBottom: '28px' }}>
            <div className="metric-box">
              <span className="metric-label">Location / Mode</span>
              <span className="metric-val">{locationDisplay}</span>
            </div>

            <div className="metric-box">
              <span className="metric-label">Compensation</span>
              <span className="metric-val">{formatPay(pay_type, pay_amount)}</span>
            </div>

            <div className="metric-box">
              <span className="metric-label">Open Positions</span>
              <span className="metric-val">{openSlots} {openSlots === 1 ? 'opening' : 'openings'}</span>
            </div>

            {deadline && (
              <div className="metric-box">
                <span className="metric-label">Deadline</span>
                <span className="metric-val">{new Date(deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
              </div>
            )}
          </div>

          {/* Description */}
          <div style={{ marginBottom: '28px' }}>
            <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)', marginBottom: '10px' }}>
              About this {is_student_project ? 'Project' : 'Opportunity'}
            </h3>
            <p style={{ fontSize: '15px', lineHeight: '1.6', color: '#334155', whiteSpace: 'pre-line' }}>
              {description}
            </p>
          </div>

          {/* Required Skills */}
          {required_skills && required_skills.length > 0 && (
            <div style={{ marginBottom: '32px' }}>
              <h3 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)', marginBottom: '12px' }}>
                Required Skills
              </h3>
              <div className="opp-skills-list" style={{ flexWrap: 'wrap', gap: '8px' }}>
                {required_skills.map((skill, index) => (
                  <span key={index} className="skill-tag" style={{ padding: '6px 14px', fontSize: '13px' }}>
                    {skill}
                  </span>
                ))}
              </div>
            </div>
          )}

          <hr style={{ border: 'none', borderTop: '1px solid var(--border-color)', margin: '32px 0' }} />

          {/* Action / Application Section */}
          <div style={{ background: 'var(--bg-canvas)', borderRadius: '12px', padding: '24px', border: '1px solid var(--border-color)' }}>
            
            {/* SCENARIO 1: Logged out user */}
            {!isAuthenticated && (
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <h4 style={{ fontSize: '16px', fontWeight: '700', marginBottom: '8px' }}>Interested in this opportunity?</h4>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '20px' }}>
                  Sign in or register a student account on NextGig to submit your application.
                </p>
                <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap' }}>
                  <Link to="/login" className="btn-primary" style={{ display: 'inline-flex', width: 'auto', textDecoration: 'none', padding: '10px 24px' }}>
                    Sign In to Apply
                  </Link>
                  <Link to="/register" className="btn-secondary" style={{ display: 'inline-flex', width: 'auto', textDecoration: 'none', padding: '10px 24px' }}>
                    Create Account
                  </Link>
                </div>
              </div>
            )}

            {/* SCENARIO 2: Opportunity Poster logged in */}
            {isAuthenticated && isPoster && (
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '6px 14px', background: '#e0f2fe', color: '#0369a1', borderRadius: '20px', fontSize: '13px', fontWeight: '600', marginBottom: '12px' }}>
                  You are the poster of this opportunity
                </div>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '16px' }}>
                  You cannot submit an application to your own listing. You can review applicants from your provider dashboard.
                </p>
                <Link to="/provider-dashboard" className="btn-secondary" style={{ display: 'inline-flex', width: 'auto', textDecoration: 'none', padding: '8px 20px' }}>
                  View Applicants in Provider Hub
                </Link>
              </div>
            )}

            {/* SCENARIO 3: Non-poster Provider or Admin logged in */}
            {isAuthenticated && !isPoster && !isStudent && (
              <div style={{ textAlign: 'center', padding: '12px 0' }}>
                <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>
                  Applications are reserved for student accounts. You are currently signed in as <strong>{userRole}</strong>.
                </p>
              </div>
            )}

            {/* SCENARIO 4: Student already applied */}
            {isAuthenticated && isStudent && applySuccess && (
              <div className="apply-success-box" style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: '10px', padding: '20px' }}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <div>
                  <strong style={{ fontSize: '16px', color: '#15803d' }}>Application Submitted!</strong>
                  <p style={{ fontSize: '14px', color: '#166534', marginTop: '4px' }}>
                    Status: <span style={{ textTransform: 'uppercase', fontWeight: '700' }}>{(existingApplication?.status || 'applied').replace('_', ' ')}</span>
                  </p>
                  <p style={{ fontSize: '13px', color: '#166534', marginTop: '4px' }}>
                    The poster has been notified. You can track updates under <strong>My Applications</strong> in your dashboard.
                  </p>
                </div>
              </div>
            )}

            {/* SCENARIO 5: Student logged in and hasn't applied */}
            {isAuthenticated && isStudent && !applySuccess && (
              <form onSubmit={handleApply} className="apply-form">
                <h4 style={{ fontSize: '16px', fontWeight: '700', color: 'var(--text-main)', marginBottom: '12px' }}>
                  {is_student_project ? 'Connect & Join Project' : 'Submit Application'}
                </h4>

                {applyError && (
                  <div className="apply-error-banner" style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', padding: '12px', borderRadius: '8px', fontSize: '14px', marginBottom: '16px' }}>
                    {applyError}
                  </div>
                )}

                <div className="form-group" style={{ marginBottom: '20px' }}>
                  <label htmlFor="cover-note-detail" style={{ fontSize: '14px', fontWeight: '600', color: 'var(--text-main)', marginBottom: '6px' }}>
                    Note / Introduction (Optional)
                  </label>
                  <textarea
                    id="cover-note-detail"
                    rows="4"
                    className="form-textarea"
                    placeholder="Briefly introduce yourself, share relevant projects, or explain why you'd like to collaborate..."
                    value={coverNote}
                    onChange={(e) => setCoverNote(e.target.value)}
                  />
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary"
                  style={{ width: '100%', padding: '12px 24px', fontSize: '15px', fontWeight: '700' }}
                >
                  {submitting ? 'Submitting Application...' : is_student_project ? 'Send Teammate Request' : 'Submit Application'}
                </button>
              </form>
            )}

          </div>

        </div>
      </div>
    );
  };

  // Wrap in DashboardLayout if logged in, otherwise render clean header
  if (isAuthenticated) {
    return (
      <DashboardLayout activeTab="opportunities">
        {renderContent()}
      </DashboardLayout>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-canvas)' }}>
      {/* Public Header */}
      <header className="header-bar">
        <div className="header-left">
          <Link to="/" className="header-brand">
            <div className="header-logo">N</div>
            <span className="header-brand-title">NextGig</span>
          </Link>
        </div>
        <div className="header-right" style={{ gap: '12px' }}>
          <Link to="/login" className="btn-secondary-link">
            Sign In
          </Link>
          <Link to="/register" className="btn-primary-sm">
            Get Started
          </Link>
        </div>
      </header>
      <main>{renderContent()}</main>
    </div>
  );
}
