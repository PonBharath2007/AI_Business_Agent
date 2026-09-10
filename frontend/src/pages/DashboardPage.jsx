import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Receipt,
  AlertCircle,
  TrendingUp,
  RefreshCw,
  ArrowRight
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
      <div className="space-y-6 max-w-5xl mx-auto py-2">
        {/* Skeleton Header */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-[#222227]">
          <div className="space-y-2">
            <div className="h-6 w-48 bg-slate-200 dark:bg-[#1c1c21] rounded-md animate-pulse" />
            <div className="h-3.5 w-64 bg-slate-200 dark:bg-[#1c1c21] rounded-md animate-pulse" />
          </div>
          <div className="h-8 w-24 bg-slate-200 dark:bg-[#1c1c21] rounded-md animate-pulse" />
        </div>

        {/* Skeleton 4 KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-28 bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-5 shadow-xs animate-pulse flex flex-col justify-between"
            >
              <div className="flex justify-between items-center">
                <div className="h-3 w-24 bg-slate-200 dark:bg-[#1c1c21] rounded" />
                <div className="h-8 w-8 bg-slate-200 dark:bg-[#1c1c21] rounded-xl" />
              </div>
              <div className="h-7 w-20 bg-slate-200 dark:bg-[#1c1c21] rounded mt-2" />
            </div>
          ))}
        </div>

        {/* Skeleton Today's Brief */}
        <div className="h-32 bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-6 shadow-xs animate-pulse" />

        {/* Skeleton Recommended Actions */}
        <div className="h-48 bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-6 shadow-xs animate-pulse" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto my-16 p-6 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] text-center shadow-md space-y-4">
        <div className="w-10 h-10 rounded-full bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 mx-auto flex items-center justify-center">
          <AlertCircle className="w-5 h-5" />
        </div>
        <h3 className="text-base font-bold text-slate-900 dark:text-white">{error}</h3>
        <p className="text-xs text-slate-500 dark:text-slate-400">
          Please check your network connection and try again.
        </p>
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
  const todayBrief =
    data?.today_brief ||
    'All operations are currently clear. Ready to process new invoices and manage customer accounts.';
  const recommendedActions = data?.recommended_actions || [];

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-2">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-[#222227]">
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
            className="text-xs font-semibold"
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
          className="bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-5 shadow-xs hover:border-slate-300 dark:hover:border-[#383842] transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Total Customers
            </span>
            <div className="p-2 rounded-xl bg-indigo-50 text-indigo-600 border border-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-400 dark:border-indigo-500/20">
              <Users className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              {totalCustomers}
            </span>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Active Client Profiles
            </p>
          </div>
        </div>

        {/* 2. PENDING INVOICES */}
        <div
          onClick={() => onNavigate('invoices')}
          className="bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-5 shadow-xs hover:border-slate-300 dark:hover:border-[#383842] transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Pending Invoices
            </span>
            <div className="p-2 rounded-xl bg-amber-50 text-amber-600 border border-amber-100 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/20">
              <Receipt className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              {pendingInvoices}
            </span>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Awaiting Settlement
            </p>
          </div>
        </div>

        {/* 3. OVERDUE INVOICES */}
        <div
          onClick={() => onNavigate('invoices')}
          className="bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-5 shadow-xs hover:border-slate-300 dark:hover:border-[#383842] transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Overdue Invoices
            </span>
            <div className="p-2 rounded-xl bg-rose-50 text-rose-600 border border-rose-100 dark:bg-rose-500/10 dark:text-rose-400 dark:border-rose-500/20">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span
              className={`text-2xl sm:text-3xl font-bold tracking-tight ${
                overdueInvoices > 0 ? 'text-rose-600 dark:text-rose-400' : 'text-slate-900 dark:text-white'
              }`}
            >
              {overdueInvoices}
            </span>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Requires Attention
            </p>
          </div>
        </div>

        {/* 4. MONTHLY INCOME */}
        <div
          onClick={() => onNavigate('analytics')}
          className="bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-5 shadow-xs hover:border-slate-300 dark:hover:border-[#383842] transition-all cursor-pointer flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Monthly Income
            </span>
            <div className="p-2 rounded-xl bg-emerald-50 text-emerald-600 border border-emerald-100 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/20">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
              {formatMoney(monthlyIncome)}
            </span>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Total Revenue MTD
            </p>
          </div>
        </div>
      </div>

      {/* SECTION 2: TODAY'S BRIEF */}
      <div className="bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-5 sm:p-6 shadow-xs">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-[#26262c]">
          <span className="text-base" role="img" aria-label="brain">🧠</span>
          <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white tracking-tight">
            Today's Brief
          </h2>
        </div>
        <div className="mt-3">
          <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-200 font-medium leading-relaxed">
            {todayBrief}
          </p>
        </div>
      </div>

      {/* SECTION 3: RECOMMENDED ACTIONS */}
      <div className="bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] rounded-2xl p-5 sm:p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-[#26262c]">
          <div className="flex items-center gap-2">
            <span className="text-base" role="img" aria-label="robot">🤖</span>
            <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white tracking-tight">
              Recommended Actions
            </h2>
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">
            {recommendedActions.length} action{recommendedActions.length !== 1 ? 's' : ''}
          </span>
        </div>

        <div className="space-y-3">
          {!recommendedActions.length ? (
            <div className="py-8 text-center text-xs text-slate-500 dark:text-slate-400 font-medium">
              No recommended actions today. All operations up to date.
            </div>
          ) : (
            recommendedActions.map((action) => {
              // Status colors: icon, priority indicator & small badge only - card remains neutral
              let indicator = '🟡';
              let badgeClasses =
                'bg-amber-50 text-amber-800 border-amber-200 dark:bg-amber-950/30 dark:text-amber-300 dark:border-amber-800/50';

              if (action.priority === 'Critical') {
                indicator = '🔴';
                badgeClasses =
                  'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/30 dark:text-rose-300 dark:border-rose-800/50';
              } else if (action.priority === 'High') {
                indicator = '🟠';
                badgeClasses =
                  'bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-950/30 dark:text-orange-300 dark:border-orange-800/50';
              } else if (action.priority === 'Low') {
                indicator = '🟢';
                badgeClasses =
                  'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/30 dark:text-emerald-300 dark:border-emerald-800/50';
              }

              return (
                <div
                  key={action.id}
                  onClick={() => handleActionClick(action)}
                  className="group flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl border border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50/80 dark:bg-[#18181d] dark:hover:bg-[#1f1f25] dark:border-[#26262c] dark:hover:border-[#383842] shadow-2xs hover:shadow-xs transition-all cursor-pointer"
                >
                  <div className="flex items-start gap-3 min-w-0">
                    <span className="text-sm shrink-0 mt-0.5">{indicator}</span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h4 className="text-xs sm:text-sm font-bold text-slate-900 dark:text-white truncate group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                          {action.title}
                        </h4>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${badgeClasses}`}>
                          {action.priority}
                        </span>
                      </div>
                      {action.description && (
                        <p className="text-xs text-slate-600 dark:text-slate-300 mt-1 line-clamp-1">
                          {action.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {action.action_type !== 'none' && (
                    <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-600 dark:text-indigo-400 px-3 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-500/15 border border-indigo-200 dark:border-indigo-500/30 self-end sm:self-center shrink-0 group-hover:bg-indigo-100 dark:group-hover:bg-indigo-500/25 transition-colors">
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
