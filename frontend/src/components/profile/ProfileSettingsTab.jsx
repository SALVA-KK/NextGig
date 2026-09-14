import React, { useState, useEffect } from 'react';
import SocialLinksInput from '../common/SocialLinksInput';
import ChangePasswordCard from './ChangePasswordCard';
import InviteCard from '../dashboard/InviteCard';
import { STUDENT_FIELD_CONFIG, PROVIDER_FIELD_CONFIG } from '../../config/profileFieldConfigs';

export default function ProfileSettingsTab({
  profile,
  role = 'student',
  onSaveProfile,
  saving = false,
  message = null,
  fieldErrors = {},
}) {
  const configs = role === 'provider' ? PROVIDER_FIELD_CONFIG : STUDENT_FIELD_CONFIG;

  const [formData, setFormData] = useState({});
  const [socialLinks, setSocialLinks] = useState({});

  useEffect(() => {
    if (!profile) return;
    const initialForm = {};
    configs.forEach((field) => {
      const key = field.key;
      if (field.type === 'tags') {
        const val = profile[key];
        initialForm[key] = Array.isArray(val) ? val.join(', ') : val || '';
      } else if (field.type === 'checkbox') {
        initialForm[key] = !!profile[key];
      } else if (field.type !== 'social') {
        initialForm[key] = profile[key] !== null && profile[key] !== undefined ? profile[key] : '';
      }
    });
    setFormData(initialForm);
    setSocialLinks(profile.social_links || {});
  }, [profile, role]);

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSaveProfile(formData, socialLinks);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
          <span>Settings & Live Profile Form</span>
          <span className="w-2 h-2 rounded-full bg-indigo-500" />
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Directly edit and save your profile details, privacy preferences, social links, and security options.
        </p>
      </div>

      {/* Alert Feedback Banner */}
      {message && (
        <div
          className={
            message.type === 'success'
              ? 'p-4 rounded-xl text-sm font-semibold border bg-emerald-50 text-emerald-800 border-emerald-200'
              : 'p-4 rounded-xl text-sm font-semibold border bg-red-50 text-red-800 border-red-200'
          }
        >
          {message.text}
        </div>
      )}

      {/* Main Settings Form */}
      <form onSubmit={handleSubmit} className="space-y-8 bg-white p-6 sm:p-8 rounded-2xl border border-slate-200 shadow-sm">
        
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-6">
          {configs.map((field) => {
            const key = field.key;
            const errorText = fieldErrors[key];

            // Render Social links custom component
            if (field.type === 'social') {
              return (
                <div key={key} className="sm:col-span-2 space-y-4 pt-4 border-t border-slate-200">
                  <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 mb-2">
                    {field.label}
                  </label>
                  <SocialLinksInput value={socialLinks} onChange={setSocialLinks} />
                  {errorText && <p className="text-xs text-red-500 font-semibold mt-1.5">{errorText}</p>}
                </div>
              );
            }

            // Render Checkboxes (Contact Privacy Toggles)
            if (field.type === 'checkbox') {
              return (
                <div key={key} className="sm:col-span-2 p-4.5 rounded-xl bg-slate-50 border border-slate-200">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      name={key}
                      checked={!!formData[key]}
                      onChange={handleChange}
                      className="w-4.5 h-4.5 text-indigo-600 rounded border-slate-300 focus:ring-indigo-500 cursor-pointer"
                    />
                    <span className="text-sm font-bold text-slate-800">
                      {field.label}
                    </span>
                  </label>
                  {errorText && <p className="text-xs text-red-500 font-semibold mt-1.5">{errorText}</p>}
                </div>
              );
            }

            // Render Textarea
            if (field.type === 'textarea') {
              return (
                <div key={key} className="sm:col-span-2 space-y-2">
                  <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 mb-2">
                    {field.label} {field.required && <span className="text-red-500">*</span>}
                  </label>
                  <textarea
                    name={key}
                    rows={4}
                    value={formData[key] || ''}
                    onChange={handleChange}
                    placeholder={field.placeholder}
                    className="w-full px-4 py-3 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all shadow-sm"
                  />
                  {errorText && <p className="text-xs text-red-500 font-semibold mt-1">{errorText}</p>}
                </div>
              );
            }

            // Render Select Dropdown
            if (field.type === 'select') {
              return (
                <div key={key} className="space-y-2">
                  <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 mb-2">
                    {field.label} {field.required && <span className="text-red-500">*</span>}
                  </label>
                  <select
                    name={key}
                    value={formData[key] || ''}
                    onChange={handleChange}
                    className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all shadow-sm"
                  >
                    {field.options?.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                  {errorText && <p className="text-xs text-red-500 font-semibold mt-1">{errorText}</p>}
                </div>
              );
            }

            // Default Input Types: text, url, phone, tags
            return (
              <div key={key} className="space-y-2">
                <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 mb-2">
                  {field.label} {field.required && <span className="text-red-500">*</span>}
                </label>
                <input
                  type={field.type === 'url' ? 'url' : 'text'}
                  name={key}
                  value={formData[key] || ''}
                  onChange={handleChange}
                  placeholder={field.placeholder}
                  className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all shadow-sm"
                />
                {errorText && <p className="text-xs text-red-500 font-semibold mt-1">{errorText}</p>}
              </div>
            );
          })}
        </div>

        {/* Submit Button */}
        <div className="pt-6 border-t border-slate-200 flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-3 rounded-xl font-extrabold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition-all active:scale-95 disabled:opacity-50"
          >
            {saving ? 'Saving Changes...' : 'Save Profile Settings'}
          </button>
        </div>
      </form>

      {/* ACCOUNT SECURITY & CHANGE PASSWORD CARD */}
      <div className="space-y-4">
        <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
          Account Security & Authentication
        </h3>
        <ChangePasswordCard />
      </div>

      {/* REFERRALS & INVITE CARD */}
      <div className="space-y-4">
        <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
          Referral & Peer Invitations
        </h3>
        <InviteCard />
      </div>
    </div>
  );
}
