import { useState, useEffect } from 'react';
import DashboardLayout from '../../components/dashboard/DashboardLayout';
import ProfileHeader from '../../components/profile/ProfileHeader';
import ProfileSection from '../../components/profile/ProfileSection';
import ProfileField from '../../components/profile/ProfileField';
import ChangePasswordCard from '../../components/profile/ChangePasswordCard';
import ResumeCard from '../../components/profile/ResumeCard';
import InviteCard from '../../components/dashboard/InviteCard';
import { authService } from '../../services/authService';

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Profile Edit Form State
  const [fullName, setFullName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');

  // Profile Alert Feedback State
  const [message, setMessage] = useState(null);

  // Fetch Profile on Mount
  useEffect(() => {
    let isMounted = true;
    authService.getProfile()
      .then(data => {
        if (!isMounted) return;
        setProfile(data);
        setFullName(data.full_name || '');
        setPhoneNumber(data.phone_number || '');
      })
      .catch(err => {
        if (!isMounted) return;
        console.error('[Profile] fetchProfile error:', err);
        setMessage({
          type: 'error',
          text: err.message || 'Failed to load profile data.',
        });
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => { isMounted = false; };
  }, []);

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
      console.error('[Profile] handleSave error:', err);
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
    <DashboardLayout title="Profile">
      <div className="profile-container">
        {loading ? (
          <div className="profile-loading-state">
            <div className="skeleton-line title" style={{ width: '200px', height: '28px', marginBottom: '16px' }}></div>
            <div className="skeleton-card" style={{ height: '140px' }}></div>
          </div>
        ) : profile ? (
          <>
            {/* Header Card */}
            <ProfileHeader
              profile={profile}
              isEditing={isEditing}
              onEditClick={handleEditClick}
              onCancelEdit={handleCancel}
              saving={saving}
            />

            {/* Alert Feedback Banner */}
            {message && (
              <div className={`alert-banner alert-${message.type}`}>
                {message.text}
              </div>
            )}

            {/* Profile Content Container */}
            <div className="profile-sections-wrapper">
              <form onSubmit={handleSave}>
                {/* SECTION 1: Personal Information */}
                <ProfileSection
                  title="Personal Information"
                  description="Your primary identity details on the NextGig workspace."
                >
                  <div className="profile-fields-grid">
                    <ProfileField
                      id="full_name"
                      label="Full Name"
                      value={isEditing ? fullName : profile.full_name}
                      isEditing={isEditing}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                      placeholder="Enter full name"
                    />

                    <ProfileField
                      id="role"
                      label="Account Role"
                      value={profile.role ? profile.role.toUpperCase() : 'STUDENT'}
                      readOnly
                      isEditing={isEditing}
                    />
                  </div>
                </ProfileSection>

                {/* SECTION 2: Contact Information */}
                <ProfileSection
                  title="Contact Information"
                  description="Contact channels used for platform notifications and identity verification."
                >
                  <div className="profile-fields-grid">
                    <ProfileField
                      id="email"
                      label="Email Address"
                      value={profile.email}
                      readOnly
                      isEditing={isEditing}
                    />

                    <ProfileField
                      id="phone_number"
                      label="Phone Number"
                      value={isEditing ? phoneNumber : profile.phone_number}
                      isEditing={isEditing}
                      onChange={(e) => setPhoneNumber(e.target.value)}
                      placeholder="+91 98765 43210"
                    />
                  </div>
                </ProfileSection>

                {/* Edit Mode Save & Cancel Bar */}
                {isEditing && (
                  <div className="profile-edit-actions-bar">
                    <button
                      type="submit"
                      className="btn-primary"
                      disabled={saving}
                      style={{ width: 'auto', padding: '10px 24px' }}
                    >
                      {saving ? 'Saving Changes...' : 'Save Changes'}
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
                )}
              </form>

              {/* SECTION: Resume & Opportunity Profile (Student Role) */}
              {(profile.role === 'student' || !profile.role) && <ResumeCard />}

              {/* SECTION 3: Account Security */}
              <ProfileSection
                title="Account & Security"
                description="Security settings, account age, and password management."
              >
                <div className="profile-fields-grid" style={{ marginBottom: '20px' }}>
                  <ProfileField
                    id="member_since"
                    label="Member Since"
                    value={formatDate(profile.date_joined)}
                    readOnly
                  />
                </div>

                <ChangePasswordCard />
              </ProfileSection>

              {/* SECTION 4: Referrals & Invitations */}
              <ProfileSection
                title="Invite People & Referrals"
                description="Generate a unique invitation link to invite friends or colleagues to join NextGig."
              >
                <InviteCard />
              </ProfileSection>
            </div>
          </>
        ) : (
          <div className="profile-error-state">
            <p>Failed to load profile details.</p>
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
