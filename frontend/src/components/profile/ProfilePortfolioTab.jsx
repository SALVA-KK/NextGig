import React from 'react';
import ResumeCard from './ResumeCard';
import { STUDENT_FIELD_CONFIG, PROVIDER_FIELD_CONFIG } from '../../config/profileFieldConfigs';

export default function ProfilePortfolioTab({ profile, role = 'student', onEditClick }) {
  const configs = role === 'provider' ? PROVIDER_FIELD_CONFIG : STUDENT_FIELD_CONFIG;
  const portfolioConfigs = configs.filter((c) => c.tab === 'portfolio');

  return (
    <div className="space-y-6">
      {/* Header Action Bar */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-extrabold text-slate-900 flex items-center gap-2">
          <span>{role === 'provider' ? 'Company Showcase & Web' : 'Portfolio & Work Showcase'}</span>
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
          Edit Link
        </button>
      </div>

      {/* Dynamic Config-Driven Portfolio Cards */}
      {portfolioConfigs.map((field) => {
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

      {/* RESUME CARD (Student Role ONLY - Must still render correctly inside shell) */}
      {role === 'student' && (
        <div className="pt-2">
          <ResumeCard />
        </div>
      )}

      {/* Gig Stories / Case Study Showcase Placeholder Card */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm relative overflow-hidden space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 border border-indigo-200">
          🔒 Upcoming Feature
        </div>
        <h3 className="text-base font-extrabold text-slate-900">Gig Showcase & Verified Client Reviews</h3>
        <p className="text-xs text-slate-500 max-w-lg">
          {role === 'provider'
            ? 'Showcase completed gigs, featured client stories, and impact statistics to attract top talent.'
            : 'Display your top project deliverables, verified employer ratings, and gig stories directly on your profile.'}
        </p>
      </div>
    </div>
  );
}
