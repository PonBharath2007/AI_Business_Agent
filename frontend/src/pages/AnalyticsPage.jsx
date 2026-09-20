import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell
} from 'recharts';
import {
  BarChart3,
  TrendingUp,
  Clock,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  Calendar,
  Zap,
  Sliders,
  Play,
  HelpCircle,
  DollarSign,
  Download,
  FileSpreadsheet,
  Printer,
  RefreshCw,
  ArrowUpRight,
  Filter,
  Layers,
  FileText
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import { useTheme } from '../context/ThemeContext';
import StatCard from '../components/common/StatCard';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';

const STATUS_COLORS = {
  paid: '#10b981',
  partially_paid: '#6366f1',
  unpaid: '#f59e0b',
  overdue: '#f43f5e'
};

const AnalyticsPage = () => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();
  const { isDark } = useTheme();

  // Selected Filter States
  const todayStr = useMemo(() => {
    const d = new Date();
    return d.toISOString().split('T')[0];
  }, []);

  const yesterdayStr = useMemo(() => {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return d.toISOString().split('T')[0];
  }, []);

  const currentMonthStr = useMemo(() => {
    const d = new Date();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${d.getFullYear()}-${m}`;
  }, []);

  const prevMonthStr = useMemo(() => {
    const d = new Date();
    d.setDate(1);
    d.setMonth(d.getMonth() - 1);
    const m = String(d.getMonth() + 1).padStart(2, '0');
    return `${d.getFullYear()}-${m}`;
  }, []);

  const [dateFilterType, setDateFilterType] = useState('today'); // 'today', 'yesterday', 'custom'
  const [selectedDate, setSelectedDate] = useState(todayStr);

  const [monthFilterType, setMonthFilterType] = useState('current'); // 'current', 'prev', 'custom'
  const [selectedMonth, setSelectedMonth] = useState(currentMonthStr);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [incomeData, setIncomeData] = useState(null);

  // Active Report Tab: 'daily_income', 'monthly_income', 'outstanding', 'overdue'
  const [activeReportTab, setActiveReportTab] = useState('daily_income');
  const [exporting, setExporting] = useState(false);

  // Optional Secondary Intelligence Modules
  const [showIntelligenceTools, setShowIntelligenceTools] = useState(false);
  const [cashFlow, setCashFlow] = useState(null);
  const [rcaData, setRcaData] = useState(null);
  const [rcaLoading, setRcaLoading] = useState(false);
  const [simScenario, setSimScenario] = useState('early_discount');
  const [simDaysDelay, setSimDaysDelay] = useState(30);
  const [simDiscountPct, setSimDiscountPct] = useState(5.0);
  const [simBoostPct, setSimBoostPct] = useState(25.0);
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);

  // Fetch real analytics data
  const fetchAnalytics = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      const res = await api.get(`/analytics/income-overview?date=${selectedDate}&month=${selectedMonth}`);
      setIncomeData(res.data);
    } catch (err) {
      console.error('Error loading analytics:', err);
      addToast('error', 'Analytics Error', 'Failed to retrieve real-time income analytics.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedDate, selectedMonth, addToast]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  // Handle Daily Filter selection
  const handleDateFilterChange = (type, customVal = null) => {
    setDateFilterType(type);
    if (type === 'today') {
      setSelectedDate(todayStr);
    } else if (type === 'yesterday') {
      setSelectedDate(yesterdayStr);
    } else if (type === 'custom' && customVal) {
      setSelectedDate(customVal);
    }
  };

  // Handle Monthly Filter selection
  const handleMonthFilterChange = (type, customVal = null) => {
    setMonthFilterType(type);
    if (type === 'current') {
      setSelectedMonth(currentMonthStr);
    } else if (type === 'prev') {
      setSelectedMonth(prevMonthStr);
    } else if (type === 'custom' && customVal) {
      setSelectedMonth(customVal);
    }
  };

  // Export handlers
  const handleExportCSV = async () => {
    setExporting(true);
    try {
      const res = await api.get(
        `/analytics/reports/export?report_type=${activeReportTab}&format=csv&date=${selectedDate}&month=${selectedMonth}`,
        { responseType: 'blob' }
      );
      const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `OpsNova_${activeReportTab}_${selectedDate || selectedMonth}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      addToast('success', 'Report Exported', 'CSV report downloaded successfully.');
    } catch (err) {
      console.error('Export CSV error:', err);
      addToast('error', 'Export Failed', 'Could not export CSV report.');
    } finally {
      setExporting(false);
    }
  };

  const handleExportExcel = async () => {
    setExporting(true);
    try {
      const res = await api.get(
        `/analytics/reports/export?report_type=${activeReportTab}&format=csv&date=${selectedDate}&month=${selectedMonth}`,
        { responseType: 'blob' }
      );
      const blob = new Blob([res.data], { type: 'application/vnd.ms-excel;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `OpsNova_${activeReportTab}_${selectedDate || selectedMonth}.xls`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      addToast('success', 'Excel Exported', 'Excel report downloaded successfully.');
    } catch (err) {
      console.error('Export Excel error:', err);
      addToast('error', 'Export Failed', 'Could not export Excel report.');
    } finally {
      setExporting(false);
    }
  };

  const handleExportPDF = () => {
    window.print();
  };

  // Optional Intelligence Tools
  const loadIntelligenceData = async () => {
    if (cashFlow) return;
    try {
      const cfRes = await api.get('/intelligence/cash-flow');
      setCashFlow(cfRes.data);
    } catch (err) {
      console.error('Cash flow error:', err);
    }
  };

  const handleRunRCA = async () => {
    setRcaLoading(true);
    try {
      const res = await api.post('/intelligence/root-cause', { query: 'Why are payments getting delayed?' });
      setRcaData(res.data);
    } catch (err) {
      addToast('error', 'RCA Error', 'Failed to generate root cause analysis.');
    } finally {
      setRcaLoading(false);
    }
  };

  const handleRunSimulation = async () => {
    setSimLoading(true);
    try {
      const res = await api.post('/intelligence/what-if', {
        scenario: simScenario,
        param_days_delay: parseInt(simDaysDelay, 10),
        param_discount_pct: parseFloat(simDiscountPct),
        param_collection_boost_pct: parseFloat(simBoostPct)
      });
      setSimResult(res.data);
    } catch (err) {
      addToast('error', 'Simulation Error', 'Failed to run scenario simulation.');
    } finally {
      setSimLoading(false);
    }
  };

  if (loading || !incomeData) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
        <p className="text-sm text-slate-400 font-medium">Computing Real-time Income & Reports...</p>
      </div>
    );
  }

  const {
    daily_income,
    daily_payments_count,
    monthly_income,
    monthly_payments_count,
    avg_daily_income,
    total_pending,
    total_overdue,
    revenue_vs_income,
    payment_status_distribution,
    daily_income_trend,
    has_daily_income_data,
    monthly_income_trend,
    has_monthly_income_data,
    ai_business_insight,
    reports
  } = incomeData;

  const gridStroke = isDark ? '#26262c' : '#e2e8f0';
  const textStroke = isDark ? '#a1a1aa' : '#475569';
  const tooltipStyle = {
    backgroundColor: isDark ? '#141417' : '#ffffff',
    borderColor: isDark ? '#2c2c34' : '#e2e8f0',
    borderRadius: '0.75rem',
    fontSize: '12px',
    color: isDark ? '#f4f4f5' : '#0f172a',
    boxShadow: isDark ? '0 10px 15px -3px rgba(0,0,0,0.6)' : '0 4px 6px -1px rgba(0,0,0,0.08)'
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-2">
      {/* 1. Header & Quick Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-200 dark:border-[#222227]">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              Analytics & Reports
            </h1>
            <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300 border border-indigo-100 dark:border-indigo-500/30">
              OpsNova AI
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Real collected income, outstanding receivables, daily trend trajectories, and official accounting reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={() => fetchAnalytics(true)}
            variant="secondary"
            size="sm"
            loading={refreshing}
            icon={RefreshCw}
            className="text-xs font-semibold"
          >
            Refresh Data
          </Button>
        </div>
      </div>

      {/* 2. Interactive Filter Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-4 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs">
        {/* Daily Income Filter */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              Daily Income Date
            </label>
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              Selected: {incomeData.selected_date_formatted}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => handleDateFilterChange('today')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                dateFilterType === 'today'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-[#1c1c22] text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-[#25252d]'
              }`}
            >
              Today
            </button>
            <button
              type="button"
              onClick={() => handleDateFilterChange('yesterday')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                dateFilterType === 'yesterday'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-[#1c1c22] text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-[#25252d]'
              }`}
            >
              Yesterday
            </button>
            <div className="relative flex items-center">
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => handleDateFilterChange('custom', e.target.value)}
                className={`text-xs px-2.5 py-1.5 rounded-xl border font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500 ${
                  dateFilterType === 'custom'
                    ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20 text-indigo-700 dark:text-indigo-300 font-bold'
                    : 'border-slate-300 dark:border-[#2e2e36] bg-white dark:bg-[#18181d] text-slate-800 dark:text-slate-200'
                }`}
              />
            </div>
          </div>
        </div>

        {/* Monthly Income Filter */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
              <TrendingUp className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
              Monthly Income Period
            </label>
            <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
              Selected: {incomeData.selected_month_formatted}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => handleMonthFilterChange('current')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                monthFilterType === 'current'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-[#1c1c22] text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-[#25252d]'
              }`}
            >
              Current Month
            </button>
            <button
              type="button"
              onClick={() => handleMonthFilterChange('prev')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                monthFilterType === 'prev'
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-slate-100 dark:bg-[#1c1c22] text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-[#25252d]'
              }`}
            >
              Previous Month
            </button>
            <div className="relative flex items-center">
              <input
                type="month"
                value={selectedMonth}
                onChange={(e) => handleMonthFilterChange('custom', e.target.value)}
                className={`text-xs px-2.5 py-1.5 rounded-xl border font-medium focus:outline-none focus:ring-1 focus:ring-indigo-500 ${
                  monthFilterType === 'custom'
                    ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20 text-indigo-700 dark:text-indigo-300 font-bold'
                    : 'border-slate-300 dark:border-[#2e2e36] bg-white dark:bg-[#18181d] text-slate-800 dark:text-slate-200'
                }`}
              />
            </div>
          </div>
        </div>
      </div>

      {/* 3. ROW 1: PRIMARY INCOME KPIS (Daily & Monthly) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Daily Income Card */}
        <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs uppercase font-bold tracking-wider text-slate-500 dark:text-slate-400">
                Daily Income
              </span>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                Amount collected on {incomeData.selected_date_formatted}
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-500/30">
              {daily_payments_count} {daily_payments_count === 1 ? 'payment' : 'payments'}
            </span>
          </div>

          <div className="mt-4">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-emerald-600 dark:text-emerald-400 tracking-tight">
              {formatMoney(daily_income)}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              Actual collected money (unpaid invoice totals excluded)
            </p>
          </div>
        </div>

        {/* Monthly Income Card */}
        <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs uppercase font-bold tracking-wider text-slate-500 dark:text-slate-400">
                Monthly Income
              </span>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                Total collected during {incomeData.selected_month_formatted}
              </p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-indigo-50 text-indigo-700 dark:bg-indigo-500/15 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30">
              {monthly_payments_count} {monthly_payments_count === 1 ? 'payment' : 'payments'}
            </span>
          </div>

          <div className="mt-4">
            <h2 className="text-3xl sm:text-4xl font-extrabold text-indigo-600 dark:text-indigo-400 tracking-tight">
              {formatMoney(monthly_income)}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              Real database settlement records
            </p>
          </div>
        </div>
      </div>

      {/* 4. ROW 2: FINANCIAL HEALTH & COMPARISON */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Pending */}
        <div className="p-4 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-amber-600 dark:text-amber-400">
              Total Pending
            </span>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {formatMoney(total_pending)}
            </p>
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 block">
            Outstanding unpaid balances
          </span>
        </div>

        {/* Total Overdue */}
        <div className="p-4 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-rose-600 dark:text-rose-400">
              Total Overdue
            </span>
            <p className="text-2xl font-bold text-rose-600 dark:text-rose-400 mt-1">
              {formatMoney(total_overdue)}
            </p>
          </div>
          <span className="text-[11px] text-rose-500/90 dark:text-rose-400/80 mt-2 block">
            Due date elapsed past-due
          </span>
        </div>

        {/* Average Daily Income */}
        <div className="p-4 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-indigo-600 dark:text-indigo-400">
              Avg Daily Income
            </span>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {formatMoney(avg_daily_income)}
            </p>
          </div>
          <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 block">
            Calculated across {incomeData.selected_month_formatted}
          </span>
        </div>

        {/* Revenue Distinction (Invoice Value vs Collected) */}
        <div className="p-4 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs flex flex-col justify-between">
          <div>
            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-600 dark:text-slate-300">
              Total Invoiced
            </span>
            <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">
              {formatMoney(revenue_vs_income.invoice_value)}
            </p>
          </div>
          <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 flex items-center justify-between border-t border-slate-100 dark:border-[#26262c] pt-1">
            <span>Collected: <strong>{formatMoney(revenue_vs_income.collected)}</strong></span>
            <span>Pending: <strong>{formatMoney(revenue_vs_income.pending)}</strong></span>
          </div>
        </div>
      </div>

      {/* 5. ROW 3: CHARTS (Daily Income Trend & Monthly Income Trend) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily Income Trend */}
        <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-[#26262c]">
            <div>
              <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                Daily Income Trend
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Income collected each day in {incomeData.selected_month_formatted}
              </p>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
              Daily Cash Flow
            </span>
          </div>

          <div className="h-64 mt-4">
            {has_daily_income_data ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={daily_income_trend}>
                  <defs>
                    <linearGradient id="dailyIncomeGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                  <XAxis dataKey="date" stroke={textStroke} fontSize={10} interval="preserveStartEnd" />
                  <YAxis stroke={textStroke} fontSize={10} />
                  <Tooltip
                    formatter={(val) => [formatMoney(val), 'Income Collected']}
                    contentStyle={tooltipStyle}
                  />
                  <Area
                    type="monotone"
                    dataKey="income"
                    stroke="#10b981"
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#dailyIncomeGradient)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-2">
                <Clock className="w-8 h-8 text-slate-400" />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">₹0</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No income recorded for this period.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Monthly Income Trend */}
        <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs">
          <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-[#26262c]">
            <div>
              <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                Monthly Income Trend
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Actual collected income for each month (Last 6 months)
              </p>
            </div>
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300">
              Monthly Growth
            </span>
          </div>

          <div className="h-64 mt-4">
            {has_monthly_income_data ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={monthly_income_trend}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                  <XAxis dataKey="month" stroke={textStroke} fontSize={11} />
                  <YAxis stroke={textStroke} fontSize={10} />
                  <Tooltip
                    formatter={(val, name) => [formatMoney(val), name === 'income' ? 'Collected Income' : 'Total Invoiced']}
                    contentStyle={tooltipStyle}
                  />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Bar dataKey="income" name="Collected Income" fill="#6366f1" radius={[5, 5, 0, 0]} />
                  <Bar dataKey="invoiced" name="Total Invoiced" fill="#cbd5e1" radius={[5, 5, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center space-y-2">
                <BarChart3 className="w-8 h-8 text-slate-400" />
                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">₹0</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No income recorded for this period.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 6. ROW 4: PAYMENT STATUS & AI BUSINESS INSIGHT */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Payment Status Breakdown */}
        <div className="lg:col-span-5 p-5 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white pb-3 border-b border-slate-200 dark:border-[#26262c]">
              Payment Status Distribution
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2">
              Invoice payment health based on database records.
            </p>

            <div className="grid grid-cols-2 gap-3 mt-4">
              <div className="p-3 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-500/20">
                <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Paid</span>
                <p className="text-xl font-bold text-emerald-700 dark:text-emerald-300 mt-0.5">
                  {payment_status_distribution.paid || 0}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/20 border border-indigo-100 dark:border-indigo-500/20">
                <span className="text-[10px] font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">Partially Paid</span>
                <p className="text-xl font-bold text-indigo-700 dark:text-indigo-300 mt-0.5">
                  {payment_status_distribution.partially_paid || 0}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-amber-50/60 dark:bg-amber-950/20 border border-amber-100 dark:border-amber-500/20">
                <span className="text-[10px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider">Unpaid</span>
                <p className="text-xl font-bold text-amber-700 dark:text-amber-300 mt-0.5">
                  {payment_status_distribution.unpaid || 0}
                </p>
              </div>

              <div className="p-3 rounded-xl bg-rose-50/60 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-500/20">
                <span className="text-[10px] font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider">Overdue</span>
                <p className="text-xl font-bold text-rose-700 dark:text-rose-300 mt-0.5">
                  {payment_status_distribution.overdue || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-100 dark:border-[#26262c] text-[11px] text-slate-400">
            Total active invoices: {Object.values(payment_status_distribution).reduce((a, b) => a + b, 0)}
          </div>
        </div>

        {/* AI Business Insight */}
        <div className="lg:col-span-7 p-5 sm:p-6 rounded-2xl bg-linear-to-br from-indigo-50/40 to-purple-50/20 dark:from-[#181822] dark:to-[#14141a] border border-indigo-200/80 dark:border-indigo-500/30 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-indigo-100 dark:border-[#282834]">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-indigo-600 text-white shadow-xs">
                  <Sparkles className="w-4 h-4" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  AI Business Insight
                </h3>
              </div>
              <Badge variant="ai">Gemini AI Synthesis</Badge>
            </div>

            <div className="mt-4 p-4 rounded-xl bg-white/80 dark:bg-[#141417]/80 border border-slate-200/70 dark:border-[#26262c] shadow-2xs">
              <p className="text-xs sm:text-sm font-medium text-slate-800 dark:text-slate-200 leading-relaxed whitespace-pre-line">
                "{ai_business_insight}"
              </p>
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-indigo-100/70 dark:border-[#282834] flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
              Grounded strictly in verified database ledgers
            </span>
            <span className="font-mono text-[10px] text-indigo-600 dark:text-indigo-400 font-semibold">
              OpsNova AI
            </span>
          </div>
        </div>
      </div>

      {/* 7. ROW 5: REPORTS & EXPORT SECTION */}
      <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] shadow-xs space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-[#26262c]">
          <div>
            <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
              Financial & Operations Reports
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Detailed payment breakdown, aging status, and customer receivables.
            </p>
          </div>

          {/* Export Actions */}
          <div className="flex items-center gap-2">
            <Button
              onClick={handleExportCSV}
              variant="secondary"
              size="sm"
              loading={exporting}
              icon={Download}
              className="text-xs font-semibold"
            >
              Export CSV
            </Button>
            <Button
              onClick={handleExportExcel}
              variant="secondary"
              size="sm"
              loading={exporting}
              icon={FileSpreadsheet}
              className="text-xs font-semibold"
            >
              Export Excel
            </Button>
            <Button
              onClick={handleExportPDF}
              variant="secondary"
              size="sm"
              icon={Printer}
              className="text-xs font-semibold"
            >
              Print / PDF
            </Button>
          </div>
        </div>

        {/* Report Tab Selector */}
        <div className="flex border-b border-slate-200 dark:border-[#26262c] gap-4 overflow-x-auto text-xs font-bold">
          <button
            type="button"
            onClick={() => setActiveReportTab('daily_income')}
            className={`pb-2.5 transition-colors cursor-pointer border-b-2 ${
              activeReportTab === 'daily_income'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Daily Income Report ({reports.daily_income.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveReportTab('monthly_income')}
            className={`pb-2.5 transition-colors cursor-pointer border-b-2 ${
              activeReportTab === 'monthly_income'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Monthly Income Report ({reports.monthly_income.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveReportTab('outstanding')}
            className={`pb-2.5 transition-colors cursor-pointer border-b-2 ${
              activeReportTab === 'outstanding'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Outstanding Report ({reports.outstanding.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveReportTab('overdue')}
            className={`pb-2.5 transition-colors cursor-pointer border-b-2 ${
              activeReportTab === 'overdue'
                ? 'border-indigo-600 text-indigo-600 dark:text-indigo-400'
                : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
            }`}
          >
            Overdue Report ({reports.overdue.length})
          </button>
        </div>

        {/* Tab 1: Daily Income Report Table */}
        {activeReportTab === 'daily_income' && (
          <div className="overflow-x-auto">
            {reports.daily_income.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-[#26262c] text-slate-400 uppercase text-[10px] font-bold">
                    <th className="py-2.5 px-3">Invoice #</th>
                    <th className="py-2.5 px-3">Customer</th>
                    <th className="py-2.5 px-3 text-right">Invoice Total</th>
                    <th className="py-2.5 px-3 text-right">Paid Amount</th>
                    <th className="py-2.5 px-3">Payment Date</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-[#202026]">
                  {reports.daily_income.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-[#18181f] transition-colors">
                      <td className="py-3 px-3 font-bold text-slate-900 dark:text-white">{item.invoice_number}</td>
                      <td className="py-3 px-3 text-slate-700 dark:text-slate-300">{item.customer_name}</td>
                      <td className="py-3 px-3 text-right font-medium text-slate-500">{formatMoney(item.total_amount)}</td>
                      <td className="py-3 px-3 text-right font-bold text-emerald-600 dark:text-emerald-400">
                        {formatMoney(item.paid_amount)}
                      </td>
                      <td className="py-3 px-3 text-slate-500">{item.payment_date}</td>
                      <td className="py-3 px-3 text-center">
                        <Badge variant={item.status === 'paid' ? 'success' : 'info'}>{item.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="py-12 text-center space-y-1">
                <p className="text-base font-bold text-slate-800 dark:text-slate-200">₹0</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No income recorded for this period ({incomeData.selected_date_formatted}).
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Monthly Income Report Table */}
        {activeReportTab === 'monthly_income' && (
          <div className="overflow-x-auto">
            {reports.monthly_income.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-[#26262c] text-slate-400 uppercase text-[10px] font-bold">
                    <th className="py-2.5 px-3">Invoice #</th>
                    <th className="py-2.5 px-3">Customer</th>
                    <th className="py-2.5 px-3 text-right">Invoice Total</th>
                    <th className="py-2.5 px-3 text-right">Collected Amount</th>
                    <th className="py-2.5 px-3">Payment Date</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-[#202026]">
                  {reports.monthly_income.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-[#18181f] transition-colors">
                      <td className="py-3 px-3 font-bold text-slate-900 dark:text-white">{item.invoice_number}</td>
                      <td className="py-3 px-3 text-slate-700 dark:text-slate-300">{item.customer_name}</td>
                      <td className="py-3 px-3 text-right font-medium text-slate-500">{formatMoney(item.total_amount)}</td>
                      <td className="py-3 px-3 text-right font-bold text-indigo-600 dark:text-indigo-400">
                        {formatMoney(item.paid_amount)}
                      </td>
                      <td className="py-3 px-3 text-slate-500">{item.payment_date}</td>
                      <td className="py-3 px-3 text-center">
                        <Badge variant={item.status === 'paid' ? 'success' : 'info'}>{item.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="py-12 text-center space-y-1">
                <p className="text-base font-bold text-slate-800 dark:text-slate-200">₹0</p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  No income recorded for this period ({incomeData.selected_month_formatted}).
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Outstanding Report Table */}
        {activeReportTab === 'outstanding' && (
          <div className="overflow-x-auto">
            {reports.outstanding.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-[#26262c] text-slate-400 uppercase text-[10px] font-bold">
                    <th className="py-2.5 px-3">Customer</th>
                    <th className="py-2.5 px-3">Invoice #</th>
                    <th className="py-2.5 px-3 text-right">Total</th>
                    <th className="py-2.5 px-3 text-right">Paid</th>
                    <th className="py-2.5 px-3 text-right">Pending Balance</th>
                    <th className="py-2.5 px-3">Due Date</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-[#202026]">
                  {reports.outstanding.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-[#18181f] transition-colors">
                      <td className="py-3 px-3 font-semibold text-slate-900 dark:text-white">{item.customer}</td>
                      <td className="py-3 px-3 font-mono text-slate-700 dark:text-slate-300">{item.invoice}</td>
                      <td className="py-3 px-3 text-right font-medium text-slate-500">{formatMoney(item.total)}</td>
                      <td className="py-3 px-3 text-right text-slate-600 dark:text-slate-400">{formatMoney(item.paid)}</td>
                      <td className="py-3 px-3 text-right font-bold text-amber-600 dark:text-amber-400">
                        {formatMoney(item.pending)}
                      </td>
                      <td className="py-3 px-3 text-slate-500">{item.due_date}</td>
                      <td className="py-3 px-3 text-center">
                        <Badge variant={item.status === 'overdue' ? 'urgent' : (item.status === 'partially_paid' ? 'info' : 'warning')}>
                          {item.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="py-12 text-center text-xs text-slate-500">
                No outstanding invoices found. All client ledgers settled!
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Overdue Report Table */}
        {activeReportTab === 'overdue' && (
          <div className="overflow-x-auto">
            {reports.overdue.length > 0 ? (
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-[#26262c] text-slate-400 uppercase text-[10px] font-bold">
                    <th className="py-2.5 px-3">Customer</th>
                    <th className="py-2.5 px-3">Invoice #</th>
                    <th className="py-2.5 px-3 text-right">Pending Amount</th>
                    <th className="py-2.5 px-3">Due Date</th>
                    <th className="py-2.5 px-3 text-center">Days Overdue</th>
                    <th className="py-2.5 px-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-[#202026]">
                  {reports.overdue.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-[#18181f] transition-colors">
                      <td className="py-3 px-3 font-semibold text-slate-900 dark:text-white">{item.customer}</td>
                      <td className="py-3 px-3 font-mono text-slate-700 dark:text-slate-300">{item.invoice}</td>
                      <td className="py-3 px-3 text-right font-bold text-rose-600 dark:text-rose-400">
                        {formatMoney(item.pending_amount)}
                      </td>
                      <td className="py-3 px-3 text-slate-500">{item.due_date}</td>
                      <td className="py-3 px-3 text-center">
                        <span className="px-2 py-0.5 rounded font-bold text-[11px] bg-rose-50 text-rose-700 dark:bg-rose-950/30 dark:text-rose-300">
                          +{item.days_overdue} days
                        </span>
                      </td>
                      <td className="py-3 px-3 text-center">
                        <Badge variant="urgent">Overdue</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="py-12 text-center text-xs text-slate-500">
                No past-due invoices found. Operations are on track!
              </div>
            )}
          </div>
        )}
      </div>

      {/* 8. Secondary Intelligence Collapsible: What-If Simulator & Root Cause Diagnostic */}
      <div className="rounded-2xl border border-slate-200 dark:border-[#26262c] bg-white dark:bg-[#141417] shadow-xs overflow-hidden">
        <button
          type="button"
          onClick={() => {
            setShowIntelligenceTools(!showIntelligenceTools);
            if (!showIntelligenceTools) loadIntelligenceData();
          }}
          className="w-full px-5 py-3.5 flex items-center justify-between text-left text-xs font-bold text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-[#18181d] transition-colors cursor-pointer"
        >
          <div className="flex items-center gap-2">
            <Sliders className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
            <span>Advanced Predictive Tools (What-If Simulator & Root Cause Diagnostics)</span>
          </div>
          <span className="text-[11px] text-indigo-600 dark:text-indigo-400">
            {showIntelligenceTools ? 'Hide Tools ▲' : 'Show Tools ▼'}
          </span>
        </button>

        {showIntelligenceTools && (
          <div className="p-5 border-t border-slate-200 dark:border-[#26262c] space-y-6">
            {/* Root Cause Diagnostics */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#18181d] border border-slate-200 dark:border-[#26262c] space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <HelpCircle className="w-4 h-4 text-indigo-600" />
                    AI Root Cause Analysis
                  </h4>
                  <p className="text-[11px] text-slate-500">Diagnose payment latency across customer segments</p>
                </div>
                <Button
                  onClick={handleRunRCA}
                  variant="primary"
                  size="sm"
                  loading={rcaLoading}
                  icon={Sparkles}
                  className="text-xs font-bold"
                >
                  Run Diagnostic
                </Button>
              </div>

              {rcaData && (
                <div className="space-y-3 text-xs pt-2">
                  <div className="p-3 rounded-lg bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c]">
                    <span className="font-bold text-indigo-600 dark:text-indigo-400">Primary Finding: </span>
                    <span className="text-slate-700 dark:text-slate-300">{rcaData.primary_finding}</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                    {rcaData.key_factors.map((f, i) => (
                      <div key={i} className="p-2.5 rounded-lg bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c]">
                        <p className="font-bold text-slate-800 dark:text-slate-200">{f.factor}</p>
                        <p className="text-[11px] text-slate-500 mt-1">{f.data_evidence}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* What-If Simulator */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-[#18181d] border border-slate-200 dark:border-[#26262c] space-y-3">
              <h4 className="text-xs font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                <Sliders className="w-4 h-4 text-indigo-600" />
                What-If Business Operations Simulator
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-300 mb-1">Scenario</label>
                  <select
                    value={simScenario}
                    onChange={(e) => setSimScenario(e.target.value)}
                    className="w-full bg-white dark:bg-[#141417] border border-slate-300 dark:border-[#2e2e36] rounded-lg px-2.5 py-1.5 text-xs"
                  >
                    <option value="early_discount">5% Early Settlement Discount</option>
                    <option value="reminder_blitz">+25% AI Reminder Blitz</option>
                    <option value="payment_delay">+30 Days Payment Delay</option>
                  </select>
                </div>
                <div className="flex items-end">
                  <Button
                    onClick={handleRunSimulation}
                    variant="primary"
                    size="sm"
                    loading={simLoading}
                    icon={Play}
                    className="w-full text-xs font-bold py-2"
                  >
                    Compute Simulation
                  </Button>
                </div>
              </div>

              {simResult && (
                <div className="p-3.5 rounded-lg bg-white dark:bg-[#141417] border border-slate-200 dark:border-[#26262c] text-xs space-y-2 mt-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-900 dark:text-white">{simResult.scenario_title}</span>
                    <Badge variant={simResult.net_variance >= 0 ? 'success' : 'urgent'}>{simResult.impact_percentage}</Badge>
                  </div>
                  <p className="text-[11px] text-slate-600 dark:text-slate-400 whitespace-pre-line">
                    {simResult.detailed_projection_markdown}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalyticsPage;
