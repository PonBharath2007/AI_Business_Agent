import React, { useState, useEffect, useCallback } from 'react';
import {
  Receipt,
  Plus,
  Search,
  AlertCircle,
  Clock,
  Sparkles,
  Eye,
  Trash2,
  RefreshCw,
  FileText,
  CreditCard,
  Building,
  Mail,
  Phone,
  Calendar,
  ExternalLink
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const InvoicesPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const [viewInvoice, setViewInvoice] = useState(null);
  const [actionLoadingId, setActionLoadingId] = useState(null);

  // Payment Recording State
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [paymentInvoice, setPaymentInvoice] = useState(null);
  const [paymentAmount, setPaymentAmount] = useState('');
  const [paymentNotes, setPaymentNotes] = useState('');
  const [paymentSubmitting, setPaymentSubmitting] = useState(false);

  const fetchInvoices = useCallback(async () => {
    try {
      const res = await api.get(`/invoices${statusFilter !== 'all' ? `?status=${statusFilter}` : ''}`);
      setInvoices(res.data || []);
    } catch (err) {
      console.error('Error fetching invoices:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, searchQuery]);

  const handleGenerateReminder = async (inv) => {
    setActionLoadingId(inv.id);
    try {
      await api.post(`/invoices/${inv.id}/reminder`);
      addToast(
        'success',
        'AI Reminder Drafted',
        `Reminder prepared for ${inv.customer_name} (${inv.invoice_number}). Routed to Approval Center.`
      );
      if (onNavigate) {
        onNavigate('approvals');
      }
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Could not draft reminder.';
      addToast('error', 'Action Error', errMsg);
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this invoice?')) return;
    try {
      await api.delete(`/invoices/${id}`);
      addToast('info', 'Invoice Deleted', 'Invoice was removed.');
      fetchInvoices();
    } catch (err) {
      addToast('error', 'Error', 'Failed to delete invoice.');
    }
  };

  const handleOpenPaymentModal = (inv) => {
    setPaymentInvoice(inv);
    const pend = inv.pending_amount !== undefined ? inv.pending_amount : Math.max(0, (inv.total_amount ?? inv.amount) - (inv.paid_amount || 0));
    setPaymentAmount(pend > 0 ? pend.toString() : '0');
    setPaymentNotes('');
    setPaymentModalOpen(true);
  };

  const handleRecordPayment = async (e) => {
    e.preventDefault();
    if (!paymentInvoice) return;
    const amountVal = parseFloat(paymentAmount);
    if (isNaN(amountVal) || amountVal <= 0) {
      addToast('warning', 'Invalid Amount', 'Payment amount must be greater than zero.');
      return;
    }
    const currentPend = paymentInvoice.pending_amount !== undefined ? paymentInvoice.pending_amount : Math.max(0, (paymentInvoice.total_amount ?? paymentInvoice.amount) - (paymentInvoice.paid_amount || 0));
    if (amountVal > currentPend && currentPend > 0) {
      addToast('warning', 'Exceeds Pending', `Payment (${formatMoney(amountVal)}) cannot exceed pending balance (${formatMoney(currentPend)}).`);
      return;
    }

    setPaymentSubmitting(true);
    try {
      const res = await api.post(`/invoices/${paymentInvoice.id}/payments`, {
        amount: amountVal,
        payment_date: new Date().toISOString().split('T')[0],
        notes: paymentNotes.trim() || undefined
      });

      addToast(
        'success',
        'Payment Recorded',
        `Recorded payment of ${formatMoney(amountVal)} against invoice ${paymentInvoice.invoice_number}! Pending balance: ${formatMoney(res.data.pending_amount)}`
      );

      setPaymentModalOpen(false);
      setPaymentInvoice(null);
      if (viewInvoice && viewInvoice.id === paymentInvoice.id) {
        setViewInvoice(res.data);
      }
      fetchInvoices();
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Failed to record payment.';
      addToast('error', 'Payment Error', errMsg);
    } finally {
      setPaymentSubmitting(false);
    }
  };

  const filteredInvoices = invoices.filter((inv) => {
    const query = searchQuery.toLowerCase();
    return (
      inv.invoice_number?.toLowerCase().includes(query) ||
      inv.customer_name?.toLowerCase().includes(query) ||
      inv.customer_company?.toLowerCase().includes(query)
    );
  });

  const totalPages = Math.max(1, Math.ceil(filteredInvoices.length / pageSize));
  const paginatedInvoices = filteredInvoices.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400">
              <Receipt className="w-5 h-5" />
            </span>
            Invoices
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Read, view, search, and manage generated and OCR-processed customer invoices.
          </p>
        </div>

        <Button
          onClick={() => (onNavigate ? onNavigate('billing') : null)}
          variant="primary"
          size="sm"
          icon={Plus}
          className="text-xs self-start sm:self-auto"
        >
          Create New Billing
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white dark:bg-slate-900 p-3 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['all', 'overdue', 'partially_paid', 'pending', 'paid'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-colors cursor-pointer whitespace-nowrap ${
                statusFilter === status
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {status.replace('_', ' ')}
            </button>
          ))}
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search invoice #, customer..."
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-4 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Invoice Table Card */}
      <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xs">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-slate-50 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                <th className="p-3.5 font-bold uppercase tracking-wider">Invoice #</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Customer</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Total</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Paid</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Pending</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Due Date</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Status</th>
                <th className="p-3.5 font-bold uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                      <span>Loading invoices...</span>
                    </div>
                  </td>
                </tr>
              ) : !filteredInvoices.length ? (
                <tr>
                  <td colSpan={8} className="p-8">
                    <EmptyState
                      icon={Receipt}
                      title="No invoices found"
                      description={
                        statusFilter !== 'all'
                          ? `No ${statusFilter.replace('_', ' ')} invoices found.`
                          : "Create a new billing or upload a document in Documents & OCR."
                      }
                      actionText="Create New Billing"
                      onAction={() => (onNavigate ? onNavigate('billing') : null)}
                    />
                  </td>
                </tr>
              ) : (
                paginatedInvoices.map((inv) => {
                  const isOverdue = inv.status === 'overdue';
                  const tot = inv.total_amount !== undefined ? inv.total_amount : (inv.amount || 0);
                  const paid = inv.paid_amount || 0;
                  const pending = inv.pending_amount !== undefined ? inv.pending_amount : Math.max(0, tot - paid);

                  return (
                    <tr
                      key={inv.id}
                      onClick={() => setViewInvoice(inv)}
                      className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors cursor-pointer ${
                        isOverdue ? 'bg-rose-50/20 dark:bg-rose-950/10' : ''
                      }`}
                    >
                      <td className="p-3.5 font-mono font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        {inv.invoice_number}
                        {isOverdue && <span className="w-2 h-2 rounded-full bg-rose-500" />}
                        {inv.document_id && (
                          <span className="px-1.5 py-0.2 rounded text-[9px] font-medium bg-slate-100 dark:bg-slate-800 text-slate-500">
                            OCR
                          </span>
                        )}
                      </td>
                      <td className="p-3.5">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">{inv.customer_name}</div>
                        <div className="text-[10px] text-slate-400">{inv.customer_email || 'No email provided'}</div>
                      </td>
                      <td className="p-3.5 font-bold text-slate-900 dark:text-slate-100">
                        {formatMoney(tot)}
                      </td>
                      <td className="p-3.5 font-semibold text-emerald-600 dark:text-emerald-400">
                        {formatMoney(paid)}
                      </td>
                      <td className="p-3.5 font-semibold text-rose-600 dark:text-rose-400">
                        {formatMoney(pending)}
                      </td>
                      <td className="p-3.5">
                        <span className={isOverdue ? 'text-rose-600 dark:text-rose-400 font-semibold' : 'text-slate-600 dark:text-slate-300'}>
                          {inv.due_date}
                        </span>
                      </td>
                      <td className="p-3.5">
                        <Badge variant={inv.status}>
                          {inv.payment_status || inv.status?.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td className="p-3.5 text-right space-x-1" onClick={(e) => e.stopPropagation()}>
                        {inv.status !== 'paid' && pending > 0 && (
                          <>
                            <Button
                              onClick={() => handleOpenPaymentModal(inv)}
                              variant="secondary"
                              size="sm"
                              icon={CreditCard}
                              className="text-xs"
                              title="Record payment against this invoice"
                            >
                              Record Payment
                            </Button>
                            <Button
                              onClick={() => handleGenerateReminder(inv)}
                              variant={isOverdue ? 'danger' : 'secondary'}
                              size="sm"
                              loading={actionLoadingId === inv.id}
                              icon={Sparkles}
                              className="text-xs"
                            >
                              AI Reminder
                            </Button>
                          </>
                        )}
                        <button
                          onClick={() => setViewInvoice(inv)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(inv.id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors cursor-pointer"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-3.5 border-t border-slate-200 dark:border-slate-800 text-xs">
            <span className="text-slate-500 dark:text-slate-400">
              Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, filteredInvoices.length)} of {filteredInvoices.length} invoices
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage === 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                Previous
              </Button>
              <span className="font-semibold text-slate-700 dark:text-slate-300 px-2">
                Page {currentPage} of {totalPages}
              </span>
              <Button
                variant="secondary"
                size="sm"
                disabled={currentPage === totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Invoice Details View Modal (Section 13) */}
      {viewInvoice && (
        <Modal
          isOpen={Boolean(viewInvoice)}
          onClose={() => setViewInvoice(null)}
          title={`Invoice Details – ${viewInvoice.invoice_number}`}
        >
          <div className="space-y-4">
            {/* Customer Details */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs">
              <div>
                <span className="text-slate-500 font-semibold block uppercase text-[10px]">Customer Details</span>
                <span className="text-slate-900 dark:text-white font-bold text-sm block mt-0.5">{viewInvoice.customer_name}</span>
                <div className="space-y-0.5 mt-1 text-slate-600 dark:text-slate-400">
                  {viewInvoice.customer_email && (
                    <div className="flex items-center gap-1.5">
                      <Mail className="w-3 h-3 text-slate-400" />
                      <span>{viewInvoice.customer_email}</span>
                    </div>
                  )}
                  {viewInvoice.customer_phone && (
                    <div className="flex items-center gap-1.5">
                      <Phone className="w-3 h-3 text-slate-400" />
                      <span>{viewInvoice.customer_phone}</span>
                    </div>
                  )}
                  {viewInvoice.customer_company && (
                    <div className="flex items-center gap-1.5">
                      <Building className="w-3 h-3 text-slate-400" />
                      <span>{viewInvoice.customer_company}</span>
                    </div>
                  )}
                </div>
              </div>

              <div>
                <span className="text-slate-500 font-semibold block uppercase text-[10px]">Invoice Schedule</span>
                <div className="mt-1 space-y-1 text-xs">
                  <div className="text-slate-700 dark:text-slate-300">
                    Invoice Number: <strong className="font-mono text-indigo-600 dark:text-indigo-400">{viewInvoice.invoice_number}</strong>
                  </div>
                  <div className="text-slate-700 dark:text-slate-300">
                    Invoice Date: <strong>{viewInvoice.issue_date}</strong>
                  </div>
                  <div className="text-rose-600 dark:text-rose-400">
                    Payment Due: <strong>{viewInvoice.due_date}</strong>
                  </div>
                  <div className="text-slate-700 dark:text-slate-300">
                    Currency: <strong className="text-indigo-600 dark:text-indigo-400">INR (₹)</strong>
                  </div>
                  {viewInvoice.document_id && (
                    <div className="pt-1">
                      <button
                        type="button"
                        onClick={() => {
                          setViewInvoice(null);
                          if (onNavigate) onNavigate('documents');
                        }}
                        className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-600 dark:text-indigo-400 hover:underline cursor-pointer"
                      >
                        <FileText className="w-3 h-3" /> View Source Document #{viewInvoice.document_id} &rarr;
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Line Items / Services Breakdown */}
            {viewInvoice.line_items && viewInvoice.line_items.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Billing Items & Services
                </span>
                <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden text-xs">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-800/80 text-slate-500 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200 dark:border-slate-800">
                        <th className="p-2.5">Item / Service</th>
                        <th className="p-2.5 w-16 text-center">Quantity</th>
                        <th className="p-2.5 w-24">Unit Price</th>
                        <th className="p-2.5 w-28 text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {viewInvoice.line_items.map((it, idx) => (
                        <tr key={idx}>
                          <td className="p-2.5 text-slate-900 dark:text-white font-medium">
                            {it.description || it.name || 'Service item'}
                          </td>
                          <td className="p-2.5 text-center text-slate-600 dark:text-slate-300">
                            {it.quantity || 1}
                          </td>
                          <td className="p-2.5 text-slate-600 dark:text-slate-300">
                            {formatMoney(it.unit_price || 0)}
                          </td>
                          <td className="p-2.5 text-right font-semibold text-slate-900 dark:text-white">
                            {formatMoney(it.total_price || (it.quantity || 1) * (it.unit_price || 0))}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* PAYMENT DETAILS */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-800 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700/60 pb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                  Payment Details
                </span>
                <Badge variant={viewInvoice.status}>
                  {viewInvoice.payment_status || viewInvoice.status?.replace('_', ' ')}
                </Badge>
              </div>

              {/* Subtotal, Tax, Discount */}
              <div className="grid grid-cols-3 gap-2 text-center text-xs border-b border-slate-200 dark:border-slate-700/60 pb-2">
                <div>
                  <span className="text-[10px] text-slate-500 block uppercase">Subtotal</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {formatMoney(viewInvoice.subtotal || viewInvoice.total_amount || viewInvoice.amount)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block uppercase">Tax / GST</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {formatMoney(viewInvoice.tax_amount || 0)}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 block uppercase">Discount</span>
                  <span className="font-semibold text-slate-800 dark:text-slate-200">
                    {formatMoney(viewInvoice.discount_amount || 0)}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                  <span className="text-[10px] text-slate-500 block font-semibold uppercase">Total Amount</span>
                  <span className="text-sm font-bold text-slate-900 dark:text-white mt-0.5 block">
                    {formatMoney(viewInvoice.total_amount ?? viewInvoice.amount)}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                  <span className="text-[10px] text-slate-500 block font-semibold uppercase">Paid Amount</span>
                  <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400 mt-0.5 block">
                    {formatMoney(viewInvoice.paid_amount || 0)}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                  <span className="text-[10px] text-slate-500 block font-semibold uppercase">Remaining Amount</span>
                  <span className="text-sm font-bold text-rose-600 dark:text-rose-400 mt-0.5 block">
                    {formatMoney(
                      viewInvoice.pending_amount !== undefined
                        ? viewInvoice.pending_amount
                        : Math.max(0, (viewInvoice.total_amount ?? viewInvoice.amount) - (viewInvoice.paid_amount || 0))
                    )}
                  </span>
                </div>
              </div>
            </div>

            {viewInvoice.notes && (
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300">
                <span className="font-semibold text-slate-500 block mb-1">Notes / Description:</span>
                <p className="whitespace-pre-line">{viewInvoice.notes}</p>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              {viewInvoice.status !== 'paid' && (
                (viewInvoice.pending_amount !== undefined
                  ? viewInvoice.pending_amount > 0
                  : ((viewInvoice.total_amount ?? viewInvoice.amount) - (viewInvoice.paid_amount || 0)) > 0)
              ) && (
                <>
                  <Button
                    onClick={() => {
                      handleOpenPaymentModal(viewInvoice);
                    }}
                    variant="primary"
                    size="sm"
                    icon={CreditCard}
                  >
                    Record Payment
                  </Button>
                  <Button
                    onClick={() => {
                      handleGenerateReminder(viewInvoice);
                      setViewInvoice(null);
                    }}
                    variant="danger"
                    size="sm"
                    icon={Sparkles}
                  >
                    Generate Reminder
                  </Button>
                </>
              )}
              <Button onClick={() => setViewInvoice(null)} variant="secondary" size="sm">
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Record Payment Modal */}
      {paymentModalOpen && paymentInvoice && (
        <Modal
          isOpen={paymentModalOpen}
          onClose={() => setPaymentModalOpen(false)}
          title={`Record Payment – ${paymentInvoice.invoice_number}`}
          maxWidth="max-w-md"
        >
          <form onSubmit={handleRecordPayment} className="space-y-4">
            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-slate-500">Customer:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200">{paymentInvoice.customer_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Total Invoice:</span>
                <span className="font-semibold">{formatMoney(paymentInvoice.total_amount ?? paymentInvoice.amount)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Currently Paid:</span>
                <span className="font-semibold text-emerald-600 dark:text-emerald-400">{formatMoney(paymentInvoice.paid_amount || 0)}</span>
              </div>
              <div className="flex justify-between font-bold pt-1 border-t border-slate-200 dark:border-slate-700">
                <span className="text-slate-700 dark:text-slate-300">Pending Balance:</span>
                <span className="text-amber-600 dark:text-amber-400">
                  {formatMoney(paymentInvoice.pending_amount !== undefined ? paymentInvoice.pending_amount : Math.max(0, (paymentInvoice.total_amount ?? paymentInvoice.amount) - (paymentInvoice.paid_amount || 0)))}
                </span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Payment Amount (₹) *
              </label>
              <input
                type="number"
                step="0.01"
                min="0.01"
                max={paymentInvoice.pending_amount !== undefined ? paymentInvoice.pending_amount : Math.max(0, (paymentInvoice.total_amount ?? paymentInvoice.amount) - (paymentInvoice.paid_amount || 0))}
                value={paymentAmount}
                onChange={(e) => setPaymentAmount(e.target.value)}
                required
                className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs font-mono font-bold text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Notes / Reference (Optional)
              </label>
              <input
                type="text"
                placeholder="e.g. Bank Transfer Ref #12345"
                value={paymentNotes}
                onChange={(e) => setPaymentNotes(e.target.value)}
                className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setPaymentModalOpen(false)}
                disabled={paymentSubmitting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                icon={CreditCard}
                loading={paymentSubmitting}
              >
                Confirm Payment
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};

export default InvoicesPage;
