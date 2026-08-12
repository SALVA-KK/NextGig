import React from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Modern ProfileHeader component.
 * Displays avatar initials, full name, role badge, contact preview, and edit toggle button.
 */
export default function ProfileHeader({
  profile,
  isEditing,
  onEditClick,
  onCancelEdit,
  saving,
}) {
  const navigate = useNavigate();

  if (!profile) return null;

  const displayName = profile.full_name || profile.email || 'User';
  const initial = displayName.charAt(0).toUpperCase();

  return (
    <div className="profile-header-card">
      <div className="profile-header-top">
        <div className="profile-header-main">
          {/* Avatar Initials Badge */}
          <div className="profile-avatar-large">
            <span>{initial}</span>
          </div>

          {/* User Bio / Header Info */}
          <div className="profile-header-info">
            <div className="profile-name-row">
              <h1 className="profile-user-name">{displayName}</h1>
              <span className="profile-role-badge">{profile.role || 'STUDENT'}</span>
            </div>

            <div className="profile-contact-meta">
              <span className="profile-meta-item">
                <svg className="meta-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 002-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                {profile.email}
              </span>

              {profile.phone_number && (
                <span className="profile-meta-item">
                  <svg className="meta-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                  </svg>
                  {profile.phone_number}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="profile-header-actions">
          {!isEditing ? (
            <button
              type="button"
              className="btn-profile-edit"
              onClick={onEditClick}
            >
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24" width="16" height="16">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 210.3H3v-3.572L16.732 3.732z" />
              </svg>
              Edit Profile
            </button>
          ) : (
            <button
              type="button"
              className="btn-profile-cancel"
              onClick={onCancelEdit}
              disabled={saving}
            >
              Cancel Edit
            </button>
          )}

          <button
            type="button"
            className="btn-profile-back"
            onClick={() => navigate('/dashboard')}
          >
            ← Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
