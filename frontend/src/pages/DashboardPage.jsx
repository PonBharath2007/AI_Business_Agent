import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Receipt,
  AlertCircle,
  TrendingUp,
  RefreshCw,
  ArrowRight,
  Sparkles,
  ExternalLink,
  ShieldCheck,
  AlertOctagon,
  CheckCircle2,
  Clock
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';

const DashboardPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const fetchDashboardData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    setError(null);
    try {
      const res = await api.get(`/dashboard${isRefresh ? '?refresh=true' : ''}`);
      if (res.data) {
        setData(res.data);
      }
    } catch (err) {
      console.error('Dashboard data load error:', err);
      setError('Unable to load dashboard information. Please try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData(false);
  }, [fetchDashboardData]);

  const handleRefresh = () => {
    fetchDashboardData(true);
  };

  const handleActionClick = (action) => {
    if (action.action_target && action.action_target !== 'dashboard') {
      onNavigate(action.action_target);
    } else if (action.action_type === 'send_payment_reminder') {
      onNavigate('invoices');
    } else if (action.action_type === 'open_approvals') {
      onNavigate('approvals');
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto py-4">
        {/* Skeleton Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="space-y-2">
            <div className="h-6 w-48 bg-slate-200 dark:bg-slate-800 rounded-md animate-pulse" />
            <div className="h-3.5 w-64 bg-slate-200 dark:bg-slate-800 rounded-md animate-pulse" />
          </div>
          <div className="h-8 w-24 bg-slate-200 dark:bg-slate-800 rounded-md animate-pulse" />
        </div>

        {/* Skeleton 4 KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-28 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs animate-pulse flex flex-col justify-between">
              <div className="flex justify-between items-center">
                <div className="h-3 w-24 bg-slate-200 dark:bg-slate-800 rounded" />
                <div className="h-8 w-8 bg-slate-200 dark:bg-slate-800 rounded-xl" />
              </div>
              <div className="h-7 w-20 bg-slate-200 dark:bg-slate-800 rounded mt-2" />
            </div>
          ))}
        </div>

        {/* Skeleton Today's Brief */}
        <div className="h-32 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs animate-pulse" />

        {/* Skeleton Recommended Actions */}
        <div className="h-48 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-6 shadow-xs animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto my-16 p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-center shadow-md space-y-4">
        <div className="w-10 h-10 rounded-full bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 mx-auto flex items-center justify-center">
          <AlertCircle className="w-5 h-5" />
        </div>
        <h3 className="text-base font-bold text-slate-900 dark:text-white">{error}</h3>
        <p className="text-xs text-slate-500">Please check your network connection and try again.</p>
        <Button onClick={() => fetchDashboardData(true)} variant="primary" size="sm" icon={RefreshCw}>
          Retry Now
        </Button>
      </div>
    );
  }

  const totalCustomers = data?.total_customers ?? 0;
  const pendingInvoices = data?.pending_invoices ?? 0;
  const overdueInvoices = data?.overdue_invoices ?? 0;
  const monthlyIncome = data?.monthly_income ?? 0.0;
  const todayBrief = data?.today_brief || 'All operations are currently clear. Ready to process new invoices and manage customer accounts.';
  const recommendedActions = data?.recommended_actions || [];

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-2">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
            Business Overview
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Real-time business status and operational priorities for today.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleRefresh}
            variant="secondary"
            size="sm"
            loading={refreshing}
            icon={RefreshCw}
            className="text-xs"
          >
            Refresh
          </Button>
        </div>
      </div>

      {/* 4 CORE KPI CARDS GRID */}
      {/* Desktop: 4 in a row | Tablet: 2 x 2 | Mobile: 1 per row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* 1. TOTAL CUSTOMERS */}
        <div
          onClick={() => onNavigate('customers')}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Total Customers
            </span>
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100 dark:bg-indigo-950/40 dark:text-indigo-400 dark:border-indigo-900/60">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              {totalCustomers}
            </span>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Total Customers
            </p>
          </div>
        </div>

        {/* 2. PENDING INVOICES */}
        <div
          onClick={() => onNavigate('invoices')}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Pending Invoices
            </span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600 border border-amber-100 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-900/60">
              <Receipt className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              {pendingInvoices}
            </span>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Pending Invoices
            </p>
          </div>
        </div>

        {/* 3. OVERDUE INVOICES */}
        <div
          onClick={() => onNavigate('invoices')}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Overdue Invoices
            </span>
            <div className="p-2 rounded-xl bg-rose-50 text-rose-600 border border-rose-100 dark:bg-rose-950/40 dark:text-rose-400 dark:border-rose-900/60">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className={`text-2xl sm:text-3xl font-bold tracking-tight ${overdueInvoices > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-900 dark:text-white'}`}>
              {overdueInvoices}
            </span>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Overdue Invoices
            </p>
          </div>
        </div>

        {/* 4. MONTHLY INCOME */}
        <div
          onClick={() => onNavigate('analytics')}
          className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 shadow-xs hover:border-slate-300 dark:hover:border-slate-700 transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Monthly Income
            </span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-900/60">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              {formatMoney(monthlyIncome)}
            </span>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Monthly Income
            </p>
          </div>
        </div>
      </div>

      {/* SECTION 5: TODAY'S BRIEF */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xs">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-slate-800">
          <span className="text-base" role="img" aria-label="brain">🧠</span>
          <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white tracking-tight">
            Today's Brief
          </h2>
        </div>
        <div className="mt-3">
          <p className="text-sm sm:text-base text-slate-700 dark:text-slate-200 font-medium leading-relaxed">
            {todayBrief}
          </p>
        </div>
      </div>

      {/* SECTION 6: RECOMMENDED ACTIONS */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-base" role="img" aria-label="robot">🤖</span>
            <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white tracking-tight">
              Recommended Actions
            </h2>
          </div>
          <span className="text-xs text-slate-400">
            {recommendedActions.length} action{recommendedActions.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="space-y-2.5">
          {!recommendedActions.length ? (
            <div className="py-6 text-center text-xs text-slate-500">
              No recommended actions today.
            </div>
          ) : (
            recommendedActions.map((action) => {
              // Priority indicator & badge styling
              let indicator = '🟡';
              let badgeClasses = 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800';

              if (action.priority === 'Critical') {
                indicator = '🔴';
                badgeClasses = 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-800';
              } else if (action.priority === 'High') {
                indicator = '🟠';
                badgeClasses = 'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950/40 dark:text-orange-300 dark:border-orange-800';
              } else if (action.priority === 'Low') {
                indicator = '🟢';
                badgeClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800';
              }

              return (
                <div
                  key={action.id}
                  onClick={() => handleActionClick(action)}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-850/40 hover:bg-slate-100/70 dark:hover:bg-slate-800/60 transition-colors cursor-pointer"
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <span className="text-sm shrink-0 mt-0.5">{indicator}</span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-xs sm:text-sm font-semibold text-slate-900 dark:text-white truncate">
                          {action.title}
                        </h4>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeClasses}`}>
                          {action.priority}
                        </span>
                      </div>
                      {action.description && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1">
                          {action.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {action.action_type !== 'none' && (
                    <div className="flex items-center gap-1 text-xs font-semibold text-indigo-600 dark:text-indigo-400 self-end sm:self-center shrink-0">
                      <span>View</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
