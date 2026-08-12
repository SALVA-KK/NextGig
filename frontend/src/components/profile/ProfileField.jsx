import React from 'react';

/**
 * Reusable ProfileField component.
 * Renders cleanly in both view mode and edit mode.
 */
export default function ProfileField({
  id,
  label,
  value,
  type = 'text',
  isEditing = false,
  onChange,
  readOnly = false,
  placeholder = '',
  required = false,
  helpText = null,
}) {
  return (
    <div className="profile-field-item">
      <label htmlFor={id} className="profile-field-label">
        {label}
        {readOnly && isEditing && <span className="read-only-tag"> (Read-only)</span>}
      </label>

      {isEditing && !readOnly ? (
        <div className="profile-field-input-wrapper">
          <input
            id={id}
            name={id}
            type={type}
            value={value}
            onChange={onChange}
            placeholder={placeholder}
            required={required}
            className="form-input"
          />
          {helpText && <span className="form-help-text">{helpText}</span>}
        </div>
      ) : (
        <div className={`profile-field-value ${readOnly ? 'muted-value' : ''}`}>
          {value || <span className="empty-value">Not provided</span>}
        </div>
      )}
    </div>
  );
}
