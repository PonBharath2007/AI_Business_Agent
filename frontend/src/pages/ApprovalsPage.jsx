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

      if (editingApproval) setEditingApproval(null);

      // Handle no communication contact available
      if (res.data?.no_contact) {
        addToast(
          'warning',
          'No Communication Contact',
          res.data.message || 'No communication contact available for this customer. Follow-up task created.'
        );
        fetchApprovals();
        return;
      }

      // Handle non-communication tasks (e.g. dispatch_task)
      if (approval.action_type === 'dispatch_task') {
        addToast('success', 'Task Created', res.data.message || 'Task created successfully.');
        fetchApprovals();
        return;
      }

      const context = res.data?.context || {};
      const channel = res.data?.channel || context.communication_channel || 'email';
      const fallback = Boolean(res.data?.fallback);
      const fallbackReason = res.data?.fallback_reason;

      // Show fallback notification if channel was adjusted
      if (fallback && fallbackReason) {
        addToast('warning', 'Channel Fallback', fallbackReason);
      } else {
        const toastMsg = channel === 'sms'
          ? 'Action approved. Message is ready to review.'
          : 'Action approved. Email is ready to review.';
        addToast('success', 'Action Approved', res.data?.message || toastMsg);
      }

      // Automatically route user to Email Sender or Message Center
      if (channel === 'sms') {
        onNavigate('message_center', {
          ...context,
          approval_id: approval.id,
          customerId: context.customer_id
        });
      } else {
        onNavigate('email_assistant', {
          ...context,
          approval_id: approval.id,
          customerId: context.customer_id
        });
      }
    } catch (err) {
      console.error('Approval execution error:', err);
      const errMsg = err.response?.data?.detail || 'Failed to approve and prepare action.';
      addToast('error', 'Execution Error', errMsg);
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            Approval Center (Human-in-the-Loop AI)
            <Badge variant="ai">Multilingual Communication</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Review, edit, and approve AI-generated business actions. Sensitive operations are never executed without your sign-off.
          </p>
        </div>

        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-[#18181d] p-1 rounded-xl border border-slate-200 dark:border-[#26262c] self-start sm:self-auto">
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
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
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
            const isApproved = ['approved', 'communication_ready', 'sent', 'executed'].includes(app.status);
            const isRejected = app.status === 'rejected';
            const isSms = app.action_type === 'send_sms' || data.channel === 'sms';
            const lang = data.language || 'en';
            const langTag = lang === 'ta' ? 'தமிழ்' : (lang === 'en_ta' ? 'EN + தமிழ்' : 'English');

            return (
              <div
                key={app.id}
                className={`rounded-2xl border p-5 sm:p-6 transition-all ${
                  isPending
                    ? 'border-indigo-300 dark:border-indigo-500/40 bg-white dark:bg-[#141417] shadow-sm'
                    : isApproved
                    ? 'border-emerald-200 dark:border-emerald-500/30 bg-white dark:bg-[#141417]'
                    : 'border-slate-200 dark:border-[#26262c] bg-slate-50 dark:bg-[#141417] opacity-80'
                }`}
              >
                <div className="flex flex-col lg:flex-row lg:flex-wrap lg:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-[#26262c]">
                  <div className="flex items-start gap-3.5">
                    <div className="w-10 h-10 rounded-2xl bg-indigo-50 dark:bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center shrink-0">
                      {isSms ? <MessageSquare className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                          {isSms ? 'SMS Communication' : (app.action_type === 'send_payment_reminder' ? 'Email Payment Reminder' : app.action_type)}
                        </span>
                        <span className="px-2 py-0.5 rounded-md bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 text-[10px] font-bold uppercase border border-indigo-200 dark:border-indigo-500/30">
                          {langTag}
                        </span>
                        <Badge
                          variant={isPending ? 'warning' : (app.status === 'rejected' ? 'danger' : 'success')}
                        >
                          {app.status === 'communication_ready' ? 'READY TO REVIEW' : app.status.toUpperCase()}
                        </Badge>
                      </div>
                      <h3 className="text-base font-bold text-slate-900 dark:text-white mt-1">
                        Send {langTag} {isSms ? 'SMS' : 'Notice'} to {data.customer_name || 'Customer'}
                      </h3>
                    </div>
                  </div>

                  {/* Summary Badges */}
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    {data.invoice_number && (
                      <span className="px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-semibold">
                        Invoice: {data.invoice_number}
                      </span>
                    )}
                    {data.amount && (
                      <span className="px-2.5 py-1 rounded-xl bg-rose-50 dark:bg-rose-500/20 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 font-bold">
                        Amount: {formatMoney(data.amount)}
                      </span>
                    )}
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      Requested: {new Date(app.requested_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>

                {/* AI Recommendation Message */}
                {app.recommendation && (
                  <div className="mt-4 p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-500/20 flex items-start gap-2.5">
                    <Sparkles className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                    <div className="text-xs text-slate-700 dark:text-slate-200">
                      <strong className="text-indigo-700 dark:text-indigo-300">AI Recommendation: </strong>
                      {app.recommendation}
                    </div>
                  </div>
                )}

                {/* Generated Content Preview */}
                {(data.body || data.message) && (
                  <div className="mt-4 p-4 rounded-xl bg-slate-50 dark:bg-[#18181d] border border-slate-200 dark:border-[#26262c] space-y-2">
                    <div className="flex flex-wrap items-center justify-between text-xs text-slate-500 dark:text-slate-400 pb-2 border-b border-slate-200 dark:border-[#26262c] gap-2">
                      <span><strong>Recipient:</strong> {isSms ? (data.recipient_phone || data.phone || data.customer_phone) : (data.recipient_email || data.customer_email)}</span>
                      {!isSms && data.subject && <span><strong>Subject:</strong> {data.subject}</span>}
                    </div>
                    <p className="text-xs text-slate-800 dark:text-slate-200 whitespace-pre-wrap font-sans leading-relaxed">
                      {data.body || data.message}
                    </p>
                  </div>
                )}

                {/* Bottom Decision Actions */}
                {isPending && (
                  <div className="mt-5 pt-4 border-t border-slate-200 dark:border-[#26262c] flex flex-wrap items-center justify-between gap-3">
                    <div className="text-xs text-slate-500 dark:text-slate-400">
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
                        className="text-xs text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-500/10"
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
                        {actionLoadingId === app.id ? 'Approving and preparing action...' : 'Approve & Execute'}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Execution timestamp for already approved */}
                {isApproved && (
                  <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800 text-xs text-emerald-600 dark:text-emerald-400 flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      <Check className="w-4 h-4" />
                      <span>
                        {app.status === 'communication_ready'
                          ? `Approved on ${new Date(app.approved_at || app.requested_at).toLocaleString()} – Prepared for Review`
                          : `Approved & Sent on ${new Date(app.approved_at || app.requested_at).toLocaleString()}`}
                      </span>
                    </div>
                    {app.status === 'communication_ready' && (
                      <Button
                        onClick={() => handleApprove(app)}
                        variant="secondary"
                        size="xs"
                        className="text-xs"
                      >
                        Open {isSms ? 'Message Center' : 'Email Sender'} →
                      </Button>
                    )}
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
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                {editingApproval.action_type === 'send_sms' ? 'Recipient Phone Number' : 'Recipient Email'}
              </label>
              <input
                type={editingApproval.action_type === 'send_sms' ? 'tel' : 'email'}
                value={editRecipient}
                onChange={(e) => setEditRecipient(e.target.value)}
                required
                className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 font-mono"
              />
            </div>

            {editingApproval.action_type !== 'send_sms' && (
              <div>
                <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">Subject Line</label>
                <input
                  type="text"
                  value={editSubject}
                  onChange={(e) => setEditSubject(e.target.value)}
                  required
                  className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            )}

            <div>
              <label className="block font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Message Content (Supports English, தமிழ், and Bilingual UTF-8)
              </label>
              <textarea
                value={editBody}
                onChange={(e) => setEditBody(e.target.value)}
                rows={7}
                required
                className="w-full bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-xl p-3 text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500 font-sans leading-relaxed text-xs"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-slate-800">
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
                {actionLoadingId === editingApproval.id ? 'Approving and preparing action...' : 'Approve with Edits & Execute'}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default ApprovalsPage;
