import React, { useState, useEffect, useCallback } from 'react';
import {
  Workflow,
  Plus,
  Play,
  CheckCircle2,
  Clock,
  ShieldCheck,
  AlertCircle,
  Sparkles,
  ArrowRight,
  RefreshCw,
  Trash2,
  Sliders,
  Layers,
  Check,
  RotateCw
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const WorkflowBuilderPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [activeTab, setActiveTab] = useState('rules'); // 'rules' or 'executions'
  const [rules, setRules] = useState([]);
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [executingId, setExecutingId] = useState(null);

  // New Rule Form
  const [newRule, setNewRule] = useState({
    name: '',
    description: '',
    trigger_event: 'invoice_overdue',
    amount_threshold: '50000',
    days_overdue: '7',
    action_type: 'generate_reminder',
    require_approval: true
  });

  const fetchData = useCallback(async () => {
    try {
      const [rulesRes, execRes] = await Promise.all([
        api.get('/workflows'),
        api.get('/workflows/executions')
      ]);
      setRules(rulesRes.data || []);
      setExecutions(execRes.data || []);
    } catch (err) {
      console.error('Error fetching workflows:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleCreateRule = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name: newRule.name,
        description: newRule.description,
        trigger_event: newRule.trigger_event,
        condition_json: {
          amount_gt: parseFloat(newRule.amount_threshold || 0),
          days_overdue_gte: parseInt(newRule.days_overdue || 1)
        },
        action_type: newRule.action_type,
        require_approval: newRule.require_approval,
        is_active: true
      };

      await api.post('/workflows', payload);
      addToast('success', 'Workflow Rule Created', `Rule '${newRule.name}' is now active.`);
      setCreateModalOpen(false);
      setNewRule({
        name: '',
        description: '',
        trigger_event: 'invoice_overdue',
        amount_threshold: '50000',
        days_overdue: '7',
        action_type: 'generate_reminder',
        require_approval: true
      });
      fetchData();
    } catch (err) {
      addToast('error', 'Creation Error', 'Failed to create workflow rule.');
    }
  };

  const handleTriggerRule = async (ruleId) => {
    setExecutingId(ruleId);
    try {
      const res = await api.post(`/workflows/${ruleId}/execute`);
      addToast('success', 'Workflow Triggered', res.data.message || 'Workflow executed successfully.');
      fetchData();
    } catch (err) {
      addToast('error', 'Execution Error', 'Failed to trigger workflow rule.');
    } finally {
      setExecutingId(null);
    }
  };

  const handleDeleteRule = async (ruleId) => {
    if (!window.confirm('Delete this workflow automation rule?')) return;
    try {
      await api.delete(`/workflows/${ruleId}`);
      addToast('info', 'Rule Removed', 'Workflow rule deleted.');
      fetchData();
    } catch (err) {
      addToast('error', 'Error', 'Failed to delete rule.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            AI Workflow Builder & Autonomous Agents
            <Badge variant="ai">Multi-Step Automation</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Define declarative business automation rules (WHEN → CHECK → THEN → REQUIRE → EXECUTE) with built-in Human-in-the-Loop approval.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Tabs */}
          <div className="flex items-center bg-slate-900 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('rules')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'rules' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              Automation Rules ({rules.length})
            </button>
            <button
              onClick={() => setActiveTab('executions')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'executions' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
              }`}
            >
              Execution Audit ({executions.length})
            </button>
          </div>

          <Button
            onClick={() => setCreateModalOpen(true)}
            variant="primary"
            size="sm"
            icon={Plus}
            className="text-xs"
          >
            New Rule
          </Button>
        </div>
      </div>

      {activeTab === 'rules' ? (
        <div className="space-y-4">
          {!rules.length ? (
            <EmptyState
              icon={Workflow}
              title="No Automation Rules Configured"
              description="Create your first rule to automate overdue collections, large transaction alerts, and client follow-ups."
              actionText="Create Workflow Rule"
              onAction={() => setCreateModalOpen(true)}
            />
          ) : (
            rules.map((rule) => (
              <div
                key={rule.id}
                className="glass-panel rounded-2xl p-5 sm:p-6 border border-slate-800 hover:border-indigo-500/40 transition-all space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center font-bold">
                      <Workflow className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="text-sm font-bold text-white">{rule.name}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">{rule.description || 'Continuous operations rule'}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Badge variant={rule.is_active ? 'success' : 'gray'}>
                      {rule.is_active ? 'ACTIVE' : 'PAUSED'}
                    </Badge>
                    {rule.require_approval && (
                      <Badge variant="ai">REQUIRES OWNER APPROVAL</Badge>
                    )}
                  </div>
                </div>

                {/* Structured Logic Visual Flow Blocks */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 text-xs">
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-indigo-400">1. WHEN</span>
                    <p className="font-semibold text-slate-200 mt-1 capitalize">{rule.trigger_event.replace('_', ' ')}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-amber-400">2. CHECK</span>
                    <p className="font-semibold text-slate-200 mt-1">
                      {rule.condition_json?.amount_gt ? `Amount > ${formatMoney(rule.condition_json.amount_gt)}` : 'Overdue status'}
                    </p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-violet-400">3. THEN</span>
                    <p className="font-semibold text-slate-200 mt-1 capitalize">{rule.action_type.replace('_', ' ')}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-emerald-400">4. REQUIRE</span>
                    <p className="font-semibold text-slate-200 mt-1">{rule.require_approval ? 'Owner Approval' : 'Auto Execute'}</p>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-sky-400">5. EXECUTE</span>
                    <p className="font-semibold text-slate-200 mt-1">Dispatch & Audit Log</p>
                  </div>
                </div>

                {/* Bottom Actions */}
                <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                  <span className="text-[11px] text-slate-500">
                    Created on {new Date(rule.created_at).toLocaleDateString()}
                  </span>

                  <div className="flex items-center gap-2">
                    <Button
                      onClick={() => handleTriggerRule(rule.id)}
                      variant="secondary"
                      size="sm"
                      loading={executingId === rule.id}
                      icon={Play}
                      className="text-xs text-indigo-300 hover:text-white"
                    >
                      Run Rule Now
                    </Button>
                    <button
                      onClick={() => handleDeleteRule(rule.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
                      title="Delete Rule"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        /* Executions Audit Timeline */
        <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 uppercase font-semibold">
                <tr>
                  <th className="p-4">Execution / Rule</th>
                  <th className="p-4">Trigger Data</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Execution Steps</th>
                  <th className="p-4">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 bg-slate-900/30">
                {!executions.length ? (
                  <tr>
                    <td colSpan="5" className="p-8 text-center text-slate-400">
                      No workflow execution records yet.
                    </td>
                  </tr>
                ) : (
                  executions.map((ex) => (
                    <tr key={ex.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="p-4 font-bold text-white flex items-center gap-2">
                        <Workflow className="w-4 h-4 text-indigo-400" />
                        <span>{ex.rule_name || 'Golden Workflow'}</span>
                      </td>
                      <td className="p-4 text-slate-300 font-mono text-[11px]">
                        {ex.trigger_data_json?.invoice_number ? `Invoice: ${ex.trigger_data_json.invoice_number}` : 'Manual Event'}
                      </td>
                      <td className="p-4">
                        <Badge variant={ex.status === 'executed' ? 'success' : (ex.status === 'pending_approval' ? 'warning' : 'info')}>
                          {ex.status.replace('_', ' ').toUpperCase()}
                        </Badge>
                      </td>
                      <td className="p-4 text-slate-300 text-[11px]">
                        {ex.execution_log_json?.length ? `${ex.execution_log_json.length} steps recorded` : 'Multi-step completed'}
                      </td>
                      <td className="p-4 text-slate-400">
                        {new Date(ex.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Create Rule Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Configure New AI Automation Rule"
      >
        <form onSubmit={handleCreateRule} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Rule Name</label>
            <input
              type="text"
              value={newRule.name}
              onChange={(e) => setNewRule({ ...newRule, name: e.target.value })}
              placeholder="e.g. Overdue Invoices > ₹50,000 Auto Reminder"
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Description</label>
            <textarea
              value={newRule.description}
              onChange={(e) => setNewRule({ ...newRule, description: e.target.value })}
              placeholder="Describe what business situation this rule automates..."
              rows={2}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Trigger Event (WHEN)</label>
              <select
                value={newRule.trigger_event}
                onChange={(e) => setNewRule({ ...newRule, trigger_event: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="invoice_overdue">Invoice Overdue</option>
                <option value="invoice_uploaded">Invoice Uploaded</option>
                <option value="contract_expiring">Contract Approaching Expiry</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Action (THEN)</label>
              <select
                value={newRule.action_type}
                onChange={(e) => setNewRule({ ...newRule, action_type: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="generate_reminder">Generate Payment Reminder Draft</option>
                <option value="create_task">Create High Priority Task</option>
                <option value="alert_owner">Notify Owner Immediately</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Amount Threshold ({business.currency})</label>
              <input
                type="number"
                value={newRule.amount_threshold}
                onChange={(e) => setNewRule({ ...newRule, amount_threshold: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Days Overdue</label>
              <input
                type="number"
                value={newRule.days_overdue}
                onChange={(e) => setNewRule({ ...newRule, days_overdue: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-200">Require Owner Approval Before Execution</span>
            <input
              type="checkbox"
              checked={newRule.require_approval}
              onChange={(e) => setNewRule({ ...newRule, require_approval: e.target.checked })}
              className="w-4 h-4 rounded text-indigo-600 bg-slate-800 border-slate-700"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <Button onClick={() => setCreateModalOpen(false)} variant="ghost" size="sm">
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm">
              Save Automation Rule
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default WorkflowBuilderPage;
