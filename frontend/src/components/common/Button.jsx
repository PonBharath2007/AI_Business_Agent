import React from 'react';

const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  onClick,
  disabled = false,
  loading = false,
  className = '',
  type = 'button',
  icon: Icon
}) => {
  const base =
    'inline-flex items-center justify-center font-semibold rounded-xl transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-[#09090b] disabled:opacity-50 disabled:pointer-events-none cursor-pointer select-none';

  const variants = {
    // Primary Button: Strong Brand Background, Crisp White Text, Solid Visual Presence
    primary:
      'bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white shadow-xs focus:ring-indigo-500 border border-indigo-700/30 dark:border-indigo-500/40',

    // Secondary Button: Light Background with High-Contrast Border & Dark Text (Light), Dark Neutral (Dark)
    secondary:
      'bg-white hover:bg-slate-100 active:bg-slate-200 text-slate-800 border border-slate-300 shadow-2xs focus:ring-slate-400 dark:bg-[#1c1c21] dark:hover:bg-[#27272e] dark:active:bg-[#141417] dark:text-[#f4f4f5] dark:border-[#2e2e36] dark:focus:ring-slate-500',

    // Success Button: Green Accent, White Text
    success:
      'bg-emerald-600 hover:bg-emerald-700 active:bg-emerald-800 text-white shadow-xs focus:ring-emerald-500 border border-emerald-700/30',

    // Danger Button: Red Accent, White Text
    danger:
      'bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white shadow-xs focus:ring-rose-500 border border-rose-700/30',

    // Warning Button: Amber/Orange Accent, White Text
    warning:
      'bg-amber-600 hover:bg-amber-700 active:bg-amber-800 text-white shadow-xs focus:ring-amber-500 border border-amber-700/30',

    // Ghost Button: Transparent, Subtle Hover
    ghost:
      'bg-transparent hover:bg-slate-100 active:bg-slate-200 text-slate-700 hover:text-slate-900 border border-transparent focus:ring-slate-400 dark:text-slate-300 dark:hover:bg-[#1c1c21] dark:hover:text-[#f4f4f5]',

    // Outline Button
    outline:
      'bg-transparent border border-slate-300 text-slate-800 hover:bg-slate-50 dark:border-[#2e2e36] dark:text-[#f4f4f5] dark:hover:bg-[#1c1c21] focus:ring-slate-400'
  };

  const sizes = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2 text-xs sm:text-sm gap-2',
    lg: 'px-5 py-2.5 text-sm sm:text-base gap-2.5'
  };

  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      className={`${base} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${className}`}
    >
      {loading ? (
        <svg
          className="animate-spin -ml-0.5 mr-1.5 h-3.5 w-3.5 text-current"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
          />
        </svg>
      ) : Icon ? (
        <Icon className="w-4 h-4 shrink-0" />
      ) : null}
      {children}
    </button>
  );
};

export default Button;
