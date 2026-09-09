import React, { useState, useEffect, useCallback } from 'react';
import {
  AlertTriangle,
  AlertOctagon,
  AlertCircle,
  Info,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Send,
  CheckCircle2,
  FileText,
  Clock,
  Filter
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';

const SEVERITY_CONFIG = {
  CRITICAL: {
    label: 'Critical Priority',
    color: 'border-rose-200 dark:border-rose-500/40 bg-rose-50/50 dark:bg-gradient-to-r dark:from-rose-950/30 dark:via-slate-900/60 dark:to-slate-900/40',
    badge: 'urgent',
    icon: AlertOctagon,
    iconColor: 'text-rose-600 dark:text-rose-400 bg-rose-50 dark:bg-rose-500/10 border-rose-200 dark:border-rose-500/20'
  },
  HIGH: {
    label: 'High Priority',
    color: 'border-amber-200 dark:border-amber-500/40 bg-amber-50/50 dark:bg-gradient-to-r dark:from-amber-950/20 dark:via-slate-900/60 dark:to-slate-900/40',
    badge: 'warning',
    icon: AlertTriangle,
    iconColor: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-500/10 border-amber-200 dark:border-amber-500/20'
  },
  MEDIUM: {
    label: 'Medium Priority',
    color: 'border-sky-200 dark:border-sky-500/30 bg-sky-50/50 dark:bg-slate-900/40',
    badge: 'info',
    icon: AlertCircle,
    iconColor: 'text-sky-600 dark:text-sky-400 bg-sky-50 dark:bg-sky-500/10 border-sky-200 dark:border-sky-500/20'
  },
  LOW: {
    label: 'Low Priority',
    color: 'border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/30',
    badge: 'gray',
    icon: Info,
    iconColor: 'text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 border-slate-200 dark:border-slate-700'
  }
};

const ExceptionCenterPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [severityFilter, setSeverityFilter] = useState('all');
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const fetchExceptions = useCallback(async () => {
    try {
      const res = await api.get('/exceptions');
      setExceptions(res.data || []);
    } catch (err) {
      console.error('Error fetching exceptions:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchExceptions();
  }, [fetchExceptions]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchExceptions();
  };

  const handleAction = async (exc) => {
    setActionLoadingId(exc.id);
    try {
      if (exc.action_type === 'generate_reminder' && exc.entity_id) {
        await api.post(`/invoices/${exc.entity_id}/reminder`);
        addToast('success', 'Reminder Prepared', `AI draft prepared for ${exc.title}. Routed to Approval Center.`);
        onNavigate('approvals');
      } else if (exc.action_target) {
        const tab = exc.action_target.replace('/', '');
        onNavigate(tab || 'dashboard');
      }
    } catch (err) {
      console.error('Exception action error:', err);
      addToast('error', 'Error', 'Failed to process exception action.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const filtered = exceptions.filter((e) => {
    if (severityFilter === 'all') return true;
    return e.severity === severityFilter;
  });

  const criticalCount = exceptions.filter((e) => e.severity === 'CRITICAL').length;
  const highCount = exceptions.filter((e) => e.severity === 'HIGH').length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            AI Exception Center & Anomaly Detection
            <Badge variant="ai">Autonomous Sentinel</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Focus on critical business outliers: overdue balances, unusually large invoices, expiring agreements, and approval bottlenecks.
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
            Scan Exceptions
          </Button>
        </div>
      </div>

      {/* Exception Metrics Summary Pills */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
        <div className="p-4 rounded-2xl bg-rose-50/60 dark:bg-rose-950/40 border border-rose-100 dark:border-rose-500/30 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-rose-600 dark:text-rose-300 tracking-wider">Critical Anomalies</span>
            <AlertOctagon className="w-4 h-4 text-rose-600 dark:text-rose-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">{criticalCount}</p>
          <span className="text-[10px] text-rose-600/80 dark:text-rose-300/80 mt-0.5 block">Immediate action required</span>
        </div>

        <div className="p-4 rounded-2xl bg-amber-50/60 dark:bg-amber-950/40 border border-amber-100 dark:border-amber-500/30 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-amber-600 dark:text-amber-300 tracking-wider">High Priority Risks</span>
            <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">{highCount}</p>
          <span className="text-[10px] text-amber-600/80 dark:text-amber-300/80 mt-0.5 block">Pending review within 24h</span>
        </div>

        <div className="p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-500/30 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-indigo-600 dark:text-indigo-300 tracking-wider">Total Detected</span>
            <Sparkles className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
          </div>
          <p className="text-2xl font-bold text-slate-900 dark:text-white mt-2">{exceptions.length}</p>
          <span className="text-[10px] text-indigo-600/80 dark:text-indigo-300/80 mt-0.5 block">Monitored database items</span>
        </div>

        <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/40 border border-emerald-100 dark:border-emerald-500/30 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase font-bold text-emerald-600 dark:text-emerald-300 tracking-wider">AI Sentinel Mode</span>
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-2">Active</p>
          <span className="text-[10px] text-emerald-600/80 dark:text-emerald-300/80 mt-0.5 block">Continuous rule evaluation</span>
        </div>
      </div>

      {/* Severity Filter Tabs */}
      <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-900/80 p-1 rounded-xl border border-slate-200 dark:border-slate-800 self-start">
        {[
          { id: 'all', label: 'All Exceptions' },
          { id: 'CRITICAL', label: '🔴 Critical' },
          { id: 'HIGH', label: '🟡 High' },
          { id: 'MEDIUM', label: '🔵 Medium' }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSeverityFilter(tab.id)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
              severityFilter === tab.id
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Exceptions List */}
      <div className="space-y-3.5">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 space-y-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs text-slate-500 dark:text-slate-400">Scanning business database for exceptions...</p>
          </div>
        ) : !filtered.length ? (
          <EmptyState
            icon={ShieldCheck}
            title="All Clear – Zero Critical Exceptions"
            description="Your operations sentinel reports zero unaddressed business exceptions or overdue anomalies."
            actionText="Go to Dashboard"
            onAction={() => onNavigate('dashboard')}
          />
        ) : (
          filtered.map((exc) => {
            const config = SEVERITY_CONFIG[exc.severity] || SEVERITY_CONFIG.MEDIUM;
            const Icon = config.icon;

            return (
              <div
                key={exc.id}
                className={`rounded-2xl p-5 border transition-all ${config.color} flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm`}
              >
                <div className="flex items-start gap-3.5 min-w-0">
                  <div className={`p-2 rounded-xl shrink-0 border ${config.iconColor}`}>
                    <Icon className="w-5 h-5" />
                  </div>

                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge variant={config.badge}>
                        {exc.severity}
                      </Badge>
                      <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400">
                        {exc.category}
                      </span>
                    </div>

                    <h4 className="text-sm font-bold text-slate-900 dark:text-white mt-1">
                      {exc.title}
                    </h4>

                    <p className="text-xs text-slate-700 dark:text-slate-300 mt-1 leading-relaxed">
                      {exc.description}
                    </p>

                    <div className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1.5">
                      <span className="font-semibold text-slate-700 dark:text-slate-300">💡 Suggested Action:</span>
                      <span>{exc.suggested_action}</span>
                    </div>
                  </div>
                </div>

                <div className="self-end sm:self-center shrink-0">
                  <Button
                    onClick={() => handleAction(exc)}
                    variant={exc.severity === 'CRITICAL' ? 'danger' : 'primary'}
                    size="sm"
                    loading={actionLoadingId === exc.id}
                    icon={ArrowRight}
                    className="text-xs font-bold"
                  >
                    Take Action
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default ExceptionCenterPage;
