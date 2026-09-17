import React from 'react';

export default function ProfileTabs({ activeTab, onTabChange }) {
  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'settings', label: 'Settings & Edit' },
  ];

  return (
    <div className="bg-slate-100 p-1.5 rounded-xl border border-slate-200 flex items-center gap-1.5 mb-6 overflow-x-auto">
      {tabs.map((tab) => {
        const isActive = activeTab === tab.id;

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
