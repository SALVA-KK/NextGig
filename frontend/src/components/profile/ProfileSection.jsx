import React from 'react';

/**
 * Reusable ProfileSection container component.
 * Modular section wrapper for scalable profile information.
 */
export default function ProfileSection({ title, description, children, action = null }) {
  return (
    <section className="profile-section-card">
      <div className="profile-section-header">
        <div>
          <h3 className="profile-section-title">{title}</h3>
          {description && <p className="profile-section-desc">{description}</p>}
        </div>
        {action && <div className="profile-section-action">{action}</div>}
      </div>

      <div className="profile-section-content">{children}</div>
    </section>
  );
}
