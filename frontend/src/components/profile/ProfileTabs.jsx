import React from 'react';

export default function ProfileTabs({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'about', label: 'About' },
    { id: 'portfolio', label: 'Portfolio' },
    { id: 'stories', label: 'Gig Stories', isLocked: true },
    { id: 'settings', label: 'Settings & Edit' },
  ];

  return (
    <div className="bg-slate-100 p-1.5 rounded-xl border border-slate-200 flex items-center gap-1.5 mb-6 overflow-x-auto">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

        if (tab.isLocked) {
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                alert('Gig Stories feature is coming soon! Reserve your place as a top freelancer on NextGig.');
              }}
              className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-wider text-slate-400 cursor-not-allowed transition-colors whitespace-nowrap"
              title="Coming Soon"
            >
              <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
              <span>{tab.label}</span>
              <span className="px-2 py-0.5 text-[9px] font-extrabold uppercase rounded-md bg-slate-200 text-slate-600">
                Soon
              </span>
            </button>
          );
        }

        return (
          <button
            key={tab.id}
            type="button"
            onClick={() => onTabChange(tab.id)}
            className={`px-5 py-2.5 rounded-lg text-xs font-extrabold uppercase tracking-wider transition-all whitespace-nowrap ${
              isActive
                ? 'bg-white text-indigo-600 shadow-sm border border-slate-200'
                : 'text-slate-600 hover:text-slate-900 hover:bg-slate-200/50'
            }`}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
