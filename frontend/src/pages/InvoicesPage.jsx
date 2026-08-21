import React, { useState, useEffect, useCallback } from 'react';
import {
  Receipt,
  Plus,
  Search,
  Filter,
  AlertCircle,
  CheckCircle2,
  Clock,
  Send,
  Trash2,
  Eye,
  Sparkles,
  ArrowUpDown
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

  const fetchData = useCallback(async () => {
    try {
      const [invRes, custRes] = await Promise.all([
        api.get(`/invoices${statusFilter !== 'all' ? `?status=${statusFilter}` : ''}`),
        api.get('/customers')
      ]);
      setInvoices(invRes.data || []);
      setCustomers(custRes.data || []);
    } catch (err) {
      console.error('Error fetching invoices:', err);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
      fetchData();
    } catch (err) {
      addToast('error', 'Creation Error', 'Failed to create invoice.');
    }
  };


  const handleGenerateReminder = async (inv) => {
    setActionLoadingId(inv.id);
    try {
      const res = await api.post(`/invoices/${inv.id}/reminder`);
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
      fetchData();
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Invoice Management & Overdue Tracking
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
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
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 glass-panel p-3 rounded-2xl border border-slate-800">
        {/* Status Filter Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          {['all', 'overdue', 'pending', 'paid'].map((status) => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold uppercase tracking-wider transition-all ${
                statusFilter === status
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
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
            placeholder="Search invoice # or customer..."
            className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Invoices Table */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="p-4">Invoice #</th>
                <th className="p-4">Customer</th>
                <th className="p-4">Amount</th>
                <th className="p-4">Issue Date</th>
                <th className="p-4">Due Date</th>
                <th className="p-4">Status</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 bg-slate-900/40">
              {!filteredInvoices.length ? (
                <tr>
                  <td colSpan="7" className="p-8 text-center text-slate-400">
                    No invoices found for the selected criteria.
                  </td>
                </tr>
              ) : (
                filteredInvoices.map((inv) => {
                  const isOverdue = inv.status === 'overdue';

                  return (
                    <tr
                      key={inv.id}
                      className={`hover:bg-slate-800/40 transition-colors ${
                        isOverdue ? 'bg-rose-950/10' : ''
                      }`}
                    >
                      <td className="p-4 font-bold text-white flex items-center gap-2">
                        {inv.invoice_number}
                        {isOverdue && (
                          <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                        )}
                      </td>
                      <td className="p-4">
                        <div className="font-semibold text-slate-200">{inv.customer_name}</div>
                        <div className="text-[10px] text-slate-400">{inv.customer_email}</div>
                      </td>
                      <td className="p-4 font-bold text-slate-100 text-sm">
                        {formatMoney(inv.amount)}
                      </td>
                      <td className="p-4 text-slate-400">{inv.issue_date}</td>
                      <td className="p-4">
                        <span className={isOverdue ? 'text-rose-400 font-semibold' : 'text-slate-300'}>
                          {inv.due_date}
                        </span>
                      </td>
                      <td className="p-4">
                        <Badge variant={inv.status}>
                          {inv.status}
                        </Badge>
                      </td>
                      <td className="p-4 text-right space-x-1.5" onClick={(e) => e.stopPropagation()}>
                        {/* 1-Click Reminder Trigger for Overdue / Pending */}
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
                          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                          title="View Details"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleDelete(inv.id)}
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
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
              <label className="block text-xs font-semibold text-slate-300">Select Customer</label>
              <button
                type="button"
                onClick={() => setQuickCustomerModalOpen(true)}
                className="text-[11px] text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1 cursor-pointer"
              >
                <Plus className="w-3 h-3" /> New Customer
              </button>
            </div>
            <select
              value={newInvoice.customer_id}
              onChange={(e) => setNewInvoice({ ...newInvoice, customer_id: e.target.value })}
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
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
              <label className="block text-xs font-semibold text-slate-300 mb-1">Invoice Number</label>
              <input
                type="text"
                value={newInvoice.invoice_number}
                onChange={(e) => setNewInvoice({ ...newInvoice, invoice_number: e.target.value })}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Amount ({business.currency})</label>
              <input
                type="number"
                step="0.01"
                value={newInvoice.amount}
                onChange={(e) => setNewInvoice({ ...newInvoice, amount: e.target.value })}
                placeholder="5000.00"
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Issue Date</label>
              <input
                type="date"
                value={newInvoice.issue_date}
                onChange={(e) => setNewInvoice({ ...newInvoice, issue_date: e.target.value })}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Due Date</label>
              <input
                type="date"
                value={newInvoice.due_date}
                onChange={(e) => setNewInvoice({ ...newInvoice, due_date: e.target.value })}
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Status</label>
            <select
              value={newInvoice.status}
              onChange={(e) => setNewInvoice({ ...newInvoice, status: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="pending">Pending</option>
              <option value="overdue">Overdue</option>
              <option value="paid">Paid</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Notes / Description</label>
            <textarea
              value={newInvoice.notes}
              onChange={(e) => setNewInvoice({ ...newInvoice, notes: e.target.value })}
              placeholder="Enterprise consulting retainer..."
              rows={3}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
            <Button onClick={() => setCreateModalOpen(false)} variant="ghost" size="sm">
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
            <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs">
              <div>
                <span className="text-slate-400 font-semibold block">Customer:</span>
                <span className="text-white font-bold text-sm">{viewInvoice.customer_name}</span>
                <span className="text-slate-400 block">{viewInvoice.customer_email}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Total Amount:</span>
                <span className="text-emerald-400 font-bold text-base">{formatMoney(viewInvoice.amount)}</span>
                <Badge variant={viewInvoice.status} className="mt-1">{viewInvoice.status}</Badge>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Issue Date:</span>
                <span className="text-slate-200">{viewInvoice.issue_date}</span>
              </div>
              <div>
                <span className="text-slate-400 font-semibold block">Payment Due:</span>
                <span className="text-rose-400 font-semibold">{viewInvoice.due_date}</span>
              </div>
            </div>

            {viewInvoice.notes && (
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-300">
                <span className="font-semibold text-slate-400 block mb-1">Notes:</span>
                {viewInvoice.notes}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
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
                  Generate Payment Reminder
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
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Customer Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={quickCustomer.name}
              onChange={(e) => setQuickCustomer({ ...quickCustomer, name: e.target.value })}
              placeholder="e.g. Acme Corp"
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Email <span className="text-rose-400">*</span>
              </label>
              <input
                type="email"
                value={quickCustomer.email}
                onChange={(e) => setQuickCustomer({ ...quickCustomer, email: e.target.value })}
                placeholder="billing@acme.example"
                required
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Phone</label>
              <input
                type="text"
                value={quickCustomer.phone}
                onChange={(e) => setQuickCustomer({ ...quickCustomer, phone: e.target.value })}
                placeholder="+1 555 000 0000"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Company</label>
            <input
              type="text"
              value={quickCustomer.company}
              onChange={(e) => setQuickCustomer({ ...quickCustomer, company: e.target.value })}
              placeholder="Acme Corporation"
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
            />
          </div>
          <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
            <Button
              onClick={() => setQuickCustomerModalOpen(false)}
              variant="ghost"
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

