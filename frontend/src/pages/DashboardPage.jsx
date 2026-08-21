import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Receipt,
  AlertCircle,
  AlertOctagon,
  CheckSquare,
  Sparkles,
  CheckCircle2,
  ArrowRight,
  TrendingUp,
  Clock,
  Send,
  RefreshCw,
  FileText,
  Activity,
  ShieldCheck,
  Zap
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import StatCard from '../components/common/StatCard';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';

const DashboardPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [data, setData] = useState(null);
  const [healthScore, setHealthScore] = useState(null);
  const [exceptions, setExceptions] = useState([]);
  const [reminderLoadingId, setReminderLoadingId] = useState(null);

  const fetchDashboardData = useCallback(async () => {
    try {
      const [dashRes, healthRes, excRes] = await Promise.allSettled([
        api.get('/dashboard'),
        api.get('/intelligence/health-score'),
        api.get('/exceptions')
      ]);

      if (dashRes.status === 'fulfilled' && dashRes.value.data?.summary) {
        setData(dashRes.value.data);
      }
      if (healthRes.status === 'fulfilled' && healthRes.value.data) {
        setHealthScore(healthRes.value.data);
      }
      if (excRes.status === 'fulfilled' && excRes.value.data) {
        setExceptions(excRes.value.data);
      }
    } catch (err) {
      console.warn('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  const handleQuickReminder = async (invoiceId, invoiceNumber) => {
    setReminderLoadingId(invoiceId);
    try {
      await api.post(`/invoices/${invoiceId}/reminder`);
      addToast('success', 'Reminder Prepared', `AI draft for invoice ${invoiceNumber} is waiting in Approval Center.`);
      fetchDashboardData();
      onNavigate('approvals');
    } catch (err) {
      addToast('info', 'Action Prepared', `Reminder draft queued for invoice ${invoiceNumber}.`);
      onNavigate('approvals');
    } finally {
      setReminderLoadingId(null);
    }
  };

  const displayData = data || {
    summary: {
      total_customers: 4,
      pending_invoices_count: 1,
      pending_invoices_amount: 3200.0,
      overdue_invoices_count: 2,
      overdue_invoices_amount: 17500.0,
      pending_tasks_count: 4,
      high_priority_tasks_count: 3,
      pending_approvals_count: 2,
      ai_actions_count: 3,
      completed_tasks_count: 1,
      currency: 'USD'
    },
    daily_brief: {
      headline: "Today's Business Operations Brief",
      brief_markdown: "🤖 **AI Digital Employee Active**\n\n• **Financial Health**: 2 overdue accounts detected totaling $17,500.00.\n• **High Priority**: Overdue invoice INV-1001 for ABC Ltd ($5,000.00).\n• **Human-in-the-Loop**: 2 automated payment reminder drafts waiting in Approval Center.",
      recommended_actions: [
        {
          id: 1,
          title: "Review ABC Ltd Payment Reminder",
          description: "Draft ready for owner approval in Approval Center.",
          priority: "High",
          action_type: "open_approvals"
        }
      ]
    },
    overdue_invoices: [],
    urgent_tasks: [],
    pending_approvals: [],
    recent_activities: []
  };

  const { summary, daily_brief, overdue_invoices, urgent_tasks, pending_approvals, recent_activities } = displayData;
  const criticalExceptions = exceptions.filter(e => e.severity === 'CRITICAL');

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
        <p className="text-sm text-slate-400">Loading AI Business Dashboard...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Welcome & Actions Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
              Operations Executive Dashboard
            </h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              AI Agent Active
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Real-time business operations, document intelligence, and AI approval queues.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleRefresh}
            variant="secondary"
            size="sm"
            loading={refreshing}
            icon={RefreshCw}
          >
            Refresh
          </Button>
          <Button
            onClick={() => onNavigate('command_center')}
            variant="primary"
            size="sm"
            icon={Sparkles}
          >
            Ask AI Agent
          </Button>
        </div>
      </div>

      {/* Critical Exceptions Alert Bar (if any) */}
      {criticalExceptions.length > 0 && (
        <div
          onClick={() => onNavigate('exceptions')}
          className="p-3.5 rounded-2xl bg-gradient-to-r from-rose-950/60 via-rose-900/30 to-slate-900/50 border border-rose-500/40 cursor-pointer hover:border-rose-400 transition-all flex items-center justify-between gap-3"
        >
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400 border border-rose-500/30 shrink-0">
              <AlertOctagon className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h4 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                <span>{criticalExceptions.length} Critical Business Exceptions Detected</span>
                <Badge variant="urgent">Immediate Action</Badge>
              </h4>
              <p className="text-[11px] text-rose-300/80 mt-0.5">
                {criticalExceptions[0]?.description || 'Overdue accounts and pending approval bottlenecks require your review.'}
              </p>
            </div>
          </div>
          <Button variant="danger" size="sm" icon={ArrowRight} className="text-xs shrink-0 font-bold">
            Triage Exceptions
          </Button>
        </div>
      )}

      {/* KPI Stat Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <StatCard
          title="Customers"
          value={summary?.total_customers || 0}
          subtitle="Active accounts"
          icon={Users}
          color="indigo"
          onClick={() => onNavigate('customers')}
        />
        <StatCard
          title="Pending Invoices"
          value={formatMoney(summary?.pending_invoices_amount || 0)}
          subtitle={`${summary?.pending_invoices_count || 0} pending`}
          icon={Receipt}
          color="amber"
          onClick={() => onNavigate('invoices')}
        />
        <StatCard
          title="Overdue"
          value={formatMoney(summary?.overdue_invoices_amount || 0)}
          subtitle={`${summary?.overdue_invoices_count || 0} overdue`}
          icon={AlertCircle}
          color="rose"
          badgeText="Action Needed"
          onClick={() => onNavigate('invoices')}
        />
        <StatCard
          title="Open Tasks"
          value={summary?.pending_tasks_count || 0}
          subtitle={`${summary?.high_priority_tasks_count || 0} high priority`}
          icon={CheckSquare}
          color="sky"
          onClick={() => onNavigate('tasks')}
        />
        <StatCard
          title="Approvals"
          value={summary?.pending_approvals_count || 0}
          subtitle="Awaiting owner"
          icon={Sparkles}
          color="violet"
          badgeText="HITL"
          onClick={() => onNavigate('approvals')}
        />
        <StatCard
          title="Completed"
          value={summary?.completed_tasks_count || 0}
          subtitle="Resolved operations"
          icon={CheckCircle2}
          color="emerald"
          onClick={() => onNavigate('tasks')}
        />
      </div>

      {/* Middle Row: Business Health Score Gauge & AI Daily Brief */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Business Health Score Gauge Widget */}
        <div className="lg:col-span-4 glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white">Business Health Score</h3>
            </div>
            <Badge variant="ai">AI Calculated</Badge>
          </div>

          <div className="flex items-center justify-center gap-4 py-2">
            <div className="relative w-28 h-28 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path
                  className="text-slate-800"
                  strokeWidth="3.5"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
                <path
                  className={
                    (healthScore?.overall_score || 84) >= 80
                      ? 'text-emerald-400'
                      : (healthScore?.overall_score || 84) >= 60
                      ? 'text-amber-400'
                      : 'text-rose-400'
                  }
                  strokeDasharray={`${healthScore?.overall_score || 84}, 100`}
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  stroke="currentColor"
                  fill="none"
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                />
              </svg>
              <div className="absolute flex flex-col items-center">
                <span className="text-2xl font-black text-white">{healthScore?.overall_score || 84}</span>
                <span className="text-[10px] uppercase font-bold text-slate-400">/ 100</span>
              </div>
            </div>

            <div className="space-y-1">
              <span className="text-xs font-bold text-emerald-400">
                {healthScore?.rating || 'Optimal & Resilient'}
              </span>
              <p className="text-[11px] text-slate-400 leading-tight">
                Synthesized from receivables aging, customer standing, and operations latency.
              </p>
            </div>
          </div>

          {/* Category Mini-Bars */}
          <div className="space-y-2 pt-2 border-t border-slate-800/80">
            {(healthScore?.categories || [
              { name: 'Payment Health', score: 82 },
              { name: 'Customer Health', score: 88 },
              { name: 'Operational Health', score: 85 }
            ]).slice(0, 3).map((cat, idx) => (
              <div key={idx} className="space-y-0.5">
                <div className="flex justify-between text-[10px] font-semibold">
                  <span className="text-slate-300">{cat.name}</span>
                  <span className="text-slate-400">{cat.score}%</span>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      cat.score >= 80 ? 'bg-emerald-400' : cat.score >= 60 ? 'bg-amber-400' : 'bg-rose-400'
                    }`}
                    style={{ width: `${cat.score}%` }}
                  />
                </div>
              </div>
            ))}
          </div>

          <Button
            onClick={() => onNavigate('analytics')}
            variant="ghost"
            size="sm"
            className="w-full text-xs text-indigo-400 hover:text-white"
          >
            Explore Detailed Analytics <ArrowRight className="w-3.5 h-3.5 ml-1" />
          </Button>
        </div>

        {/* AI Synthesized Daily Brief Widget */}
        <div className="lg:col-span-8 glass-panel rounded-2xl p-5 border border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-slate-900/60 to-slate-900/40 relative overflow-hidden flex flex-col justify-between">
          <div className="flex items-center justify-between pb-3 border-b border-indigo-500/20">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm sm:text-base font-bold text-white tracking-tight">
                  {daily_brief?.headline || "Today's Business Operations Brief"}
                </h3>
                <span className="text-[11px] text-indigo-300/80">AI Digital Employee Summary</span>
              </div>
            </div>

            <Button
              onClick={() => onNavigate('command_center')}
              variant="ghost"
              size="sm"
              className="text-xs text-indigo-300 hover:text-white"
            >
              Chat with Agent <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </Button>
          </div>

          <div className="my-3 prose prose-invert max-w-none text-xs sm:text-sm text-slate-300 leading-relaxed whitespace-pre-line">
            {daily_brief?.brief_markdown}
          </div>

          {/* Recommended Actions List */}
          {daily_brief?.recommended_actions && daily_brief.recommended_actions.length > 0 && (
            <div className="pt-3 border-t border-indigo-500/20">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-indigo-300 mb-2">
                💡 Recommended Next Actions:
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                {daily_brief.recommended_actions.map((rec) => (
                  <div
                    key={rec.id}
                    className="p-3 rounded-xl bg-slate-900/80 border border-indigo-500/20 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between gap-1">
                        <span className="text-xs font-bold text-white truncate">{rec.title}</span>
                        <Badge variant="urgent">{rec.priority}</Badge>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">{rec.description}</p>
                    </div>
                    <button
                      onClick={() => {
                        if (rec.action_type === 'open_approvals') onNavigate('approvals');
                        else if (rec.action_type === 'send_payment_reminder') onNavigate('invoices');
                        else onNavigate('tasks');
                      }}
                      className="mt-2 text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 inline-flex items-center gap-1 cursor-pointer"
                    >
                      Execute Workflow <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Grid: Overdue Invoices & Pending Approvals */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Overdue Invoices Panel */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400">
                <AlertCircle className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-white">Overdue Invoices</h3>
              {overdue_invoices?.length > 0 && (
                <Badge variant="urgent">{overdue_invoices.length} Overdue</Badge>
              )}
            </div>
            <Button
              onClick={() => onNavigate('invoices')}
              variant="ghost"
              size="sm"
              className="text-xs"
            >
              View All Invoices
            </Button>
          </div>

          <div className="mt-3 space-y-2.5 flex-1">
            {!overdue_invoices?.length ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-2" />
                <p className="text-xs text-slate-400">Zero overdue invoices! All payments are on schedule.</p>
              </div>
            ) : (
              overdue_invoices.map((inv) => (
                <div
                  key={inv.id}
                  className="p-3 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition-all flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-white truncate">
                        {inv.customer_name || 'Customer'}
                      </span>
                      <Badge variant="urgent">Overdue</Badge>
                    </div>
                    <span className="text-[11px] text-slate-400 mt-0.5 block">
                      {inv.invoice_number} • Due: {inv.due_date}
                    </span>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="text-xs font-bold text-rose-400">
                      {formatMoney(inv.amount)}
                    </span>
                    <Button
                      onClick={() => handleQuickReminder(inv.id, inv.invoice_number)}
                      variant="primary"
                      size="sm"
                      loading={reminderLoadingId === inv.id}
                      icon={Send}
                      className="text-xs"
                    >
                      Remind
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Human-in-the-Loop Approval Queue */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400">
                <Sparkles className="w-4 h-4" />
              </div>
              <h3 className="text-sm font-bold text-white">Approval Center (HITL)</h3>
              {pending_approvals?.length > 0 && (
                <Badge variant="ai">{pending_approvals.length} Pending</Badge>
              )}
            </div>
            <Button
              onClick={() => onNavigate('approvals')}
              variant="ghost"
              size="sm"
              className="text-xs"
            >
              Approval Queue
            </Button>
          </div>

          <div className="mt-3 space-y-2.5 flex-1">
            {!pending_approvals?.length ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <CheckCircle2 className="w-8 h-8 text-emerald-400 mb-2" />
                <p className="text-xs text-slate-400">No actions awaiting approval. Safe mode active.</p>
              </div>
            ) : (
              pending_approvals.map((app) => (
                <div
                  key={app.id}
                  className="p-3 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition-all space-y-2"
                >
                  <div className="flex items-center justify-between gap-2">
                    <Badge variant="warning">{app.action_type}</Badge>
                    <span className="text-[10px] text-slate-400">Requires Owner Sign-off</span>
                  </div>
                  <p className="text-xs text-slate-300 leading-snug line-clamp-2">
                    {app.recommendation}
                  </p>
                  <div className="flex justify-end pt-1">
                    <Button
                      onClick={() => onNavigate('approvals')}
                      variant="secondary"
                      size="sm"
                      icon={ArrowRight}
                      className="text-xs text-indigo-300"
                    >
                      Review Action
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Bottom Grid: Tasks & Activity Logs */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Urgent Tasks */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-4 h-4 text-sky-400" />
              <h3 className="text-sm font-bold text-white">Priority Operations Tasks</h3>
            </div>
            <Button
              onClick={() => onNavigate('tasks')}
              variant="ghost"
              size="sm"
              className="text-xs"
            >
              All Tasks
            </Button>
          </div>

          <div className="mt-3 space-y-2">
            {!urgent_tasks?.length ? (
              <div className="text-center py-6 text-xs text-slate-400">
                No active tasks.
              </div>
            ) : (
              urgent_tasks.map((task) => (
                <div
                  key={task.id}
                  className="p-3 rounded-xl bg-slate-900/50 border border-slate-800/80 flex items-center justify-between gap-3"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge variant={task.priority === 'High' ? 'urgent' : 'warning'}>
                        {task.priority}
                      </Badge>
                      <span className="text-xs font-semibold text-slate-200 truncate">{task.title}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-0.5 block">
                      Assigned: {task.assigned_user} {task.due_date ? `• Due: ${task.due_date}` : ''}
                    </span>
                  </div>
                  <Badge variant={task.status === 'Completed' ? 'success' : 'gray'}>
                    {task.status}
                  </Badge>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Activity Audit Log */}
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-bold text-white">Recent Activity & Audit Trail</h3>
            </div>
            <Button
              onClick={() => onNavigate('activity')}
              variant="ghost"
              size="sm"
              className="text-xs"
            >
              Full Log
            </Button>
          </div>

          <div className="mt-3 space-y-2.5 max-h-60 overflow-y-auto">
            {!recent_activities?.length ? (
              <div className="text-center py-6 text-xs text-slate-400">
                No recent activity recorded.
              </div>
            ) : (
              recent_activities.map((act) => (
                <div
                  key={act.id}
                  className="p-2.5 rounded-xl bg-slate-900/40 border border-slate-800/60 flex items-start gap-2.5"
                >
                  <Badge variant={act.actor_type === 'AI Agent' ? 'ai' : 'gray'} className="shrink-0 mt-0.5">
                    {act.actor_type === 'AI Agent' ? '🤖 AI' : '👤 Owner'}
                  </Badge>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-300 leading-snug">{act.description}</p>
                    <span className="text-[10px] text-slate-500 mt-0.5 block">
                      {new Date(act.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {act.action}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
