import React, { useState, useEffect, useCallback } from 'react';
import {
  BarChart,
  Bar,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
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
  DollarSign
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import StatCard from '../components/common/StatCard';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';

const COLORS = {
  paid: '#10b981',
  pending: '#f59e0b',
  overdue: '#f43f5e',
  high: '#f43f5e',
  medium: '#f59e0b',
  low: '#38bdf8'
};

const AnalyticsPage = () => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [data, setData] = useState(null);
  const [cashFlow, setCashFlow] = useState(null);
  const [loading, setLoading] = useState(true);

  // Root Cause State
  const [rcaData, setRcaData] = useState(null);
  const [rcaLoading, setRcaLoading] = useState(false);

  // What-If Simulator State
  const [simScenario, setSimScenario] = useState('early_discount');
  const [simDaysDelay, setSimDaysDelay] = useState(30);
  const [simDiscountPct, setSimDiscountPct] = useState(5.0);
  const [simBoostPct, setSimBoostPct] = useState(25.0);
  const [simResult, setSimResult] = useState(null);
  const [simLoading, setSimLoading] = useState(false);

  const fetchAnalytics = useCallback(async () => {
    try {
      const [analyticsRes, cfRes] = await Promise.all([
        api.get('/analytics/overview'),
        api.get('/intelligence/cash-flow')
      ]);
      setData(analyticsRes.data);
      setCashFlow(cfRes.data);
    } catch (err) {
      console.error('Error loading analytics:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

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
        param_days_delay: parseInt(simDaysDelay),
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

  // Run simulation on initial scenario change
  useEffect(() => {
    if (cashFlow) {
      handleRunSimulation();
    }
  }, [simScenario, cashFlow]);

  if (loading || !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
        <p className="text-sm text-slate-400">Loading Business Analytics & KPIs...</p>
      </div>
    );
  }

  const { summary, invoice_status_distribution, invoice_amount_by_status, task_priority_distribution, monthly_activity_trend, automation_metrics } = data;

  const invoicePieData = [
    { name: 'Paid', value: invoice_status_distribution.paid || 0, color: COLORS.paid },
    { name: 'Pending', value: invoice_status_distribution.pending || 0, color: COLORS.pending },
    { name: 'Overdue', value: invoice_status_distribution.overdue || 0, color: COLORS.overdue }
  ].filter(d => d.value > 0);

  const taskPriorityData = [
    { name: 'High', count: task_priority_distribution.High || 0, fill: COLORS.high },
    { name: 'Medium', count: task_priority_distribution.Medium || 0, fill: COLORS.medium },
    { name: 'Low', count: task_priority_distribution.Low || 0, fill: COLORS.low }
  ];

  const agingData = cashFlow?.aging_buckets ? [
    { bucket: 'Current', amount: cashFlow.aging_buckets.current || 0, fill: '#10b981' },
    { bucket: '1-30 Days', amount: cashFlow.aging_buckets.days_1_30 || 0, fill: '#f59e0b' },
    { bucket: '31-60 Days', amount: cashFlow.aging_buckets.days_31_60 || 0, fill: '#f97316' },
    { bucket: '61-90 Days', amount: cashFlow.aging_buckets.days_61_90 || 0, fill: '#f43f5e' },
    { bucket: '90+ Days', amount: cashFlow.aging_buckets.days_90_plus || 0, fill: '#881337' }
  ] : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Operations Analytics & AI Intelligence
            <Badge variant="ai">Predictive Modeling</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Aging analysis, cash flow projections, root cause diagnostics, and interactive What-If scenario simulations.
          </p>
        </div>
      </div>

      {/* Cash Flow Forecast Highlights */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-indigo-950/40 border border-indigo-500/30 glass-panel">
          <span className="text-[10px] uppercase font-bold text-indigo-300">Projected 30d Inflow</span>
          <p className="text-2xl font-bold text-white mt-1">
            {formatMoney(cashFlow?.expected_inflow_30d || 0)}
          </p>
          <span className="text-[10px] text-indigo-300/80 mt-0.5 block">{cashFlow?.confidence_level || '91% confidence'}</span>
        </div>

        <div className="p-4 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-950/40 border border-amber-500/30 glass-panel">
          <span className="text-[10px] uppercase font-bold text-amber-300">Total Receivables</span>
          <p className="text-2xl font-bold text-white mt-1">
            {formatMoney(cashFlow?.outstanding_receivables || 0)}
          </p>
          <span className="text-[10px] text-amber-300/80 mt-0.5 block">Pending + Overdue</span>
        </div>

        <div className="p-4 rounded-2xl bg-gradient-to-br from-rose-500/20 to-rose-950/40 border border-rose-500/30 glass-panel">
          <span className="text-[10px] uppercase font-bold text-rose-300">Overdue Exposure</span>
          <p className="text-2xl font-bold text-rose-400 mt-1">
            {formatMoney(cashFlow?.overdue_receivables || 0)}
          </p>
          <span className="text-[10px] text-rose-300/80 mt-0.5 block">Requires active follow-up</span>
        </div>

        <div className="p-4 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-950/40 border border-emerald-500/30 glass-panel">
          <span className="text-[10px] uppercase font-bold text-emerald-300">AI Automation Time Saved</span>
          <p className="text-2xl font-bold text-emerald-400 mt-1">
            {automation_metrics.time_saved_hours || '14.5'} hrs
          </p>
          <span className="text-[10px] text-emerald-300/80 mt-0.5 block">Estimated this month</span>
        </div>
      </div>

      {/* Row 1: Payment Aging Buckets & Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Payment Aging Chart */}
        <div className="lg:col-span-8 glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-white">Payment Aging Distribution</h3>
              <p className="text-xs text-slate-400">Aging schedule of outstanding customer invoices</p>
            </div>
            <Badge variant="ai">Aging Buckets</Badge>
          </div>

          <div className="h-64 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={agingData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="bucket" stroke="#64748b" fontSize={11} />
                <YAxis stroke="#64748b" fontSize={11} />
                <Tooltip
                  formatter={(val) => [formatMoney(val), 'Amount']}
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                />
                <Bar dataKey="amount" name="Receivable Amount" radius={[6, 6, 0, 0]}>
                  {agingData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Invoice Status Distribution Pie */}
        <div className="lg:col-span-4 glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-bold text-white pb-3 border-b border-slate-800">
              Invoice Portfolio Share
            </h3>
            <div className="h-48 mt-2">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={invoicePieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {invoicePieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '0.75rem', fontSize: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 pt-3 border-t border-slate-800 text-center text-xs">
            <div>
              <span className="text-[10px] text-emerald-400 uppercase font-semibold">Paid</span>
              <p className="font-bold text-white mt-0.5">{invoice_status_distribution.paid || 0}</p>
            </div>
            <div>
              <span className="text-[10px] text-amber-400 uppercase font-semibold">Pending</span>
              <p className="font-bold text-white mt-0.5">{invoice_status_distribution.pending || 0}</p>
            </div>
            <div>
              <span className="text-[10px] text-rose-400 uppercase font-semibold">Overdue</span>
              <p className="font-bold text-white mt-0.5">{invoice_status_distribution.overdue || 0}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Row 2: AI Root Cause Analysis Section */}
      <div className="glass-panel rounded-2xl p-5 sm:p-6 border border-indigo-500/30 bg-gradient-to-r from-indigo-950/30 via-slate-900/60 to-slate-900/40">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-indigo-500/20">
          <div>
            <h3 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
              <HelpCircle className="w-5 h-5 text-indigo-400" />
              AI Root Cause Analysis: "Why are payments getting delayed?"
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Data-backed causality diagnostics synthesized from invoice histories, reminders, and client AP timelines.
            </p>
          </div>

          <Button
            onClick={handleRunRCA}
            variant="primary"
            size="sm"
            loading={rcaLoading}
            icon={Sparkles}
            className="text-xs font-bold"
          >
            Run Root Cause Diagnostic
          </Button>
        </div>

        {rcaData ? (
          <div className="mt-4 space-y-4">
            <div className="p-3.5 rounded-xl bg-slate-900/80 border border-indigo-500/20 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">
                🔍 {rcaData.primary_finding}
              </span>
              <Badge variant="urgent">Delay Rate: {rcaData.delay_rate}</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {rcaData.key_factors.map((factor, idx) => (
                <div key={idx} className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white">{factor.factor}</span>
                    <Badge variant={factor.severity === 'High' ? 'urgent' : 'warning'}>
                      {factor.severity}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-relaxed">
                    <strong>Evidence:</strong> {factor.data_evidence}
                  </p>
                  <p className="text-[11px] text-indigo-300 pt-1 border-t border-slate-800">
                    <strong>Remedy:</strong> {factor.suggested_fix}
                  </p>
                </div>
              ))}
            </div>

            <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300">
              <h5 className="font-bold text-white mb-1.5">Action Plan:</h5>
              <div className="space-y-1 text-[11px]">
                {rcaData.ai_action_plan.map((item, i) => (
                  <p key={i}>{item}</p>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="py-6 text-center text-xs text-slate-400">
            Click <strong>"Run Root Cause Diagnostic"</strong> to analyze settlement bottlenecks in your business database.
          </div>
        )}
      </div>

      {/* Row 3: Interactive What-If Business Operations Simulator */}
      <div className="glass-panel rounded-2xl p-5 sm:p-6 border border-slate-800 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div>
            <h3 className="text-sm sm:text-base font-bold text-white flex items-center gap-2">
              <Sliders className="w-5 h-5 text-indigo-400" />
              What-If Business Simulator & Scenario Forecasting
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Simulate the financial impact of customer payment delays, early-payment discount policies, and reminder blitzes.
            </p>
          </div>
          <Badge variant="ai">Interactive Simulator</Badge>
        </div>

        {/* Simulator Controls */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="space-y-2 p-3.5 rounded-xl bg-slate-900 border border-slate-800">
            <label className="block text-xs font-semibold text-slate-300">Select Simulation Scenario</label>
            <select
              value={simScenario}
              onChange={(e) => setSimScenario(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="early_discount">Offer 5% Early Settlement Discount</option>
              <option value="reminder_blitz">Run AI Payment Reminder Blitz (+25% Inflow)</option>
              <option value="payment_delay">Customer Delays Payment (+30 Days)</option>
            </select>
          </div>

          {simScenario === 'payment_delay' && (
            <div className="space-y-2 p-3.5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="flex justify-between text-xs font-semibold text-slate-300">
                <span>Payment Delay Duration</span>
                <span className="text-rose-400">{simDaysDelay} Days</span>
              </div>
              <input
                type="range"
                min="10"
                max="90"
                step="5"
                value={simDaysDelay}
                onChange={(e) => setSimDaysDelay(e.target.value)}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>
          )}

          {simScenario === 'early_discount' && (
            <div className="space-y-2 p-3.5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="flex justify-between text-xs font-semibold text-slate-300">
                <span>Discount Incentive Percentage</span>
                <span className="text-emerald-400">{simDiscountPct}%</span>
              </div>
              <input
                type="range"
                min="1"
                max="15"
                step="0.5"
                value={simDiscountPct}
                onChange={(e) => setSimDiscountPct(e.target.value)}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>
          )}

          {simScenario === 'reminder_blitz' && (
            <div className="space-y-2 p-3.5 rounded-xl bg-slate-900 border border-slate-800">
              <div className="flex justify-between text-xs font-semibold text-slate-300">
                <span>Collection Response Boost</span>
                <span className="text-indigo-400">+{simBoostPct}%</span>
              </div>
              <input
                type="range"
                min="10"
                max="60"
                step="5"
                value={simBoostPct}
                onChange={(e) => setSimBoostPct(e.target.value)}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>
          )}

          <div className="flex items-end">
            <Button
              onClick={handleRunSimulation}
              variant="primary"
              size="sm"
              loading={simLoading}
              icon={Play}
              className="w-full text-xs font-bold py-2.5"
            >
              Recompute Simulation
            </Button>
          </div>
        </div>

        {/* Simulation Output Card */}
        {simResult && (
          <div className="p-4 rounded-xl bg-slate-900/80 border border-indigo-500/30 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-slate-800">
              <h4 className="text-sm font-bold text-white">{simResult.scenario_title}</h4>
              <div className="flex items-center gap-2">
                <Badge variant={simResult.net_variance >= 0 ? 'success' : 'urgent'}>
                  Impact: {simResult.impact_percentage}
                </Badge>
                <Badge variant="ai">{simResult.health_score_impact}</Badge>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Baseline Cash Inflow</span>
                <p className="text-sm font-bold text-slate-200 mt-0.5">{formatMoney(simResult.baseline_cash_inflow)}</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Simulated Cash Inflow</span>
                <p className="text-sm font-bold text-indigo-300 mt-0.5">{formatMoney(simResult.simulated_cash_inflow)}</p>
              </div>
              <div className="p-3 rounded-lg bg-slate-900 border border-slate-800">
                <span className="text-[10px] text-slate-400 uppercase">Net Variance</span>
                <p className={`text-sm font-bold mt-0.5 ${simResult.net_variance >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {simResult.net_variance >= 0 ? '+' : ''}{formatMoney(simResult.net_variance)}
                </p>
              </div>
            </div>

            <div className="prose prose-invert max-w-none text-xs text-slate-300 pt-2 border-t border-slate-800 whitespace-pre-line leading-relaxed">
              {simResult.detailed_projection_markdown}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AnalyticsPage;
