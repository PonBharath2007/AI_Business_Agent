import React from 'react';

const Badge = ({ variant = 'info', children, className = '' }) => {
  const styles = {
    urgent: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
    danger: 'bg-rose-500/15 text-rose-400 border border-rose-500/30',
    warning: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
    pending: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
    success: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
    paid: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
    completed: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
    info: 'bg-sky-500/15 text-sky-300 border border-sky-500/30',
    ai: 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm shadow-indigo-500/20',
    gray: 'bg-slate-700/50 text-slate-300 border border-slate-600/40'
  };

  const vKey = variant.toLowerCase();
  const selectedStyle = styles[vKey] || styles.info;

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium tracking-wide ${selectedStyle} ${className}`}>
      {children}
    </span>
  );
};

export default Badge;
