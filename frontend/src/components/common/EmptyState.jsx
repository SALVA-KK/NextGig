import React from 'react';

export default function EmptyState({
  icon: Icon,
  title,
  subtitle,
  actionLabel,
  onAction,
  className = '',
}) {
  return (
    <div className={`bg-white rounded-2xl border border-slate-200 p-8 sm:p-12 text-center shadow-sm flex flex-col items-center justify-center space-y-4 ${className}`}>
      {Icon && (
        <div className="w-16 h-16 rounded-full bg-slate-50 border border-slate-100 flex items-center justify-center flex-shrink-0">
          {typeof Icon === 'function' || (typeof Icon === 'object' && Icon.$$typeof) ? (
            <Icon className="w-8 h-8 text-indigo-500" />
          ) : (
            Icon
          )}
        </div>
      )}
      <div className="space-y-1.5 max-w-sm">
        {title && (
          <h3 className="text-base font-bold text-slate-900 tracking-tight">
            {title}
          </h3>
        )}
        {subtitle && (
          <p className="text-xs font-medium text-slate-500 leading-relaxed">
            {subtitle}
          </p>
        )}
      </div>
      {actionLabel && onAction && (
        <div className="pt-2">
          <button
            type="button"
            onClick={onAction}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs uppercase tracking-wider bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-all"
          >
            {actionLabel}
          </button>
        </div>
      )}
    </div>
  );
}
