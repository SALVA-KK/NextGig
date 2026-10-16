import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * OpportunityCard Component
 * Displays a clean, scannable opportunity listing card for jobs, internships, freelance, etc.
 */
export default function OpportunityCard({
  opportunity,
  isSaved,
  onSaveToggle,
  onSelect,
  application,
  onMessage,
  chatLoading
}) {
  const navigate = useNavigate();
  const {
    id,
    title,
    category,
    pay_type,
    pay_amount,
    work_mode,
    city,
    location_text,
    required_skills = [],
    vacancies,
    deadline,
    poster,
    created_at
  } = opportunity;

  // Format category display text
  const formatCategory = (cat) => {
    if (!cat) return 'Opportunity';
    const mapping = {
      full_time: 'Full-Time',
      part_time: 'Part-Time',
      internship: 'Internship',
      freelance: 'Freelance',
      startup_hiring: 'Startup Hiring',
      project_collaboration: 'Project Collaboration',
      tutoring: 'Tutoring',
      volunteer: 'Volunteer',
      event_based: 'Event Based'
    };
    return mapping[cat.toLowerCase()] || cat.replace('_', ' ');
  };

  // Format status in sentence case
  const formatStatus = (status) => {
    if (!status) return 'Applied';
    const mapping = {
      applied: 'Applied',
      under_review: 'Under review',
      accepted: 'Accepted',
      rejected: 'Rejected',
      withdrawn: 'Withdrawn'
    };
    return mapping[status.toLowerCase()] || status.charAt(0).toUpperCase() + status.slice(1).replace('_', ' ');
  };

  // Format pay text
  const formatPay = () => {
    if (pay_type === 'unpaid') return 'Unpaid';
    if (!pay_amount) return pay_type ? pay_type.toUpperCase() : 'Competitive';
    
    const amountStr = `₹${Number(pay_amount).toLocaleString('en-IN')}`;
    if (pay_type === 'hourly') return `${amountStr} / hr`;
    if (pay_type === 'monthly') return `${amountStr} / month`;
    if (pay_type === 'stipend') return `${amountStr} stipend`;
    return amountStr;
  };

  const providerName = poster?.full_name || poster?.first_name || poster?.email || 'NextGig Partner';
  const initial = providerName.charAt(0).toUpperCase();
  const locationDisplay = location_text || (city ? `${city} · ${work_mode || ''}` : work_mode || 'Remote');

  const handleNavigate = () => {
    if (onSelect) onSelect(opportunity);
    navigate(`/opportunities/${id}`);
  };

  return (
    <div className="opp-card cursor-pointer" onClick={handleNavigate}>
      <div className="opp-card-top">
        <div className="opp-card-badge-row">
          <span className={`opp-category-badge cat-${category}`}>{formatCategory(category)}</span>
          {work_mode && (
            <span className="opp-workmode-badge">
              <span className={`workmode-dot ${work_mode}`}></span>
              {work_mode.charAt(0).toUpperCase() + work_mode.slice(1)}
            </span>
          )}
        </div>
        
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSaveToggle(id);
          }}
          className={`opp-save-btn ${isSaved ? 'saved' : ''}`}
          title={isSaved ? 'Remove from saved' : 'Save opportunity'}
          aria-label={isSaved ? 'Remove from saved' : 'Save opportunity'}
          aria-pressed={!!isSaved}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill={isSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
      </div>

      <div className="opp-card-body">
        <h3 className="opp-card-title" title={title}>{title}</h3>
        
        <div className="opp-provider-row">
          <div className="provider-avatar">{initial}</div>
          <span className="provider-name" title={providerName}>{providerName}</span>
          {poster?.is_verified && (
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200 whitespace-nowrap flex-shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
              Verified
            </span>
          )}
        </div>

        <div className="opp-meta-row">
          <div className="meta-item" title={locationDisplay}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="flex-shrink-0">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span className="truncate">{locationDisplay}</span>
          </div>

          <div className="meta-item pay-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="flex-shrink-0">
              <rect x="2" y="6" width="20" height="12" rx="2"></rect>
              <circle cx="12" cy="12" r="2"></circle>
              <path d="M6 12h.01M18 12h.01"></path>
            </svg>
            <span className="pay-value">{formatPay()}</span>
          </div>
        </div>

        <div className="opp-deadline-row">
          {deadline ? (
            <span className="opp-deadline-chip">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="16" y1="2" x2="16" y2="6"></line>
                <line x1="8" y1="2" x2="8" y2="6"></line>
                <line x1="3" y1="10" x2="21" y2="10"></line>
              </svg>
              Due {new Date(deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
            </span>
          ) : null}
        </div>

        <div className="opp-skills-list">
          {required_skills && required_skills.length > 0 ? (
            <>
              {required_skills.slice(0, 2).map((skill, index) => (
                <span key={index} className="skill-tag" title={skill}>{skill}</span>
              ))}
              {required_skills.length > 2 && (
                <span className="skill-tag overflow">+{required_skills.length - 2}</span>
              )}
            </>
          ) : (
            <span className="skill-tag opacity-0 select-none pointer-events-none">&nbsp;</span>
          )}
        </div>
      </div>

      <div className="opp-card-footer">
        {application ? (
          <div className="opp-app-footer">
            <span className={`status-pill status-${(application.status || 'applied').toLowerCase()}`}>
              {formatStatus(application.status)}
            </span>
            <span className="app-date truncate text-xs text-slate-500">
              {application.applied_at ? `Applied ${new Date(application.applied_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}` : ''}
            </span>
            {onMessage && (
              <button
                type="button"
                disabled={chatLoading}
                onClick={(e) => {
                  e.stopPropagation();
                  onMessage();
                }}
                className="btn-chat-message text-xs font-semibold text-indigo-600 hover:text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 px-2.5 py-1 rounded-md transition-colors flex items-center gap-1.5 flex-shrink-0 cursor-pointer"
                title="Message poster"
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                {chatLoading ? 'Opening...' : 'Message'}
              </button>
            )}
          </div>
        ) : (
          <div className="opp-footer-info flex items-center gap-2">
            {vacancies && vacancies > 1 ? (
              <span className="vacancies-count">{vacancies} openings</span>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}
