import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  Edit3,
  Sparkles,
  Send,
  AlertCircle,
  Mail,
  MessageSquare,
  User,
  Clock,
  Check,
  Languages
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const ApprovalsPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [approvals, setApprovals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('pending');
  const [actionLoadingId, setActionLoadingId] = useState(null);

  // Edit action modal state
  const [editingApproval, setEditingApproval] = useState(null);
  const [editSubject, setEditSubject] = useState('');
  const [editBody, setEditBody] = useState('');
  const [editRecipient, setEditRecipient] = useState('');

  const fetchApprovals = useCallback(async () => {
    try {
      const res = await api.get(`/approvals?status=${statusFilter}`);
      setApprovals(res.data || []);
    } catch (err) {
      console.error('Error fetching approvals:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchApprovals();
  }, [fetchApprovals]);

  const handleApprove = async (approval, editedData = null) => {
    setActionLoadingId(approval.id);
    try {
      const payload = editedData || approval.action_data;
      const res = await api.post(`/approvals/${approval.id}/approve`, payload);
      addToast('success', 'Action Approved & Executed', res.data.message || 'Workflow executed successfully.');
      if (editingApproval) setEditingApproval(null);
      fetchApprovals();
    } catch (err) {
      addToast('error', 'Execution Error', 'Failed to approve and execute action.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReject = async (approvalId) => {
    const reason = prompt('Reason for declining this AI action (optional):');
    if (reason === null) return; // cancelled prompt

    setActionLoadingId(approvalId);
    try {
      await api.post(`/approvals/${approvalId}/reject`, { reason: reason || 'Declined by business owner' });
      addToast('warning', 'Action Rejected', 'Action marked as rejected.');
      fetchApprovals();
    } catch (err) {
      addToast('error', 'Error', 'Failed to reject action.');
    } finally {
      setActionLoadingId(null);
    }
  };

  const openEditModal = (app) => {
    const isSms = app.action_type === 'send_sms' || app.action_data?.channel === 'sms';
    setEditingApproval(app);
    setEditSubject(app.action_data?.subject || (isSms ? 'SMS Notice' : `Payment Reminder – Invoice ${app.action_data?.invoice_number || 'INV-1001'}`));
    setEditBody(app.action_data?.body || app.action_data?.message || '');
    if (isSms) {
      setEditRecipient(app.action_data?.recipient_phone || app.action_data?.phone || app.action_data?.customer_phone || '');
    } else {
      setEditRecipient(app.action_data?.recipient_email || app.action_data?.customer_email || '');
    }
  };

  const handleSaveAndApprove = async () => {
    if (!editingApproval) return;
    const isSms = editingApproval.action_type === 'send_sms' || editingApproval.action_data?.channel === 'sms';
    const updatedData = {
      ...editingApproval.action_data,
      subject: editSubject,
      body: editBody,
      ...(isSms ? { recipient_phone: editRecipient } : { recipient_email: editRecipient })
    };
    await handleApprove(editingApproval, updatedData);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Approval Center (Human-in-the-Loop AI)
            <Badge variant="ai">Multilingual Communication</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Review, edit, and approve AI-generated business actions. Sensitive operations are never executed without your sign-off.
          </p>
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 bg-slate-900/80 p-1 rounded-xl border border-slate-800 self-start sm:self-auto">
          {[
            { id: 'pending', label: 'Pending Approval' },
            { id: 'approved', label: 'Approved & Executed' },
            { id: 'rejected', label: 'Rejected' },
            { id: 'all', label: 'All History' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setStatusFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                statusFilter === tab.id
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Approval Cards List */}
      <div className="space-y-4">
        {!approvals.length ? (
          <EmptyState
            icon={ShieldCheck}
            title="Approval Queue Clear"
            description="No actions waiting for review. All AI operations are up to date."
            actionText="Go to Dashboard"
            onAction={() => onNavigate('dashboard')}
          />
        ) : (
          approvals.map((app) => {
            const data = app.action_data || {};
            const isPending = app.status === 'pending';
            const isApproved = app.status === 'approved';
            const isRejected = app.status === 'rejected';
            const isSms = app.action_type === 'send_sms' || data.channel === 'sms';
            const lang = data.language || 'en';
            const langTag = lang === 'ta' ? 'தமிழ்' : (lang === 'en_ta' ? 'EN + தமிழ்' : 'English');

            return (
              <div
                key={app.id}
                className={`glass-panel rounded-2xl border p-5 sm:p-6 transition-all ${
                  isPending
                    ? 'border-indigo-500/40 bg-gradient-to-br from-indigo-950/20 via-slate-900/70 to-slate-900/50 shadow-xl'
                    : isApproved
                    ? 'border-emerald-500/20 bg-slate-900/40 opacity-85'
                    : 'border-slate-800 bg-slate-950/40 opacity-70'
                }`}
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
                  <div className="flex items-start gap-3.5">
                    <div className="w-10 h-10 rounded-2xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 flex items-center justify-center shrink-0">
                      {isSms ? <MessageSquare className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                          {isSms ? 'SMS Communication' : (app.action_type === 'send_payment_reminder' ? 'Email Payment Reminder' : app.action_type)}
                        </span>
                        <span className="px-2 py-0.5 rounded-md bg-indigo-950 text-indigo-300 text-[10px] font-bold uppercase border border-indigo-500/30">
                          {langTag}
                        </span>
                        <Badge
                          variant={isPending ? 'warning' : (isApproved ? 'success' : 'danger')}
                        >
                          {app.status.toUpperCase()}
                        </Badge>
                      </div>
                      <h3 className="text-base font-bold text-white mt-1">
                        Send {langTag} {isSms ? 'SMS' : 'Notice'} to {data.customer_name || 'Customer'}
                      </h3>
                    </div>
                  </div>

                  {/* Summary Badges */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    {data.invoice_number && (
                      <span className="px-2.5 py-1 rounded-xl bg-slate-800 border border-slate-700 text-slate-200 font-semibold">
                        Invoice: {data.invoice_number}
                      </span>
                    )}
                    {data.amount && (
                      <span className="px-2.5 py-1 rounded-xl bg-rose-500/20 border border-rose-500/30 text-rose-300 font-bold">
                        Amount: {formatMoney(data.amount)}
                      </span>
                    )}
                    <span className="text-[11px] text-slate-400">
                      Requested: {new Date(app.requested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>

                {/* AI Recommendation Message */}
                {app.recommendation && (
                  <div className="mt-4 p-3.5 rounded-xl bg-indigo-950/40 border border-indigo-500/20 flex items-start gap-2.5">
                    <Sparkles className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
                    <div className="text-xs text-slate-200">
                      <strong className="text-indigo-300">AI Recommendation: </strong>
                      {app.recommendation}
                    </div>
                  </div>
                )}

                {/* Generated Content Preview */}
                {(data.body || data.message) && (
                  <div className="mt-4 p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                    <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 pb-2 border-b border-slate-900 gap-2">
                      <span><strong>Recipient:</strong> {isSms ? (data.recipient_phone || data.phone || data.customer_phone) : (data.recipient_email || data.customer_email)}</span>
                      {!isSms && data.subject && <span><strong>Subject:</strong> {data.subject}</span>}
                    </div>
                    <p className="text-xs text-slate-200 whitespace-pre-wrap font-sans leading-relaxed">
                      {data.body || data.message}
                    </p>
                  </div>
                )}

                {/* Bottom Decision Actions */}
                {isPending && (
                  <div className="mt-5 pt-4 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-3">
                    <div className="text-xs text-slate-400">
                      👉 <em>Review the draft above. You can approve immediately, edit contents, or reject.</em>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        onClick={() => openEditModal(app)}
                        variant="secondary"
                        size="sm"
                        icon={Edit3}
                        className="text-xs"
                      >
                        Edit Draft
                      </Button>
                      <Button
                        onClick={() => handleReject(app.id)}
                        variant="ghost"
                        size="sm"
                        disabled={actionLoadingId === app.id}
                        icon={XCircle}
                        className="text-xs text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                      >
                        Reject
                      </Button>
                      <Button
                        onClick={() => handleApprove(app)}
                        variant="success"
                        size="sm"
                        loading={actionLoadingId === app.id}
                        icon={CheckCircle2}
                        className="text-xs font-bold"
                      >
                        Approve & Execute Action
                      </Button>
                    </div>
                  </div>
                )}

                {/* Execution timestamp for already approved */}
                {isApproved && (
                  <div className="mt-4 pt-3 border-t border-slate-800 text-xs text-emerald-400 flex items-center gap-1.5">
                    <Check className="w-4 h-4" />
                    <span>Approved & Dispatched on {new Date(app.approved_at || app.requested_at).toLocaleString()}</span>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Edit & Approve Modal */}
      {editingApproval && (
        <Modal
          isOpen={Boolean(editingApproval)}
          onClose={() => setEditingApproval(null)}
          title="Edit AI Generated Action Before Approval"
          maxWidth="max-w-3xl"
        >
          <div className="space-y-4 text-xs">
            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                {editingApproval.action_type === 'send_sms' ? 'Recipient Phone Number' : 'Recipient Email'}
              </label>
              <input
                type={editingApproval.action_type === 'send_sms' ? 'tel' : 'email'}
                value={editRecipient}
                onChange={(e) => setEditRecipient(e.target.value)}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            {editingApproval.action_type !== 'send_sms' && (
              <div>
                <label className="block font-semibold text-slate-300 mb-1">Subject Line</label>
                <input
                  type="text"
                  value={editSubject}
                  onChange={(e) => setEditSubject(e.target.value)}
                  required
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Message Content (Supports English, தமிழ், and Bilingual UTF-8)
              </label>
              <textarea
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                rows={7}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-indigo-500 font-sans leading-relaxed text-xs"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <Button onClick={() => setEditingApproval(null)} variant="ghost" size="sm">
                Cancel
              </Button>
              <Button
                onClick={handleSaveAndApprove}
                variant="success"
                size="sm"
                loading={actionLoadingId === editingApproval.id}
                icon={CheckCircle2}
              >
                Approve with Edits & Execute
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default ApprovalsPage;
