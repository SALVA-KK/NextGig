import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { authService } from '../../services/authService';

export default function Profile() {
  const navigate = useNavigate();

  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Form State
  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');

  // Alert State
  const [message, setMessage] = useState(null); // { type: 'success' | 'error', text: string }

  // Fetch Profile on Mount
  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    try {
      const data = await authService.getProfile();
      setProfile(data);
      setFullName(data.full_name || '');
      setPhoneNumber(data.phone_number || '');
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Failed to load profile data.',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleEditClick = () => {
    setMessage(null);
    setFullName(profile?.full_name || '');
    setPhoneNumber(profile?.phone_number || '');
    setIsEditing(true);
  };

  const handleCancel = () => {
    setMessage(null);
    setFullName(profile?.full_name || '');
    setPhoneNumber(profile?.phone_number || '');
    setIsEditing(false);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setMessage(null);
    setSaving(true);

    try {
      const updatedData = await authService.updateProfile({
        full_name: fullName.trim(),
        phone_number: phoneNumber.trim() || null,
      });

      setProfile(updatedData);
      setIsEditing(false);
      setMessage({
        type: 'success',
        text: 'Profile updated successfully!',
      });
    } catch (err) {
      setMessage({
        type: 'error',
        text: err.message || 'Failed to update profile.',
      });
    } finally {
      setSaving(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch (e) {
      return dateString;
    }
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-card">
        {/* Header & Back Navigation */}
        <div className="dashboard-header">
          <div className="auth-brand" style={{ marginBottom: 0 }}>
            <div className="brand-logo">N</div>
            <span className="brand-name">NextGig</span>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="btn-logout"
            style={{
              background: 'rgba(124, 58, 237, 0.15)',
              borderColor: 'rgba(124, 58, 237, 0.3)',
              color: '#a78bfa',
            }}
          >
            ← Back to Dashboard
          </button>
        </div>

        {/* Page Title */}
        <div className="dashboard-welcome" style={{ paddingBottom: 0 }}>
          <h1 className="dashboard-title">User Profile</h1>
          <p className="dashboard-subtitle">
            Manage your personal account details and contact information.
          </p>
        </div>

        {/* Alert Feedback Banner */}
        {message && (
          <div className={`alert-banner alert-${message.type}`}>
            {message.text}
          </div>
        )}

        {loading ? (
          <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)' }}>
            Loading profile information...
          </div>
        ) : profile ? (
          <div className="user-profile-card">
            <div className="user-profile-header">
              <span className="badge-authenticated" style={{ textTransform: 'uppercase' }}>
                {profile.role || 'USER'}
              </span>
            </div>

            {!isEditing ? (
              /* View Mode */
              <>
                <div className="user-profile-details">
                  <div className="user-detail-row">
                    <span className="detail-label">Full Name:</span>
                    <span className="detail-value">{profile.full_name || 'Not provided'}</span>
                  </div>

                  <div className="user-detail-row">
                    <span className="detail-label">Email Address:</span>
                    <span className="detail-value">{profile.email}</span>
                  </div>

                  <div className="user-detail-row">
                    <span className="detail-label">Phone Number:</span>
                    <span className="detail-value">{profile.phone_number || 'Not provided'}</span>
                  </div>

                  <div className="user-detail-row">
                    <span className="detail-label">Role:</span>
                    <span className="detail-value" style={{ textTransform: 'capitalize' }}>
                      {profile.role}
                    </span>
                  </div>

                  <div className="user-detail-row">
                    <span className="detail-label">Member Since:</span>
                    <span className="detail-value">{formatDate(profile.date_joined)}</span>
                  </div>
                </div>

                <div style={{ marginTop: '20px' }}>
                  <button
                    type="button"
                    className="btn-primary"
                    onClick={handleEditClick}
                  >
                    Edit Profile
                  </button>
                </div>
              </>
            ) : (
              /* Edit Mode */
              <form onSubmit={handleSave} className="auth-form" style={{ marginTop: '12px' }}>
                <div className="form-group">
                  <label htmlFor="full_name">Full Name</label>
                  <input
                    id="full_name"
                    type="text"
                    className="form-input"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                    placeholder="Enter your full name"
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="phone_number">Phone Number</label>
                  <input
                    id="phone_number"
                    type="text"
                    className="form-input"
                    value={phoneNumber}
                    onChange={(e) => setPhoneNumber(e.target.value)}
                    placeholder="Enter your phone number (e.g. 6238414785)"
                  />
                </div>

                <div className="form-group">
                  <label>Email Address (Read-only)</label>
                  <input
                    type="email"
                    className="form-input disabled"
                    value={profile.email}
                    disabled
                  />
                </div>

                <div className="form-group">
                  <label>Role (Read-only)</label>
                  <input
                    type="text"
                    className="form-input disabled"
                    value={profile.role}
                    disabled
                  />
                </div>

                <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                  <button
                    type="submit"
                    className="btn-primary"
                    disabled={saving}
                  >
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                  <button
                    type="button"
                    className="btn-logout"
                    onClick={handleCancel}
                    disabled={saving}
                    style={{ flex: 1 }}
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            Failed to load profile details.
          </div>
        )}
      </div>
    </div>
  );
}
