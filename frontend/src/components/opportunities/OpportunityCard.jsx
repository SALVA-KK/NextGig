import React from 'react';

/**
 * OpportunityCard Component
 * Displays a clean, scannable opportunity listing card for jobs, internships, freelance, etc.
 */
export default function OpportunityCard({ opportunity, isSaved, onSaveToggle, onSelect }) {
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

  return (
    <div className="opp-card">
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
          onClick={(e) => {
            e.stopPropagation();
            onSaveToggle(id);
          }}
          className={`opp-save-btn ${isSaved ? 'saved' : ''}`}
          title={isSaved ? 'Remove from saved' : 'Save opportunity'}
          aria-label="Save opportunity"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill={isSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
      </div>

      <div className="opp-card-body" onClick={() => onSelect(opportunity)}>
        <h3 className="opp-card-title">{title}</h3>
        
        <div className="opp-provider-row">
          <div className="provider-avatar">{initial}</div>
          <span className="provider-name">{providerName}</span>
        </div>

        <div className="opp-meta-row">
          <div className="meta-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
              <circle cx="12" cy="10" r="3"></circle>
            </svg>
            <span>{locationDisplay}</span>
          </div>

          <div className="meta-item pay-item">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="2" y="6" width="20" height="12" rx="2"></rect>
              <circle cx="12" cy="12" r="2"></circle>
              <path d="M6 12h.01M18 12h.01"></path>
            </svg>
            <span className="pay-value">{formatPay()}</span>
          </div>
        </div>

        {required_skills && required_skills.length > 0 && (
          <div className="opp-skills-list">
            {required_skills.slice(0, 4).map((skill, index) => (
              <span key={index} className="skill-tag">{skill}</span>
            ))}
            {required_skills.length > 4 && (
              <span className="skill-tag overflow">+{required_skills.length - 4}</span>
            )}
          </div>
        )}
      </div>

      <div className="opp-card-footer">
        <div className="opp-footer-info">
          {vacancies && vacancies > 1 && (
            <span className="vacancies-count">{vacancies} openings</span>
          )}
          {deadline && (
            <span className="deadline-text">Due {new Date(deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
          )}
        </div>

        <button 
          onClick={() => onSelect(opportunity)} 
          className="btn-opp-action"
        >
          View Details
        </button>
      </div>
    </div>
  );
}
