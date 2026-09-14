import React from 'react';
import { STUDENT_FIELD_CONFIG, PROVIDER_FIELD_CONFIG } from '../../config/profileFieldConfigs';

export default function ProfileAboutTab({ profile, role = 'student', onEditClick }) {
  const configs = role === 'provider' ? PROVIDER_FIELD_CONFIG : STUDENT_FIELD_CONFIG;
  const aboutConfigs = configs.filter((c) => c.tab === 'about');

  // Filter non-empty fields
  const populatedFields = aboutConfigs.filter((c) => {
    const val = profile[c.key];
    if (val === null || val === undefined || val === '') return false;
    if (Array.isArray(val) && val.length === 0) return false;
    return true;
  });

  const formatValue = (config, val) => {
    if (!val) return null;
    if (config.type === 'select' && config.options) {
      const found = config.options.find((opt) => opt.value === val);
      return found ? found.label : val;
    }
    return String(val);
  };

  if (populatedFields.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-8 text-center border border-slate-200 shadow-sm space-y-4">
        <div className="w-12 h-12 mx-auto rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xl font-bold">
          ?
        </div>
        <h3 className="text-lg font-extrabold text-slate-900">No About Information Provided</h3>
        <p className="text-sm text-slate-500 max-w-md mx-auto">
          {role === 'provider'
            ? 'Add your organization type, contact person, location, and office address.'
            : 'Add your qualification, institution, availability, and city to boost candidate matching.'}
        </p>
        <button
          type="button"
          onClick={onEditClick}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition-all active:scale-95"
        >
          Add About Details in Settings
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Action Bar */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
          <span>About & Credentials</span>
          <span className="w-2 h-2 rounded-full bg-indigo-500" />
        </h2>
        <button
          type="button"
          onClick={onEditClick}
          className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 uppercase tracking-wider"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.03H3v-3.572L16.732 3.732z" />
          </svg>
          Edit Details
        </button>
      </div>

      {/* Grid of Cards - Responsive CSS Grid auto-fit */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {populatedFields.map((field) => {
          const val = profile[field.key];
          const displayVal = formatValue(field, val);

          return (
            <div
              key={field.key}
              className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm flex flex-col justify-between hover:border-indigo-300 transition-colors"
            >
              <div className="space-y-1">
                <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-400">
                  {field.label}
                </span>
                <p className="text-base font-bold text-slate-900">
                  {displayVal}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
