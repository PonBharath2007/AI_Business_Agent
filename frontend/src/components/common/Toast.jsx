import React from 'react';
import { useNotifications } from '../../context/NotificationContext';
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from 'lucide-react';

const Toast = () => {
  const { toasts, removeToast } = useNotifications();

  if (!toasts.length) return null;

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2.5 max-w-sm w-full pointer-events-none">
      {toasts.map((t) => {
        let Icon = Info;
        let border =
          'border-sky-200 dark:border-sky-500/40 bg-white dark:bg-[#141417] text-sky-600 dark:text-sky-400';
        if (t.type === 'success') {
          Icon = CheckCircle2;
          border =
            'border-emerald-200 dark:border-emerald-500/40 bg-white dark:bg-[#141417] text-emerald-600 dark:text-emerald-400';
        } else if (t.type === 'danger' || t.type === 'error') {
          Icon = AlertCircle;
          border =
            'border-rose-200 dark:border-rose-500/40 bg-white dark:bg-[#141417] text-rose-600 dark:text-rose-400';
        } else if (t.type === 'warning') {
          Icon = AlertTriangle;
          border =
            'border-amber-200 dark:border-amber-500/40 bg-white dark:bg-[#141417] text-amber-600 dark:text-amber-400';
        }

        return (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-2xl border shadow-lg transition-all duration-200 animate-in slide-in-from-right-5 ${border}`}
          >
            <Icon className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h4 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white">
                {t.title}
              </h4>
              {t.message && (
                <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed">
                  {t.message}
                </p>
              )}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-[#1c1c21] transition-colors cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};

export default Toast;
