import React from 'react';
import SocialLinksDisplay from '../common/SocialLinksDisplay';
import InviteCard from '../dashboard/InviteCard';
import ResumeCard from './ResumeCard';
import { STUDENT_FIELD_CONFIG, PROVIDER_FIELD_CONFIG } from '../../config/profileFieldConfigs';

export default function ProfileOverviewTab({ profile, role = 'student', onEditClick }) {
  const configs = role === 'provider' ? PROVIDER_FIELD_CONFIG : STUDENT_FIELD_CONFIG;
  const overviewConfigs = configs.filter((c) => c.tab === 'overview');

  // Filter non-empty overview configs
  const populatedConfigs = overviewConfigs.filter((field) => {
    const val = profile[field.key];
    if (val === null || val === undefined || val === '') return false;
    if (Array.isArray(val) && val.length === 0) return false;
    if (typeof val === 'object' && Object.keys(val).length === 0) return false;
    return true;
  });

  const formatValue = (field, val) => {
    if (!val) return null;
    if (field.type === 'select' && field.options) {
      const found = field.options.find((opt) => opt.value === val);
      return found ? found.label : val;
    }
    return String(val);
  };

  if (populatedConfigs.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-8 text-center border border-slate-200 shadow-sm space-y-4">
        <div className="w-12 h-12 mx-auto rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center text-xl font-bold">
          !
        </div>
        <h3 className="text-lg font-extrabold text-slate-900">Your Overview is Empty</h3>
        <p className="text-sm text-slate-500 max-w-md mx-auto">
          Add a bio, key skills, spoken languages, location, credentials, or website in Settings to display your full overview.
        </p>
        <button
          type="button"
          onClick={onEditClick}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-md transition-all active:scale-95"
        >
          Edit Profile in Settings
        </button>
      </div>
    );
  }

  // Group fields logically for clean presentation
  const textareas = populatedConfigs.filter((c) => c.type === 'textarea');
  const tagsFields = populatedConfigs.filter((c) => c.type === 'tags');
  const urlFields = overviewConfigs.filter((c) => c.type === 'url');
  const socialFields = populatedConfigs.filter((c) => c.type === 'social');
  const detailFields = populatedConfigs.filter((c) => c.type !== 'textarea' && c.type !== 'tags' && c.type !== 'social' && c.type !== 'url');

  return (
    <div className="space-y-6">
      {/* Header Action Bar */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
          <span>Overview</span>
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
          Edit Overview
        </button>
      </div>

      {/* 1. Bio / Summary Full-Width Section */}
      {textareas.map((field) => (
        <div
          key={field.key}
          className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-3"
        >
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
            {field.label}
          </h3>
          <p className="text-sm leading-relaxed text-slate-700 whitespace-pre-line font-medium">
            {profile[field.key]}
          </p>
        </div>
      ))}

      {/* 2. Skills & Languages Section */}
      {tagsFields.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {tagsFields.map((field) => {
            const val = profile[field.key];
            const tags = Array.isArray(val) ? val : [];
            const isSkills = field.key === 'skills';

            return (
              <div
                key={field.key}
                className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-3"
              >
                <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>{field.label}</span>
                  <span
                    className={
                      isSkills
                        ? 'text-[10px] font-bold px-2 py-0.5 rounded-full border bg-indigo-50 text-indigo-700 border-indigo-200'
                        : 'text-[10px] font-bold px-2 py-0.5 rounded-full border bg-slate-100 text-slate-700 border-slate-200'
                    }
                  >
                    {tags.length}
                  </span>
                </h3>
                <div className="flex flex-wrap gap-2 pt-1">
                  {tags.map((tag, idx) => (
                    <span
                      key={idx}
                      className={
                        isSkills
                          ? 'px-3 py-1.5 rounded-xl text-xs font-bold border shadow-sm transition-transform hover:scale-105 bg-indigo-50 text-indigo-700 border-indigo-200'
                          : 'px-3 py-1.5 rounded-xl text-xs font-bold border shadow-sm transition-transform hover:scale-105 bg-slate-100 text-slate-700 border-slate-200'
                      }
                    >
                      {isSkills ? `#${tag}` : `🌐 ${tag}`}
                    </span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 3. Credentials & Profile Details Grid */}
      {detailFields.length > 0 && (
        <div className="space-y-3 pt-2">
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
            {role === 'provider' ? 'Organization & Contact Details' : 'Credentials & Background'}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {detailFields.map((field) => {
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
      )}

      {/* 4. Portfolio / Website Link Card */}
      {urlFields.map((field) => {
        const urlVal = profile[field.key];
        if (!urlVal) {
          return (
            <div
              key={field.key}
              className="bg-white rounded-2xl p-6 text-center border border-slate-200 shadow-sm space-y-3"
            >
              <p className="text-sm font-semibold text-slate-500">
                No {field.label.toLowerCase()} link added yet.
              </p>
              <button
                type="button"
                onClick={onEditClick}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all"
              >
                Add {field.label} in Settings
              </button>
            </div>
          );
        }

        return (
          <div
            key={field.key}
            className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
          >
            <div className="space-y-1">
              <span className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
                {field.label}
              </span>
              <p className="text-base font-bold text-slate-900 truncate max-w-md">
                {urlVal}
              </p>
            </div>
            <a
              href={urlVal.startsWith('http') ? urlVal : `https://${urlVal}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 transition-colors"
            >
              Visit Website ↗
            </a>
          </div>
        );
      })}

      {/* 5. Resume Card (Student Role ONLY) */}
      {role === 'student' && (
        <div className="pt-2">
          <ResumeCard />
        </div>
      )}

      {/* 6. Social Links */}
      {socialFields.map((field) => (
        <div
          key={field.key}
          className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm space-y-3"
        >
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
            {field.label}
          </h3>
          <SocialLinksDisplay socialLinks={profile[field.key]} />
        </div>
      ))}

      {/* 7. Invite Friends & Peers Section */}
      <div className="space-y-3 pt-2">
        <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-400">
          Invite Friends & Peers
        </h3>
        <InviteCard />
      </div>
    </div>
  );
}
