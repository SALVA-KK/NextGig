import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * StudentCollabCard Component
 * Specifically tailored for student-to-student projects, hackathon teams, and peer collaborations.
 */
export default function StudentCollabCard({ opportunity, isSaved, onSaveToggle, onSelect }) {
  const navigate = useNavigate();
  const {
    id,
    title,
    description,
    required_skills = [],
    poster,
    vacancies,
    members_needed,
    collaboration_type,
    work_mode,
    city
  } = opportunity;

  const creatorName = poster?.full_name || poster?.first_name || poster?.email || 'Student Creator';
  const initial = creatorName.charAt(0).toUpperCase();
  const openSlots = members_needed || vacancies || 2;
  const collabBadge = collaboration_type || 'Student Team Project';

  const handleNavigate = () => {
    if (onSelect) onSelect(opportunity);
    navigate(`/opportunities/${id}`);
  };

  return (
    <div className="collab-card">
      <div className="collab-card-header">
        <div className="collab-badge-row">
          <span className="collab-type-tag">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            {collabBadge}
          </span>
          
          <span className="slots-badge">{openSlots} members needed</span>
        </div>

        <button
          onClick={(e) => {
            e.stopPropagation();
            onSaveToggle(id);
          }}
          className={`opp-save-btn ${isSaved ? 'saved' : ''}`}
          title={isSaved ? 'Remove bookmark' : 'Bookmark project'}
          aria-label="Bookmark project"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill={isSaved ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2">
            <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
          </svg>
        </button>
      </div>

      <div className="collab-card-body" onClick={handleNavigate}>
        <h3 className="collab-project-title">{title}</h3>
        <p className="collab-description">{description}</p>

        <div className="student-creator-strip">
          <div className="student-avatar">{initial}</div>
          <div className="student-info">
            <span className="student-name">{creatorName}</span>
            <span className="student-role">Student Project Lead</span>
          </div>
        </div>

        {required_skills && required_skills.length > 0 && (
          <div className="collab-skills-needed">
            <span className="skills-label">Looking for:</span>
            <div className="opp-skills-list">
              {required_skills.map((skill, index) => (
                <span key={index} className="skill-tag collab-skill">{skill}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="collab-card-footer">
        <span className="collab-location">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="2" y1="12" x2="22" y2="12"></line>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
          </svg>
          {city ? `${city} · ${work_mode || 'Hybrid'}` : work_mode ? `${work_mode}` : 'Remote Collaboration'}
        </span>

        <button 
          onClick={handleNavigate} 
          className="btn-collab-connect"
        >
          View & Connect
        </button>
      </div>
    </div>
  );
}
