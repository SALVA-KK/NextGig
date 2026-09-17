import React, { useState, useEffect } from 'react';
import ChangePasswordCard from './ChangePasswordCard';
import { authService } from '../../services/authService';

export default function AdminProfileView() {
  const [profile, setProfile] = useState(null);
  const [mfaStatus, setMfaStatus] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadAdminProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const [userData, mfaData] = await Promise.all([
        authService.getProfile(),
        authService.getAdminMFAStatus(),
      ]);
      setProfile(userData);
      setMfaStatus(Boolean(mfaData?.is_enabled));
    } catch (err) {
      console.error('[AdminProfileView] Failed to load admin profile:', err);
      setError('Unable to load admin profile details. Please try refreshing.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminProfile();
  }, []);

  if (loading) {
    return (
      <div className="discovery-container space-y-6">
        <div className="h-40 bg-slate-200 rounded-2xl animate-pulse" />
        <div className="w-full h-64 bg-slate-200 rounded-2xl animate-pulse" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="discovery-container">
        <div className="p-6 bg-red-50 rounded-2xl text-red-800 border border-red-200 text-center space-y-3">
          <p className="font-bold text-base">{error || 'Failed to load profile details.'}</p>
          <button
            onClick={loadAdminProfile}
            className="px-4 py-2 rounded-xl bg-red-600 text-white font-bold text-xs uppercase tracking-wider shadow-sm hover:bg-red-700 transition-colors"
          >
            Retry Loading Profile
          </button>
        </div>
      </div>
    );
  }

  const displayName = profile.full_name || profile.email || 'Administrator';
  const initialLetter = displayName.charAt(0).toUpperCase();

  return (
    <div className="discovery-container space-y-6">
      
      {/* HEADER CARD */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200">
        <div className="flex flex-col sm:flex-row items-center sm:items-start justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-center gap-5 text-center sm:text-left">
            
            {/* Admin Avatar Circle */}
            <div className="w-20 h-20 sm:w-24 sm:h-24 rounded-full overflow-hidden border-2 border-slate-200 bg-indigo-50 flex items-center justify-center shadow-sm flex-shrink-0">
              <span className="text-3xl sm:text-4xl font-extrabold text-indigo-600">
                {initialLetter}
              </span>
            </div>

            {/* Admin Details Header */}
            <div className="space-y-2">
              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
                <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                  {displayName}
                </h1>
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Administrator
                </span>
              </div>

              <p className="text-sm font-medium text-slate-600">
                {profile.email}
              </p>

              <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2 pt-1">
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Account Active
                </span>

                <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                  mfaStatus
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                    : 'bg-amber-50 text-amber-800 border-amber-200'
                }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${mfaStatus ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                  MFA {mfaStatus ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ACCOUNT DETAILS CARD */}
      <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 space-y-6">
        <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Account Overview
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Full Name</span>
            <span className="text-base font-semibold text-slate-900">{profile.full_name || 'Not specified'}</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Email Address</span>
            <span className="text-base font-semibold text-slate-900">{profile.email}</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Platform Role</span>
            <span className="text-base font-semibold text-slate-900 capitalize">{profile.role || 'Admin'}</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block mb-1">Date Joined</span>
            <span className="text-base font-semibold text-slate-900">
              {profile.date_joined ? new Date(profile.date_joined).toLocaleDateString() : 'N/A'}
            </span>
          </div>
        </div>
      </div>

      {/* CHANGE PASSWORD CARD */}
      <ChangePasswordCard />
    </div>
  );
}
