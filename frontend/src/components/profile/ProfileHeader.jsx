import React, { useRef, useState } from 'react';

export default function ProfileHeader({
  profile,
  role = 'student',
  onAvatarUpload,
  uploadingAvatar = false,
  onEditClick,
  activeTab,
}) {
  const fileInputRef = useRef(null);
  const [avatarError, setAvatarError] = useState(null);

  const displayName = role === 'provider'
    ? (profile.organization_name || profile.full_name || 'Organization Name')
    : (profile.full_name || profile.email || 'Student Profile');

  const headline = role === 'provider'
    ? (profile.organization_type ? profile.organization_type.replace('_', ' ').toUpperCase() : 'ORGANIZATION')
    : (profile.profession || 'Student / Candidate');

  const avatarUrl = profile.profile_picture || null;
  const initialLetter = displayName.charAt(0).toUpperCase();

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAvatarError(null);
    if (file.size > 2 * 1024 * 1024) {
      setAvatarError('Image size must be under 2MB.');
      return;
    }
    const allowed = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(file.type)) {
      setAvatarError('Image format must be JPG, PNG, or WEBP.');
      return;
    }

    try {
      await onAvatarUpload(file);
    } catch (err) {
      setAvatarError(err.message || 'Avatar upload failed.');
    }
  };

  return (
    <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-200 mb-6">
      <div className="flex flex-col sm:flex-row items-center sm:items-start justify-between gap-6">
        <div className="flex flex-col sm:flex-row items-center gap-5 text-center sm:text-left">
          
          {/* Avatar Container with Upload & Corner Camera Badge */}
          <div className="relative group w-24 h-24 sm:w-28 sm:h-28 flex-shrink-0">
            <div className="w-full h-full rounded-full overflow-hidden border-2 border-slate-200 bg-indigo-50 flex items-center justify-center shadow-sm">
              {avatarUrl ? (
                <img
                  src={avatarUrl}
                  alt={displayName}
                  className="w-full h-full object-cover"
                />
              ) : (
                <span className="text-3xl sm:text-4xl font-extrabold text-indigo-600">
                  {initialLetter}
                </span>
              )}

              {/* Uploading Overlay Spinner */}
              {uploadingAvatar && (
                <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm rounded-full flex flex-col items-center justify-center gap-1 text-white">
                  <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span className="text-[10px] font-bold uppercase tracking-wider">Uploading</span>
                </div>
              )}
            </div>

            {/* Corner Overlay Camera Upload Badge */}
            <button
              type="button"
              disabled={uploadingAvatar}
              onClick={() => fileInputRef.current?.click()}
              className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-md border-2 border-white transition-all hover:scale-110 active:scale-95 flex items-center justify-center"
              title="Change Profile Picture"
            >
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {/* User / Org Metadata Header */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-2">
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900">
                {displayName}
              </h1>

              {/* Provider Verification Badge */}
              {role === 'provider' && (
                <span
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                    profile.is_verified
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                      : 'bg-amber-50 text-amber-800 border-amber-200'
                  }`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${profile.is_verified ? 'bg-emerald-500 animate-pulse' : 'bg-amber-500'}`} />
                  {profile.is_verified ? 'Verified Provider' : 'Pending Verification'}
                </span>
              )}

              {/* Student Role Badge */}
              {role === 'student' && (
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
                  Student Member
                </span>
              )}
            </div>

            <p className="text-sm font-medium text-slate-600">
              {headline}
            </p>

            {profile.city && (
              <p className="text-xs text-slate-500 flex items-center justify-center sm:justify-start gap-1">
                <svg className="w-3.5 h-3.5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                {profile.city}
              </p>
            )}

            {avatarError && (
              <p className="text-xs text-red-600 font-semibold">{avatarError}</p>
            )}
          </div>
        </div>

        {/* Quick Edit Action Button */}
        {activeTab !== 'settings' && (
          <button
            type="button"
            onClick={onEditClick}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all active:scale-95 border border-indigo-600"
          >
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Edit Profile
          </button>
        )}
      </div>
    </div>
  );
}
