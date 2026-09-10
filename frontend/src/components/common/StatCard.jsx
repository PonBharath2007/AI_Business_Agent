import React from 'react';

const StatCard = ({ title, value, subtitle, icon: Icon, color = 'indigo', badgeText, onClick }) => {
  const iconColorMap = {
    indigo:
      'bg-indigo-50 text-indigo-600 border-indigo-100 dark:bg-indigo-950/30 dark:text-indigo-400 dark:border-indigo-800/40',
    amber:
      'bg-amber-50 text-amber-600 border-amber-100 dark:bg-amber-950/30 dark:text-amber-400 dark:border-amber-800/40',
    rose:
      'bg-rose-50 text-rose-600 border-rose-100 dark:bg-rose-950/30 dark:text-rose-400 dark:border-rose-800/40',
    emerald:
      'bg-emerald-50 text-emerald-600 border-emerald-100 dark:bg-emerald-950/30 dark:text-emerald-400 dark:border-emerald-800/40',
    sky:
      'bg-sky-50 text-sky-600 border-sky-100 dark:bg-sky-950/30 dark:text-sky-400 dark:border-sky-800/40',
    violet:
      'bg-violet-50 text-violet-600 border-violet-100 dark:bg-violet-950/30 dark:text-violet-400 dark:border-violet-800/40'
  };

  const iconStyle = iconColorMap[color] || iconColorMap.indigo;

  return (
    <div
      onClick={onClick}
      className={`bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-5 shadow-xs transition-all duration-150 hover:shadow-md hover:border-slate-300 dark:hover:border-[#383842] flex flex-col justify-between ${
        onClick ? 'cursor-pointer' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          {title}
        </span>
        {Icon && (
          <div className={`p-2 rounded-xl border ${iconStyle}`}>
            <Icon className="w-4 h-4" />
          </div>
        )}
      </div>

      <div className="mt-3">
        <div className="flex items-baseline gap-2">
          <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
            {value}
          </span>
          {badgeText && (
            <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 dark:bg-[#1c1c21] text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-[#2e2e36] font-medium">
              {badgeText}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400 truncate">
            {subtitle}
          </p>
        )}
      </div>
    </div>
  );
};

export default StatCard;
