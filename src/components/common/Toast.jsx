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
        let border = 'border-sky-500/40 bg-slate-900/95 text-sky-400';
        if (t.type === 'success') {
          Icon = CheckCircle2;
          border = 'border-emerald-500/40 bg-slate-900/95 text-emerald-400';
        } else if (t.type === 'danger' || t.type === 'error') {
          Icon = AlertCircle;
          border = 'border-rose-500/40 bg-slate-900/95 text-rose-400';
        } else if (t.type === 'warning') {
          Icon = AlertTriangle;
          border = 'border-amber-500/40 bg-slate-900/95 text-amber-400';
        }

        return (
          <div
            key={t.id}
            className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-xl backdrop-blur-md transition-all duration-300 animate-in slide-in-from-right-5 ${border}`}
          >
            <Icon className="w-5 h-5 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h4 className="text-sm font-semibold text-white">{t.title}</h4>
              {t.message && <p className="text-xs text-slate-300 mt-0.5 leading-relaxed">{t.message}</p>}
            </div>
            <button
              onClick={() => removeToast(t.id)}
              className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800/60"
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
