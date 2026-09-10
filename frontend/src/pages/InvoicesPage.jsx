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
  RefreshCw
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
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 10;

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [viewInvoice, setViewInvoice] = useState(null);
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [quickCustomerModalOpen, setQuickCustomerModalOpen] = useState(false);
  const [quickCustomerSubmitting, setQuickCustomerSubmitting] = useState(false);
  const [quickCustomer, setQuickCustomer] = useState({
    name: '',
    email: '',
    phone: '',
    company: ''
  });

  // New Invoice Form state
  const [newInvoice, setNewInvoice] = useState({
    customer_id: '',
    invoice_number: `INV-${new Date().getFullYear()}${Math.floor(100 + Math.random() * 900)}`,
    amount: '',
    issue_date: new Date().toISOString().split('T')[0],
    due_date: new Date(Date.now() + 30 * 86400000).toISOString().split('T')[0],
    status: 'pending',
    notes: ''
  });

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

  const fetchCustomers = useCallback(async () => {
    try {
      const res = await api.get('/customers');
      setCustomers(res.data || []);
    } catch (err) {
      console.error('Error fetching customers:', err);
    }
  }, []);

  useEffect(() => {
    fetchInvoices();
  }, [fetchInvoices]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, searchQuery]);

  const handleQuickAddCustomer = async (e) => {
    e.preventDefault();
    if (!quickCustomer.name.trim() || !quickCustomer.email.trim()) {
      addToast('warning', 'Missing Details', 'Please provide a customer name and email.');
      return;
    }
    setQuickCustomerSubmitting(true);
    try {
      const payload = {
        name: quickCustomer.name.trim(),
        email: quickCustomer.email.trim(),
        phone: quickCustomer.phone?.trim() || '',
        company: quickCustomer.company?.trim() || quickCustomer.name.trim(),
        status: 'active'
      };
      const res = await api.post('/customers', payload);
      addToast('success', 'Customer Added', `Created profile for ${payload.name}.`);
      setCustomers((prev) => [...prev, res.data]);
      setNewInvoice((prev) => ({ ...prev, customer_id: String(res.data.id) }));
      setQuickCustomerModalOpen(false);
      setQuickCustomer({ name: '', email: '', phone: '', company: '' });
    } catch (err) {
      console.error('Quick customer add error:', err);
      const errMsg = err.response?.data?.detail || 'Failed to add customer.';
      addToast('error', 'Error', errMsg);
    } finally {
      setQuickCustomerSubmitting(false);
    }
  };

  const handleCreateInvoice = async (e) => {
    e.preventDefault();
    if (!newInvoice.customer_id || !newInvoice.amount) {
      addToast('warning', 'Missing Fields', 'Please select a customer and enter an amount.');
      return;
    }

    try {
      const payload = {
        ...newInvoice,
        customer_id: parseInt(newInvoice.customer_id),
        amount: parseFloat(newInvoice.amount),
        currency: business.currency || 'USD'
      };

      await api.post('/invoices', payload);
      addToast('success', 'Invoice Created', `Invoice ${newInvoice.invoice_number} generated.`);
      setCreateModalOpen(false);
      fetchInvoices();
    } catch (err) {
      addToast('error', 'Creation Error', 'Failed to create invoice.');
    }
  };

  const handleGenerateReminder = async (inv) => {
    setActionLoadingId(inv.id);
    try {
      await api.post(`/invoices/${inv.id}/reminder`);
      addToast('success', 'AI Reminder Drafted', `Reminder prepared for ${inv.customer_name} (${inv.invoice_number}). Routed to Approval Center.`);
      onNavigate('approvals');
    } catch (err) {
      addToast('error', 'Action Error', 'Could not draft reminder.');
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
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            Invoices & Billing
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Track receivables, monitor payment due dates, and generate automated AI payment reminders.
          </p>
        </div>

        <Button
          onClick={() => setCreateModalOpen(true)}
          variant="primary"
          size="sm"
          icon={Plus}
          className="text-xs self-start sm:self-auto"
        >
          Create Invoice
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white dark:bg-slate-900 p-3 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['all', 'overdue', 'pending', 'paid'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-colors cursor-pointer ${
                statusFilter === status
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              {status}
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
                <th className="p-3.5 font-bold uppercase tracking-wider">Amount</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Issue Date</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Due Date</th>
                <th className="p-3.5 font-bold uppercase tracking-wider">Status</th>
                <th className="p-3.5 font-bold uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12 text-slate-400">
                    <div className="flex flex-col items-center gap-2">
                      <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                      <span>Loading invoices...</span>
                    </div>
                  </td>
                </tr>
              ) : !filteredInvoices.length ? (
                <tr>
                  <td colSpan={7} className="p-8">
                    <EmptyState
                      icon={Receipt}
                      title="No invoices found"
                      description={statusFilter !== 'all' ? `No ${statusFilter} invoices found.` : "Upload a PDF document or click 'Create Invoice' above."}
                      actionText="Create Invoice"
                      onAction={() => setCreateModalOpen(true)}
                    />
                  </td>
                </tr>
              ) : (
                paginatedInvoices.map((inv) => {
                  const isOverdue = inv.status === 'overdue';
                  return (
                    <tr
                      key={inv.id}
                      onClick={() => setViewInvoice(inv)}
                      className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors cursor-pointer ${
                        isOverdue ? 'bg-rose-50/20 dark:bg-rose-950/10' : ''
                      }`}
                    >
                      <td className="p-3.5 font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        {inv.invoice_number}
                        {isOverdue && (
                          <span className="w-2 h-2 rounded-full bg-rose-500" />
                        )}
                      </td>
                      <td className="p-3.5">
                        <div className="font-semibold text-slate-800 dark:text-slate-200">{inv.customer_name}</div>
                        <div className="text-[10px] text-slate-400">{inv.customer_email}</div>
                      </td>
                      <td className="p-3.5 font-bold text-slate-900 dark:text-slate-100">
                        {formatMoney(inv.amount)}
                      </td>
                      <td className="p-3.5 text-slate-500 dark:text-slate-400">{inv.issue_date}</td>
                      <td className="p-3.5">
                        <span className={isOverdue ? 'text-rose-600 dark:text-rose-400 font-semibold' : 'text-slate-600 dark:text-slate-300'}>
                          {inv.due_date}
                        </span>
                      </td>
                      <td className="p-3.5">
                        <Badge variant={inv.status}>
                          {inv.status}
                        </Badge>
                      </td>
                      <td className="p-3.5 text-right space-x-1" onClick={(e) => e.stopPropagation()}>
                        {inv.status !== 'paid' && (
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

      {/* Create Invoice Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create New Invoice"
      >
        <form onSubmit={handleCreateInvoice} className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">Select Customer</label>
              <button
                type="button"
                onClick={() => setQuickCustomerModalOpen(true)}
                className="text-[11px] text-indigo-600 dark:text-indigo-400 hover:underline font-semibold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3 h-3" /> New Customer
              </button>
            </div>
            <select
              value={newInvoice.customer_id}
              onChange={(e) => setNewInvoice({ ...newInvoice, customer_id: e.target.value })}
              required
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="">-- Choose Customer --</option>
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.email})
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Invoice Number</label>
              <input
                type="text"
                value={newInvoice.invoice_number}
                onChange={(e) => setNewInvoice({ ...newInvoice, invoice_number: e.target.value })}
                required
                className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Amount ({business.currency})</label>
              <input
                type="number"
                step="0.01"
                value={newInvoice.amount}
                onChange={(e) => setNewInvoice({ ...newInvoice, amount: e.target.value })}
                placeholder="5000.00"
                required
                className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Issue Date</label>
              <input
                type="date"
                value={newInvoice.issue_date}
                onChange={(e) => setNewInvoice({ ...newInvoice, issue_date: e.target.value })}
                required
                className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Due Date</label>
              <input
                type="date"
                value={newInvoice.due_date}
                onChange={(e) => setNewInvoice({ ...newInvoice, due_date: e.target.value })}
                required
                className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Status</label>
            <select
              value={newInvoice.status}
              onChange={(e) => setNewInvoice({ ...newInvoice, status: e.target.value })}
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="pending">Pending</option>
              <option value="overdue">Overdue</option>
              <option value="paid">Paid</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Notes / Description</label>
            <textarea
              value={newInvoice.notes}
              onChange={(e) => setNewInvoice({ ...newInvoice, notes: e.target.value })}
              placeholder="Enterprise consulting retainer..."
              rows={3}
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
            <Button onClick={() => setCreateModalOpen(false)} variant="secondary" size="sm">
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm">
              Save Invoice
            </Button>
          </div>
        </form>
      </Modal>

      {/* View Invoice Modal */}
      {viewInvoice && (
        <Modal
          isOpen={Boolean(viewInvoice)}
          onClose={() => setViewInvoice(null)}
          title={`Invoice Details – ${viewInvoice.invoice_number}`}
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs">
              <div>
                <span className="text-slate-500 font-semibold block">Customer:</span>
                <span className="text-slate-900 dark:text-white font-bold text-sm">{viewInvoice.customer_name}</span>
                <span className="text-slate-500 block">{viewInvoice.customer_email}</span>
              </div>
              <div>
                <span className="text-slate-500 font-semibold block">Total Amount:</span>
                <span className="text-emerald-600 dark:text-emerald-400 font-bold text-base">{formatMoney(viewInvoice.amount)}</span>
                <Badge variant={viewInvoice.status} className="mt-1">{viewInvoice.status}</Badge>
              </div>
              <div>
                <span className="text-slate-500 font-semibold block">Issue Date:</span>
                <span className="text-slate-700 dark:text-slate-300">{viewInvoice.issue_date}</span>
              </div>
              <div>
                <span className="text-slate-500 font-semibold block">Payment Due:</span>
                <span className="text-rose-600 dark:text-rose-400 font-semibold">{viewInvoice.due_date}</span>
              </div>
            </div>

            {viewInvoice.notes && (
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300">
                <span className="font-semibold text-slate-500 block mb-1">Notes:</span>
                {viewInvoice.notes}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              {viewInvoice.status !== 'paid' && (
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
              )}
              <Button onClick={() => setViewInvoice(null)} variant="secondary" size="sm">
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Quick Add Customer Modal */}
      <Modal
        isOpen={quickCustomerModalOpen}
        onClose={() => setQuickCustomerModalOpen(false)}
        title="Quick Add Customer"
      >
        <form onSubmit={handleQuickAddCustomer} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Customer Name <span className="text-rose-500">*</span>
            </label>
            <input
              type="text"
              value={quickCustomer.name}
              onChange={(e) => setQuickCustomer({ ...quickCustomer, name: e.target.value })}
              placeholder="e.g. Acme Corp"
              required
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Email <span className="text-rose-500">*</span>
              </label>
              <input
                type="email"
                value={quickCustomer.email}
                onChange={(e) => setQuickCustomer({ ...quickCustomer, email: e.target.value })}
                placeholder="billing@acme.example"
                required
                className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Phone</label>
              <input
                type="text"
                value={quickCustomer.phone}
                onChange={(e) => setQuickCustomer({ ...quickCustomer, phone: e.target.value })}
                placeholder="+1 555 000 0000"
                className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Company</label>
            <input
              type="text"
              value={quickCustomer.company}
              onChange={(e) => setQuickCustomer({ ...quickCustomer, company: e.target.value })}
              placeholder="Acme Corporation"
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button
              onClick={() => setQuickCustomerModalOpen(false)}
              variant="secondary"
              size="sm"
              disabled={quickCustomerSubmitting}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={quickCustomerSubmitting}
              disabled={quickCustomerSubmitting}
            >
              {quickCustomerSubmitting ? 'Adding...' : 'Add & Select'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default InvoicesPage;
