import React from 'react';

const StatCard = ({ title, value, subtitle, icon: Icon, color = 'indigo', badgeText, onClick }) => {
  const colorMap = {
    indigo: 'from-indigo-500/20 to-indigo-900/10 border-indigo-500/30 text-indigo-400',
    rose: 'from-rose-500/20 to-rose-900/10 border-rose-500/30 text-rose-400',
    emerald: 'from-emerald-500/20 to-emerald-900/10 border-emerald-500/30 text-emerald-400',
    amber: 'from-amber-500/20 to-amber-900/10 border-amber-500/30 text-amber-400',
    sky: 'from-sky-500/20 to-sky-900/10 border-sky-500/30 text-sky-400',
    violet: 'from-violet-500/20 to-violet-900/10 border-violet-500/30 text-violet-400'
  };

  const bgStyle = colorMap[color] || colorMap.indigo;

  return (
    <div
      onClick={onClick}
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${bgStyle} p-5 border shadow-lg backdrop-blur-md transition-all duration-300 hover:scale-[1.02] ${onClick ? 'cursor-pointer' : ''}`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">{title}</span>
        {Icon && (
          <div className="p-2.5 rounded-xl bg-slate-900/60 border border-slate-800 shadow-inner">
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl sm:text-3xl font-bold tracking-tight text-white">{value}</span>
        {badgeText && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800/80 text-slate-300 border border-slate-700 font-medium">
            {badgeText}
          </span>
        )}
      </div>

      {subtitle && (
        <p className="mt-1 text-xs text-slate-400 flex items-center gap-1">{subtitle}</p>
      )}
    </div>
  );
};

export default StatCard;
