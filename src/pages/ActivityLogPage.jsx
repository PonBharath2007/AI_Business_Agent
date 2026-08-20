import React, { useState, useEffect, useCallback } from 'react';
import {
  History,
  Bot,
  User,
  Search,
  Filter,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  Clock
} from 'lucide-react';
import api from '../services/api';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import EmptyState from '../components/common/EmptyState';

const ActivityLogPage = () => {
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actorFilter, setActorFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const fetchActivities = useCallback(async () => {
    try {
      const res = await api.get(`/activities?actor=${actorFilter}`);
      setActivities(res.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [actorFilter]);

  useEffect(() => {
    fetchActivities();
  }, [fetchActivities]);

  const filtered = activities.filter((act) => {
    const q = searchQuery.toLowerCase();
    return (
      act.action?.toLowerCase().includes(q) ||
      act.description?.toLowerCase().includes(q) ||
      act.actor_type?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Activity & System Audit Log
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Complete verifiable audit trail of all AI agent actions, user approvals, and operations.
          </p>
        </div>

        <Button
          onClick={fetchActivities}
          variant="secondary"
          size="sm"
          icon={RefreshCw}
          className="text-xs self-start sm:self-auto"
        >
          Refresh Log
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="glass-panel p-3 rounded-2xl border border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Actor filter tabs */}
        <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-slate-800 w-full sm:w-auto">
          {[
            { id: 'all', label: 'All Actors' },
            { id: 'AI Agent', label: '🤖 AI Agent' },
            { id: 'Business Owner', label: '👤 Owner' },
            { id: 'System', label: '⚙️ System' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActorFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                actorFilter === tab.id
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search audit descriptions..."
            className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Timeline List */}
      <div className="glass-panel rounded-2xl border border-slate-800 p-4 sm:p-6 space-y-4">
        {!filtered.length ? (
          <EmptyState
            icon={History}
            title="No activity records"
            description="No actions found matching the current search parameters."
          />
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
            {filtered.map((act) => {
              const isAI = act.actor_type === 'AI Agent';
              const isWarning = act.status === 'warning';

              return (
                <div key={act.id} className="relative group">
                  {/* Timeline Dot */}
                  <div
                    className={`absolute -left-6 top-1 w-5 h-5 rounded-full border-2 border-slate-900 flex items-center justify-center text-[9px] font-bold ${
                      isAI
                        ? 'bg-indigo-500 text-white shadow-md shadow-indigo-500/50'
                        : isWarning
                        ? 'bg-amber-500 text-slate-900'
                        : 'bg-emerald-500 text-white'
                    }`}
                  >
                    {isAI ? 'AI' : 'U'}
                  </div>

                  <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition-colors">
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-slate-800/60">
                      <div className="flex items-center gap-2">
                        <Badge variant={isAI ? 'ai' : 'gray'}>
                          {act.actor_type}
                        </Badge>
                        <span className="text-xs font-bold text-white">{act.action}</span>
                      </div>
                      <span className="text-[11px] text-slate-400 flex items-center gap-1">
                        <Clock className="w-3 h-3 text-slate-500" />
                        {new Date(act.created_at).toLocaleString()}
                      </span>
                    </div>

                    <p className="text-xs text-slate-200 mt-2 leading-relaxed">
                      {act.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ActivityLogPage;
