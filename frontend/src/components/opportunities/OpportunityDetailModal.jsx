import React, { useState } from 'react';

export default function OpportunityDetailModal({
  opportunity,
  onClose,
  isSaved,
  onSaveToggle,
  onApplySubmit,
  hasApplied
}) {
  const [coverNote, setCoverNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [applySuccess, setApplySuccess] = useState(hasApplied);
  const [errorMessage, setErrorMessage] = useState(null);

  if (!opportunity) return null;

  const {
    id,
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
    deadline,
    poster,
    created_at,
    is_student_project,
    collaboration_type,
    members_needed
  } = opportunity;

  const providerName = poster?.full_name || poster?.first_name || poster?.email || 'Opportunity Creator';
  const initial = providerName.charAt(0).toUpperCase();

  const handleApply = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMessage(null);
    try {
      await onApplySubmit(id, coverNote);
      setApplySuccess(true);
    } catch (err) {
      setErrorMessage(err?.response?.data?.detail || 'Failed to submit application. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-header-meta">
            <span className="modal-category-badge">{category ? category.replace('_', ' ').toUpperCase() : 'OPPORTUNITY'}</span>
            {is_student_project && <span className="modal-student-tag">Student Project</span>}
          </div>
          
          <button onClick={onClose} className="modal-close-btn" aria-label="Close modal">×</button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          <h2 className="modal-title">{title}</h2>
          
          <div className="modal-provider-card">
            <div className="provider-avatar large">{initial}</div>
            <div className="provider-details">
              <span className="provider-title">{providerName}</span>
              <span className="provider-sub">Posted {new Date(created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
            </div>
          </div>

          {/* Quick Metrics Bar */}
          <div className="modal-metrics-grid">
            <div className="metric-box">
              <span className="metric-label">Location / Mode</span>
              <span className="metric-val">{location_text || city || work_mode || 'Remote'}</span>
            </div>

            <div className="metric-box">
              <span className="metric-label">Compensation</span>
              <span className="metric-val">
                {pay_type === 'unpaid' ? 'Unpaid' : pay_amount ? `₹${Number(pay_amount).toLocaleString('en-IN')}` : pay_type || 'Flexible'}
              </span>
            </div>

            <div className="metric-box">
              <span className="metric-label">Open Positions</span>
              <span className="metric-val">{members_needed || vacancies || 1} open</span>
            </div>

            {deadline && (
              <div className="metric-box">
                <span className="metric-label">Deadline</span>
                <span className="metric-val">{new Date(deadline).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
              </div>
            )}
          </div>

          {/* Detailed Description */}
          <div className="modal-section">
            <h4 className="modal-section-heading">About this {is_student_project ? 'Project' : 'Opportunity'}</h4>
            <p className="modal-description-text">{description}</p>
          </div>

          {/* Required Skills */}
          {required_skills && required_skills.length > 0 && (
            <div className="modal-section">
              <h4 className="modal-section-heading">Required Skills</h4>
              <div className="modal-skills-flex">
                {required_skills.map((skill, idx) => (
                  <span key={idx} className="skill-tag modal-skill">{skill}</span>
                ))}
              </div>
            </div>
          )}

          {/* Application Submission Form */}
          <div className="modal-section application-form-section">
            <h4 className="modal-section-heading">
              {is_student_project ? 'Connect & Join Project' : 'Submit Application'}
            </h4>

            {applySuccess ? (
              <div className="apply-success-box">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <div>
                  <strong>Application Submitted!</strong>
                  <p>The poster has been notified. You can track your application status under My Applications.</p>
                </div>
              </div>
            ) : (
              <form onSubmit={handleApply} className="apply-form">
                {errorMessage && <div className="apply-error-banner">{errorMessage}</div>}
                
                <div className="form-group">
                  <label htmlFor="cover-note-input">Note / Introduction (Optional)</label>
                  <textarea
                    id="cover-note-input"
                    rows="3"
                    className="form-textarea"
                    placeholder="Briefly introduce yourself, share relevant projects, or explain why you'd like to collaborate..."
                    value={coverNote}
                    onChange={(e) => setCoverNote(e.target.value)}
                  />
                </div>

                <div className="modal-actions-row">
                  <button
                    type="button"
                    onClick={() => onSaveToggle(id)}
                    className={`btn-modal-save ${isSaved ? 'saved' : ''}`}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill={isSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
                      <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                    </svg>
                    {isSaved ? 'Saved' : 'Save Item'}
                  </button>

                  <button type="submit" disabled={submitting} className="btn-modal-submit">
                    {submitting ? 'Submitting...' : is_student_project ? 'Send Teammate Request' : 'Submit Application'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
