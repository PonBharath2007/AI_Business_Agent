import React, { useState, useEffect, useCallback } from 'react';
import {
  Settings,
  Building,
  DollarSign,
  Clock,
  Mail,
  Phone,
  RotateCcw,
  Sparkles,
  Save,
  CheckCircle2,
  AlertCircle,
  FileText,
  ShieldCheck,
  BrainCircuit,
  Plus,
  Trash2,
  Edit2
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';

const SettingsPage = () => {
  const { business, updateProfile, resetDemoData, formatMoney, loading: bizLoading } = useBusiness();
  const { addToast } = useNotifications();

  const [activeTab, setActiveTab] = useState('profile'); // 'profile', 'policies', 'memory', 'demo'
  const [formData, setFormData] = useState({
    name: '',
    category: '',
    currency: 'USD',
    timezone: 'America/New_York',
    payment_terms: 'Standard 30-day payment terms',
    email: '',
    phone: '',
    address: '',
    email_signature: ''
  });

  const [saving, setSaving] = useState(false);
  const [resetting, setResetting] = useState(false);

  // Policies State
  const [policies, setPolicies] = useState([]);
  const [policyModalOpen, setPolicyModalOpen] = useState(false);
  const [newPolicy, setNewPolicy] = useState({
    policy_name: '',
    policy_type: 'approval_threshold',
    threshold_value: '50000',
    action_required: 'require_approval',
    description: ''
  });

  // Memory State
  const [memories, setMemories] = useState([]);
  const [memoryModalOpen, setMemoryModalOpen] = useState(false);
  const [newMemory, setNewMemory] = useState({
    category: 'payment_behavior',
    memory_key: '',
    memory_value: '',
    confidence: 0.95
  });

  const fetchPoliciesAndMemory = useCallback(async () => {
    try {
      const [polRes, memRes] = await Promise.all([
        api.get('/policies'),
        api.get('/memory')
      ]);
      setPolicies(polRes.data || []);
      setMemories(memRes.data || []);
    } catch (err) {
      console.error('Settings fetch error:', err);
    }
  }, []);

  useEffect(() => {
    if (business) {
      setFormData({
        name: business.name || '',
        category: business.category || '',
        currency: business.currency || 'USD',
        timezone: business.timezone || 'America/New_York',
        payment_terms: business.payment_terms || 'Standard 30-day payment terms',
        email: business.email || '',
        phone: business.phone || '',
        address: business.address || '',
        email_signature: business.email_signature || ''
      });
    }
    fetchPoliciesAndMemory();
  }, [business, fetchPoliciesAndMemory]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await updateProfile(formData);
      addToast('success', 'Profile Updated', 'Business profile settings saved.');
    } catch (err) {
      addToast('error', 'Error', 'Failed to update business profile.');
    } finally {
      setSaving(false);
    }
  };

  const handleCreatePolicy = async (e) => {
    e.preventDefault();
    try {
      await api.post('/policies', {
        policy_name: newPolicy.policy_name,
        policy_type: newPolicy.policy_type,
        threshold_value: parseFloat(newPolicy.threshold_value || 0),
        action_required: newPolicy.action_required,
        description: newPolicy.description,
        is_active: true
      });
      addToast('success', 'Policy Added', `Policy '${newPolicy.policy_name}' created.`);
      setPolicyModalOpen(false);
      setNewPolicy({
        policy_name: '',
        policy_type: 'approval_threshold',
        threshold_value: '50000',
        action_required: 'require_approval',
        description: ''
      });
      fetchPoliciesAndMemory();
    } catch (err) {
      addToast('error', 'Error', 'Failed to create policy.');
    }
  };

  const handleDeletePolicy = async (id) => {
    if (!window.confirm('Delete this business policy rule?')) return;
    try {
      await api.delete(`/policies/${id}`);
      addToast('info', 'Policy Removed', 'Business policy deleted.');
      fetchPoliciesAndMemory();
    } catch (err) {
      addToast('error', 'Error', 'Failed to delete policy.');
    }
  };

  const handleCreateMemory = async (e) => {
    e.preventDefault();
    try {
      await api.post('/memory', newMemory);
      addToast('success', 'Memory Recorded', `AI business memory '${newMemory.memory_key}' added.`);
      setMemoryModalOpen(false);
      setNewMemory({
        category: 'payment_behavior',
        memory_key: '',
        memory_value: '',
        confidence: 0.95
      });
      fetchPoliciesAndMemory();
    } catch (err) {
      addToast('error', 'Error', 'Failed to add memory.');
    }
  };

  const handleDeleteMemory = async (id) => {
    if (!window.confirm('Remove this business memory item?')) return;
    try {
      await api.delete(`/memory/${id}`);
      addToast('info', 'Memory Removed', 'AI memory item removed.');
      fetchPoliciesAndMemory();
    } catch (err) {
      addToast('error', 'Error', 'Failed to delete memory.');
    }
  };

  const handleReset = async () => {
    if (window.confirm('Reset all demo data (ABC Ltd, Invoices, Tasks, Approvals) to initial pristine state?')) {
      setResetting(true);
      try {
        await resetDemoData();
        addToast('success', 'Demo Reset Complete', 'Database refreshed to initial state.');
        window.location.reload();
      } catch (err) {
        addToast('error', 'Error', 'Failed to reset demo data.');
      } finally {
        setResetting(false);
      }
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Business Profile & Policy Engine
            <Badge variant="ai">Configuration</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Configure company identity, business policies, AI business memory, and demo baseline data.
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800 self-start">
          {[
            { id: 'profile', label: 'Profile' },
            { id: 'policies', label: `Policies (${policies.length})` },
            { id: 'memory', label: `AI Memory (${memories.length})` },
            { id: 'demo', label: 'Demo Data' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === tab.id
                  ? 'bg-indigo-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {activeTab === 'profile' && (
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <h3 className="text-sm font-bold text-white pb-2 border-b border-slate-800">
              Company Identity & Localization
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Company / Agency Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Industry / Category</label>
                <input
                  type="text"
                  value={formData.category}
                  onChange={(e) => setFormData({ ...formData, category: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Currency</label>
                <select
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="INR">INR (₹) – Indian Rupee</option>
                  <option value="USD">USD ($) – US Dollar</option>
                  <option value="EUR">EUR (€) – Euro</option>
                  <option value="GBP">GBP (£) – British Pound</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Timezone</label>
                <input
                  type="text"
                  value={formData.timezone}
                  onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Standard Payment Terms</label>
              <input
                type="text"
                value={formData.payment_terms}
                onChange={(e) => setFormData({ ...formData, payment_terms: e.target.value })}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Billing Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Phone Number</label>
                <input
                  type="text"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Default AI Email Signature</label>
              <textarea
                value={formData.email_signature}
                onChange={(e) => setFormData({ ...formData, email_signature: e.target.value })}
                rows={3}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 font-mono leading-relaxed"
              />
            </div>

            <div className="pt-2 flex justify-end">
              <Button type="submit" variant="primary" size="md" loading={saving} icon={Save}>
                Save Profile Changes
              </Button>
            </div>
          </div>
        </form>
      )}

      {activeTab === 'policies' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Active Business Governance Policies</h3>
            <Button onClick={() => setPolicyModalOpen(true)} variant="primary" size="sm" icon={Plus} className="text-xs">
              Add Policy Rule
            </Button>
          </div>

          <div className="space-y-3">
            {policies.map((p) => (
              <div key={p.id} className="glass-panel rounded-2xl p-4 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
                    <span className="text-xs font-bold text-white">{p.policy_name}</span>
                    <Badge variant={p.is_active ? 'success' : 'gray'}>
                      {p.is_active ? 'Active' : 'Disabled'}
                    </Badge>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">{p.description}</p>
                  <div className="mt-1 text-[10px] text-indigo-300">
                    Action: <strong>{p.action_required}</strong> {p.threshold_value ? `• Threshold: ${formatMoney(p.threshold_value)}` : ''}
                  </div>
                </div>
                <button
                  onClick={() => handleDeletePolicy(p.id)}
                  className="self-end sm:self-center p-1.5 rounded-lg text-slate-400 hover:text-rose-400 transition-colors cursor-pointer"
                  title="Delete Policy"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'memory' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">AI Business Memory & Learned Context</h3>
              <p className="text-[11px] text-slate-400">Context injected into AI agent decisions and command reasoning.</p>
            </div>
            <Button onClick={() => setMemoryModalOpen(true)} variant="primary" size="sm" icon={Plus} className="text-xs">
              Add Memory
            </Button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {memories.map((m) => (
              <div key={m.id} className="glass-panel rounded-2xl p-4 border border-violet-500/20 bg-gradient-to-br from-violet-950/20 to-slate-900/40 space-y-2 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5">
                      <BrainCircuit className="w-3.5 h-3.5 text-violet-400" />
                      {m.memory_key}
                    </span>
                    <Badge variant="ai">{m.category}</Badge>
                  </div>
                  <p className="text-xs text-slate-300 mt-2 leading-relaxed">{m.memory_value}</p>
                </div>
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[10px] text-slate-500">
                  <span>Confidence: {int(parseFloat(m.confidence || 0.95)*100)}%</span>
                  <button
                    onClick={() => handleDeleteMemory(m.id)}
                    className="p-1 rounded text-slate-500 hover:text-rose-400 transition-colors cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeTab === 'demo' && (
        <div className="glass-panel rounded-2xl p-6 border border-rose-500/30 bg-gradient-to-r from-rose-950/20 via-slate-900/60 to-slate-900/40 space-y-3">
          <div className="flex items-center gap-2 text-sm font-bold text-rose-300">
            <RotateCcw className="w-4 h-4" />
            <span>Demo Data Management</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            Need to re-demonstrate the Golden Demo workflow (ABC Ltd overdue invoice, pending approvals, and AI summaries)?
            Click below to reset the entire database to the initial clean demonstration baseline.
          </p>
          <div className="pt-2">
            <Button
              onClick={handleReset}
              variant="danger"
              size="sm"
              loading={resetting}
              icon={RotateCcw}
              className="text-xs"
            >
              Reset Demo Data to Initial Baseline
            </Button>
          </div>
        </div>
      )}

      {/* Add Policy Modal */}
      <Modal isOpen={policyModalOpen} onClose={() => setPolicyModalOpen(false)} title="Configure Business Policy">
        <form onSubmit={handleCreatePolicy} className="space-y-3 text-xs">
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Policy Name</label>
            <input
              type="text"
              value={newPolicy.policy_name}
              onChange={(e) => setNewPolicy({ ...newPolicy, policy_name: e.target.value })}
              placeholder="e.g. Transactions > ₹50,000 Approval Required"
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Policy Type</label>
            <select
              value={newPolicy.policy_type}
              onChange={(e) => setNewPolicy({ ...newPolicy, policy_type: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="approval_threshold">Amount Approval Threshold</option>
              <option value="overdue_reminder">Overdue Reminder Schedule</option>
              <option value="escalation">Critical Overdue Escalation</option>
              <option value="external_comm_hitl">External Communications HITL</option>
            </select>
          </div>
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Threshold Value ({business.currency})</label>
            <input
              type="number"
              value={newPolicy.threshold_value}
              onChange={(e) => setNewPolicy({ ...newPolicy, threshold_value: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Description</label>
            <textarea
              value={newPolicy.description}
              onChange={(e) => setNewPolicy({ ...newPolicy, description: e.target.value })}
              rows={2}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <Button onClick={() => setPolicyModalOpen(false)} variant="ghost" size="sm">Cancel</Button>
            <Button type="submit" variant="primary" size="sm">Save Policy</Button>
          </div>
        </form>
      </Modal>

      {/* Add Memory Modal */}
      <Modal isOpen={memoryModalOpen} onClose={() => setMemoryModalOpen(false)} title="Record AI Business Memory">
        <form onSubmit={handleCreateMemory} className="space-y-3 text-xs">
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Memory Title / Key</label>
            <input
              type="text"
              value={newMemory.memory_key}
              onChange={(e) => setNewMemory({ ...newMemory, memory_key: e.target.value })}
              placeholder="e.g. ABC Ltd Billing Habit"
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Category</label>
            <select
              value={newMemory.category}
              onChange={(e) => setNewMemory({ ...newMemory, category: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="payment_behavior">Payment Behavior Pattern</option>
              <option value="business_instruction">Business Owner Instruction</option>
              <option value="customer_preference">Customer Preference</option>
              <option value="general">General Operations Fact</option>
            </select>
          </div>
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Memory Content / Observation</label>
            <textarea
              value={newMemory.memory_value}
              onChange={(e) => setNewMemory({ ...newMemory, memory_value: e.target.value })}
              rows={3}
              placeholder="Detail what the AI should remember when interacting with this customer or executing workflows..."
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <Button onClick={() => setMemoryModalOpen(false)} variant="ghost" size="sm">Cancel</Button>
            <Button type="submit" variant="primary" size="sm">Store Memory</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

function int(val) {
  return Math.round(val);
}

export default SettingsPage;
