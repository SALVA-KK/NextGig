import React, { useState, useEffect } from 'react';
import ProfileHeader from './ProfileHeader';
import ProfileTabs from './ProfileTabs';
import ProfileOverviewTab from './ProfileOverviewTab';
import ProfileAboutTab from './ProfileAboutTab';
import ProfilePortfolioTab from './ProfilePortfolioTab';
import ProfileSettingsTab from './ProfileSettingsTab';
import { authService } from '../../services/authService';
import studentProfileService from '../../services/studentProfileService';
import providerProfileService from '../../services/providerProfileService';
import { STUDENT_FIELD_CONFIG, PROVIDER_FIELD_CONFIG } from '../../config/profileFieldConfigs';

export default function ProfileShell({ role = 'student' }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});

  const isStudent = role === 'student';
  const service = isStudent ? studentProfileService : providerProfileService;
  const configs = isStudent ? STUDENT_FIELD_CONFIG : PROVIDER_FIELD_CONFIG;

  const loadProfile = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const [baseUser, roleProf] = await Promise.all([
        authService.getProfile(),
        service.getStudentProfile ? service.getStudentProfile() : service.getProviderProfile(),
      ]);

      setProfile({
        ...baseUser,
        ...roleProf,
        social_links: roleProf?.social_links || {},
      });
    } catch (err) {
      console.error(`[ProfileShell] Error loading ${role} profile:`, err);
      setMessage({
        type: 'error',
        text: 'Unable to load profile details. Please try refreshing the page.',
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, [role]);

  const handleAvatarUpload = async (file) => {
    setUploadingAvatar(true);
    setMessage(null);
    try {
      const updated = await service.uploadProfilePicture(file);
      setProfile((prev) => ({
        ...prev,
        profile_picture: updated.profile_picture || prev.profile_picture,
      }));
      setMessage({ type: 'success', text: 'Profile picture updated successfully!' });
    } catch (err) {
      console.error(`[ProfileShell] Avatar upload error:`, err);
      setMessage({
        type: 'error',
        text: 'Failed to update profile picture. Please ensure the file is an image under 2MB.',
      });
      throw err;
    } finally {
      setUploadingAvatar(false);
    }
  };

  const handleSaveProfile = async (formData, socialLinks) => {
    setSaving(true);
    setMessage(null);
    setFieldErrors({});

    try {
      // 1. Base User updates (full_name, phone_number)
      const basePayload = {};
      if ('full_name' in formData) basePayload.full_name = String(formData.full_name).trim();
      if ('phone_number' in formData) basePayload.phone_number = String(formData.phone_number).trim() || null;

      if (Object.keys(basePayload).length > 0) {
        await authService.updateProfile(basePayload);
      }

      // 2. Role Profile JSON PATCH Payload
      const rolePayload = {};
      configs.forEach((field) => {
        if (field.isBaseUserField || field.type === 'social') return;
        const val = formData[field.key];
        if (field.type === 'tags') {
          rolePayload[field.key] = typeof val === 'string'
            ? val.split(',').map((s) => s.trim()).filter(Boolean)
            : val || [];
        } else if (field.type === 'checkbox') {
          rolePayload[field.key] = !!val;
        } else if (val !== undefined && val !== null) {
          rolePayload[field.key] = String(val).trim();
        }
      });

      // Social Links object payload
      const cleanSocial = {};
      for (const [k, v] of Object.entries(socialLinks || {})) {
        if (v && typeof v === 'string' && v.trim()) {
          cleanSocial[k] = v.trim();
        }
      }
      rolePayload.social_links = cleanSocial;

      // Execute clean JSON PATCH request
      const updatedRoleProf = isStudent
        ? await studentProfileService.updateStudentProfile(rolePayload)
        : await providerProfileService.updateProviderProfile(rolePayload);

      const updatedBaseUser = await authService.getProfile();

      setProfile({
        ...updatedBaseUser,
        ...updatedRoleProf,
        social_links: updatedRoleProf.social_links || {},
      });

      setMessage({ type: 'success', text: 'Profile updated successfully!' });
    } catch (err) {
      console.error(`[ProfileShell] handleSaveProfile error:`, err);

      const serverFieldErrors = err?.response?.data || {};
      if (typeof serverFieldErrors === 'object' && !Array.isArray(serverFieldErrors)) {
        const errorsObj = {};
        for (const [k, v] of Object.entries(serverFieldErrors)) {
          errorsObj[k] = Array.isArray(v) ? v.join(' ') : String(v);
        }
        setFieldErrors(errorsObj);
      }

      setMessage({
        type: 'error',
        text: 'Failed to update profile settings. Please check the highlighted fields.',
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="discovery-container space-y-6">
        <div className="h-40 bg-slate-200 rounded-2xl animate-pulse" />
        <div className="w-full h-12 bg-slate-200 rounded-xl animate-pulse" />
        <div className="w-full h-64 bg-slate-200 rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="discovery-container">
        <div className="p-6 bg-red-50 rounded-2xl text-red-800 border border-red-200 text-center space-y-3">
          <p className="font-bold text-base">Failed to load profile details.</p>
          <button
            onClick={loadProfile}
            className="px-4 py-2 rounded-xl bg-red-600 text-white font-bold text-xs uppercase tracking-wider shadow-sm hover:bg-red-700 transition-colors"
          >
            Retry Loading Profile
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="discovery-container space-y-6">
      <ProfileHeader
        profile={profile}
        role={role}
        onAvatarUpload={handleAvatarUpload}
        uploadingAvatar={uploadingAvatar}
        onEditClick={() => setActiveTab('settings')}
        activeTab={activeTab}
      />

      <ProfileTabs activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'overview' && (
        <ProfileOverviewTab
          profile={profile}
          role={role}
          onEditClick={() => setActiveTab('settings')}
        />
      )}
      {activeTab === 'about' && (
        <ProfileAboutTab
          profile={profile}
          role={role}
          onEditClick={() => setActiveTab('settings')}
        />
      )}
      {activeTab === 'portfolio' && (
        <ProfilePortfolioTab
          profile={profile}
          role={role}
          onEditClick={() => setActiveTab('settings')}
        />
      )}
      {activeTab === 'settings' && (
        <ProfileSettingsTab
          profile={profile}
          role={role}
          onSaveProfile={handleSaveProfile}
          saving={saving}
          message={message}
          fieldErrors={fieldErrors}
        />
      )}
    </div>
  );
}
