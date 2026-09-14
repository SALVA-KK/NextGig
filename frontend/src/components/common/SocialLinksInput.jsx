import React from 'react';

const SOCIAL_PLATFORMS = [
  { key: 'linkedin', label: 'LinkedIn', placeholder: 'https://linkedin.com/in/username' },
  { key: 'github', label: 'GitHub', placeholder: 'https://github.com/username' },
  { key: 'instagram', label: 'Instagram', placeholder: 'https://instagram.com/username' },
  { key: 'twitter', label: 'Twitter / X', placeholder: 'https://x.com/username' },
  { key: 'website', label: 'Personal / Org Website', placeholder: 'https://yourwebsite.com' },
];

export default function SocialLinksInput({ value = {}, onChange }) {
  const handleChange = (key, val) => {
    const updated = { ...value, [key]: val };
    onChange(updated);
  };

  return (
    <div className="space-y-4">
      <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-500">Social & Web Links</h4>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
        {SOCIAL_PLATFORMS.map(({ key, label, placeholder }) => (
          <div key={key} className="space-y-2">
            <label htmlFor={`social_${key}`} className="block text-xs font-bold text-slate-700 mb-2">
              {label}
            </label>
            <input
              id={`social_${key}`}
              name={`social_${key}`}
              type="url"
              placeholder={placeholder}
              value={value[key] || ''}
              onChange={(e) => handleChange(key, e.target.value)}
              className="w-full px-4 py-2.5 text-sm rounded-xl border border-slate-300 bg-white text-slate-900 placeholder:text-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all shadow-sm"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
