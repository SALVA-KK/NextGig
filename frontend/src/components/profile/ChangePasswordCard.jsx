import React, { useState } from 'react';
import { authService } from '../../services/authService';

/**
 * Reusable ChangePasswordCard component for Account & Security section.
 */
export default function ChangePasswordCard() {
  const [showForm, setShowForm] = useState(false);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      setMessage({
        type: 'error',
        text: 'New password and confirmation do not match.',
      });
      return;
    }

    setMessage(null);
    setSaving(true);

    try {
      const data = await authService.changePassword(oldPassword, newPassword, confirmPassword);
      setMessage({
        type: 'success',
        text: data.message || 'Password changed successfully!',
      });
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setShowForm(false);
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Failed to change password.',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setMessage(null);
    setOldPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setShowForm(false);
  };

  return (
    <div className="security-card">
      {message && (
        <div className={`alert-banner alert-${message.type}`} style={{ marginBottom: '16px' }}>
          {message.text}
        </div>
      )}

      {!showForm ? (
        <div className="security-card-overview">
          <div>
            <h4 className="security-card-title">Password & Authentication</h4>
            <p className="security-card-desc">
              Ensure your account is using a strong password for security.
            </p>
          </div>
          <button
            type="button"
            className="btn-secondary-action"
            onClick={() => {
              setMessage(null);
              setShowForm(true);
            }}
          >
            Change Password
          </button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="auth-form" style={{ marginTop: '8px' }}>
          <div className="form-group">
            <label htmlFor="old_password">Current Password</label>
            <input
              id="old_password"
              type="password"
              className="form-input"
              placeholder="Enter current password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
              disabled={saving}
            />
          </div>

          <div className="form-group">
            <label htmlFor="new_password">New Password</label>
            <input
              id="new_password"
              type="password"
              className="form-input"
              placeholder="Enter new password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
              disabled={saving}
            />
          </div>

          <div className="form-group">
            <label htmlFor="confirm_password">Confirm New Password</label>
            <input
              id="confirm_password"
              type="password"
              className="form-input"
              placeholder="Confirm new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              disabled={saving}
            />
          </div>

          <div className="profile-edit-actions" style={{ marginTop: '16px' }}>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Updating Password...' : 'Update Password'}
            </button>
            <button
              type="button"
              className="btn-profile-cancel"
              onClick={handleCancel}
              disabled={saving}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
