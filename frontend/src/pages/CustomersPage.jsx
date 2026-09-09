import React, { useState, useEffect, useCallback } from 'react';
import {
  Users,
  Plus,
  Search,
  Mail,
  Phone,
  MessageSquare,
  Building,
  Receipt,
  ArrowRight,
  Sparkles,
  Trash2,
  Eye,
  Edit2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Clock,
  Send,
  ShieldCheck,
  BrainCircuit,
  Activity,
  History
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';
import CommunicationModal from '../components/common/CommunicationModal';

const CustomersPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 9;

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Communication Modal State
  const [commModalOpen, setCommModalOpen] = useState(false);
  const [selectedCommCustomer, setSelectedCommCustomer] = useState(null);
  const [commModalType, setCommModalType] = useState('email'); // 'email', 'sms', 'call'

  // Customer 360 Modal State
  const [customer360ModalOpen, setCustomer360ModalOpen] = useState(false);
  const [customer360Data, setCustomer360Data] = useState(null);
  const [loading360, setLoading360] = useState(false);
  const [customerCommunications, setCustomerCommunications] = useState([]);

  // Form state
  const [newCustomer, setNewCustomer] = useState({
    name: '',
    email: '',
    phone: '',
    company: '',
    status: 'active'
  });

  const [editCustomer, setEditCustomer] = useState({
    id: null,
    name: '',
    email: '',
    phone: '',
    company: '',
    status: 'active'
  });

  const fetchCustomers = useCallback(async () => {
    try {
      const res = await api.get('/customers');
      setCustomers(res.data || []);
    } catch (err) {
      console.error('Error fetching customers:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchCustomers();
  };

  const handleOpenCommunication = (customer, type = 'email') => {
    setSelectedCommCustomer(customer);
    setCommModalType(type);
    setCommModalOpen(true);
  };

  const handleOpenMessage = (customer) => {
    if (!customer?.phone || !customer.phone.trim()) {
      addToast('warning', 'Missing Phone', 'Phone number is not available for this customer.');
      return;
    }
    if (onNavigate) {
      onNavigate('message_center', { customerId: customer.id });
    } else {
      handleOpenCommunication(customer, 'sms');
    }
  };

  const handleOpen360 = async (customer) => {
    setCustomer360ModalOpen(true);
    setLoading360(true);
    setCustomer360Data(null);
    setCustomerCommunications([]);
    try {
      const [res360, resComm] = await Promise.all([
        api.get(`/intelligence/customer-360/${customer.id}`).catch(() => null),
        api.get(`/communications/customer/${customer.id}`).catch(() => ({ data: [] }))
      ]);

      if (res360?.data) {
        setCustomer360Data(res360.data);
      } else {
        setCustomer360Data({
          customer: { id: customer.id, name: customer.name, email: customer.email, company: customer.company || customer.name, phone: customer.phone },
          financials: { total_invoiced: customer.overdue_amount || 0, paid_amount: 0, overdue_amount: customer.overdue_amount || 0, currency: business.currency },
          behavior: { tag: customer.overdue_amount > 0 ? 'Frequently Delayed' : 'Active Account', badge: customer.overdue_amount > 0 ? 'warning' : 'success', score: 80, ai_insight: 'Standard account billing profile.', next_action: 'Monitor upcoming invoices.' },
          invoices: [],
          emails: [],
          tasks: [],
          ai_memories: []
        });
      }

      setCustomerCommunications(resComm.data || []);
    } catch (err) {
      console.error('Error fetching 360 data:', err);
    } finally {
      setLoading360(false);
    }
  };

  const handleInitiateCall = (customer) => {
    if (!customer?.phone || !customer.phone.trim()) {
      addToast('warning', 'Missing Phone', 'Phone number is not available for this customer.');
      return;
    }
    const cleanPhone = customer.phone.trim();
    api.post('/communications/call', {
      customer_id: customer.id,
      phone_number: cleanPhone
    }).catch((err) => console.warn('Call log note:', err));

    const sanitizedNumber = cleanPhone.replace(/[^0-9+]/g, '');
    window.location.href = `tel:${sanitizedNumber}`;
    addToast('info', 'Calling Customer', `Opening calling application for ${cleanPhone}.`);
  };

  const handleCreateCustomer = async (e) => {
    e.preventDefault();
    const name = newCustomer.name?.trim();
    const email = newCustomer.email?.trim() || '';
    const phone = newCustomer.phone?.trim() || '';

    if (!name) {
      addToast('warning', 'Missing Name', 'Please provide customer name.');
      return;
    }

    if (!email && !phone) {
      addToast('warning', 'Missing Contact Info', 'Please provide at least an email address or a phone number.');
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        name,
        email: email || null,
        phone: phone || null,
        company: newCustomer.company?.trim() || name,
        status: newCustomer.status || 'active'
      };

      await api.post('/customers', payload);
      addToast('success', 'Customer Created', `Profile for '${name}' added successfully.`);
      setCreateModalOpen(false);
      setNewCustomer({ name: '', email: '', phone: '', company: '', status: 'active' });
      fetchCustomers();
    } catch (err) {
      addToast('error', 'Creation Failed', 'Failed to create customer profile.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEditClick = (customer) => {
    setEditCustomer({
      id: customer.id,
      name: customer.name,
      email: customer.email,
      phone: customer.phone || '',
      company: customer.company || '',
      status: customer.status || 'active'
    });
    setEditModalOpen(true);
  };

  const handleUpdateCustomer = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.put(`/customers/${editCustomer.id}`, {
        name: editCustomer.name,
        email: editCustomer.email,
        phone: editCustomer.phone,
        company: editCustomer.company,
        status: editCustomer.status
      });
      addToast('success', 'Customer Updated', 'Profile updated successfully.');
      setEditModalOpen(false);
      fetchCustomers();
    } catch (err) {
      addToast('error', 'Update Failed', 'Failed to update customer profile.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id, customerName) => {
    if (!window.confirm(`Are you sure you want to delete ${customerName || 'this customer'}?`)) return;
    try {
      await api.delete(`/customers/${id}`);
      addToast('info', 'Customer Deleted', `Customer profile was removed.`);
      fetchCustomers();
    } catch (err) {
      addToast('error', 'Delete Failed', 'Failed to delete customer.');
    }
  };

  const filteredCustomers = customers.filter((c) => {
    const q = searchQuery.toLowerCase();
    return (
      c.name?.toLowerCase().includes(q) ||
      c.email?.toLowerCase().includes(q) ||
      c.company?.toLowerCase().includes(q) ||
      c.phone?.toLowerCase().includes(q)
    );
  });

  const totalPages = Math.max(1, Math.ceil(filteredCustomers.length / pageSize));
  const paginatedCustomers = filteredCustomers.slice((currentPage - 1) * pageSize, currentPage * pageSize);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            Customers
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Manage customer accounts with 1-click Email (SMTP), SMS, Call, and Customer 360° views.
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
            Refresh
          </Button>
          <Button
            onClick={() => setCreateModalOpen(true)}
            variant="primary"
            size="sm"
            icon={Plus}
            className="text-xs"
          >
            Add Customer
          </Button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="bg-white dark:bg-slate-900 p-3 rounded-2xl border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3 shadow-xs">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, company, email, phone..."
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-4 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <span className="text-xs text-slate-500 dark:text-slate-400 hidden sm:inline">
          Showing <strong>{paginatedCustomers.length}</strong> of <strong>{filteredCustomers.length}</strong> accounts
        </span>
      </div>

      {/* Customers Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full flex flex-col items-center justify-center py-16 text-slate-400 space-y-3">
            <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-xs">Loading customer directory...</p>
          </div>
        ) : !filteredCustomers.length ? (
          <div className="col-span-full">
            <EmptyState
              icon={Users}
              title="No customers found"
              description="Add a new customer profile or upload an invoice to auto-extract customer accounts."
              actionText="Add Customer"
              onAction={() => setCreateModalOpen(true)}
            />
          </div>
        ) : (
          paginatedCustomers.map((cust) => {
            const hasOverdue = (cust.overdue_amount || 0) > 0;
            return (
              <div
                key={cust.id}
                className="bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-500/40 transition-all flex flex-col justify-between space-y-4 shadow-xs"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate">{cust.name}</h3>
                      <p className="text-xs text-slate-500 dark:text-slate-400 truncate flex items-center gap-1 mt-0.5">
                        <Building className="w-3 h-3 text-slate-400" />
                        {cust.company || 'Direct Client'}
                      </p>
                    </div>
                    <Badge variant={hasOverdue ? 'urgent' : 'success'}>
                      {hasOverdue ? 'Overdue' : 'Good Standing'}
                    </Badge>
                  </div>

                  <div className="mt-3.5 space-y-1.5 text-xs text-slate-600 dark:text-slate-300">
                    <div className="flex items-center gap-2 truncate">
                      <Mail className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span className="truncate">{cust.email || 'No email'}</span>
                    </div>
                    {cust.phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                        <span>{cust.phone}</span>
                      </div>
                    )}
                  </div>

                  {/* Financial Stats strip */}
                  <div className="mt-3.5 pt-3 border-t border-slate-100 dark:border-slate-800 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-[10px] text-slate-400 block">Total Invoices</span>
                      <span className="font-semibold text-slate-800 dark:text-slate-200">{cust.total_invoices || 0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-400 block">Overdue Balance</span>
                      <span className={`font-bold ${hasOverdue ? 'text-rose-600 dark:text-rose-400' : 'text-slate-500 dark:text-slate-400'}`}>
                        {formatMoney(cust.overdue_amount || 0)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Communication Action Buttons Strip */}
                <div className="space-y-2 pt-2 border-t border-slate-100 dark:border-slate-800">
                  <div className="grid grid-cols-3 gap-1.5">
                    {/* [ Email ] */}
                    <button
                      type="button"
                      disabled={!cust.email || !cust.email.includes('@')}
                      onClick={() => handleOpenCommunication(cust, 'email')}
                      className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-xl text-xs font-semibold transition-all ${
                        cust.email && cust.email.includes('@')
                          ? 'bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-indigo-500 text-slate-700 dark:text-slate-200 hover:text-indigo-600 dark:hover:text-white cursor-pointer'
                          : 'bg-slate-100/50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-400 opacity-50 cursor-not-allowed'
                      }`}
                      title={cust.email && cust.email.includes('@') ? `Email ${cust.email}` : 'Email not available'}
                    >
                      <Mail className="w-3.5 h-3.5 text-indigo-500" />
                      <span>Email</span>
                    </button>

                    {/* [ Phone ] */}
                    <button
                      type="button"
                      disabled={!cust.phone || !cust.phone.trim()}
                      onClick={() => handleInitiateCall(cust)}
                      className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-xl text-xs font-semibold transition-all ${
                        cust.phone && cust.phone.trim()
                          ? 'bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-amber-500 text-slate-700 dark:text-slate-200 hover:text-amber-600 dark:hover:text-white cursor-pointer'
                          : 'bg-slate-100/50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-400 opacity-50 cursor-not-allowed'
                      }`}
                      title={cust.phone && cust.phone.trim() ? `Call ${cust.phone}` : 'Phone number not available'}
                    >
                      <Phone className="w-3.5 h-3.5 text-amber-500" />
                      <span>Phone</span>
                    </button>

                    {/* [ Message ] */}
                    <button
                      type="button"
                      disabled={!cust.phone || !cust.phone.trim()}
                      onClick={() => handleOpenMessage(cust)}
                      className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-xl text-xs font-semibold transition-all ${
                        cust.phone && cust.phone.trim()
                          ? 'bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-emerald-500 text-slate-700 dark:text-slate-200 hover:text-emerald-600 dark:hover:text-white cursor-pointer'
                          : 'bg-slate-100/50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-400 opacity-50 cursor-not-allowed'
                      }`}
                      title={cust.phone && cust.phone.trim() ? `Open Message Center for ${cust.name}` : 'Phone number not available'}
                    >
                      <MessageSquare className="w-3.5 h-3.5 text-emerald-500" />
                      <span>SMS</span>
                    </button>
                  </div>
                </div>

                {/* Bottom Tools */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-100 dark:border-slate-800">
                  <Button
                    onClick={() => handleOpen360(cust)}
                    variant="ghost"
                    size="sm"
                    icon={BrainCircuit}
                    className="text-xs font-semibold text-indigo-600 dark:text-indigo-400"
                  >
                    Customer 360°
                  </Button>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleEditClick(cust)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      title="Edit Profile"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(cust.id, cust.name)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                      title="Delete Profile"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-slate-200 dark:border-slate-800 text-xs">
          <span className="text-slate-500 dark:text-slate-400">
            Showing {(currentPage - 1) * pageSize + 1}–{Math.min(currentPage * pageSize, filteredCustomers.length)} of {filteredCustomers.length}
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

      {/* Customer 360 Deep-Dive Modal */}
      {customer360ModalOpen && (
        <Modal
          isOpen={customer360ModalOpen}
          onClose={() => setCustomer360ModalOpen(false)}
          title={`Customer 360°: ${customer360Data?.customer?.name || 'Loading...'}`}
          maxWidth="max-w-3xl"
        >
          {loading360 ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-slate-500">Synthesizing 360° profile...</p>
            </div>
          ) : !customer360Data ? (
            <div className="text-center py-8 text-xs text-slate-500">Failed to load customer details.</div>
          ) : (
            <div className="space-y-4 text-xs">
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-750 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-indigo-100 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 flex items-center justify-center font-bold text-sm">
                    {customer360Data.behavior.score}
                  </div>
                  <div>
                    <span className="text-sm font-bold text-slate-900 dark:text-white block">{customer360Data.customer.name}</span>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {customer360Data.customer.company} • {customer360Data.customer.email}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    onClick={() => {
                      setCustomer360ModalOpen(false);
                      handleOpenCommunication(customer360Data.customer, 'email');
                    }}
                    disabled={!customer360Data.customer.email || !customer360Data.customer.email.includes('@')}
                    variant="secondary"
                    size="sm"
                    icon={Mail}
                  >
                    Email
                  </Button>
                  <Button
                    onClick={() => {
                      setCustomer360ModalOpen(false);
                      handleOpenCommunication(customer360Data.customer, 'sms');
                    }}
                    disabled={!customer360Data.customer.phone || !customer360Data.customer.phone.trim()}
                    variant="secondary"
                    size="sm"
                    icon={MessageSquare}
                  >
                    SMS
                  </Button>
                </div>
              </div>

              {/* Financial Breakdown Tiles */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] uppercase text-slate-500">Total Billed</span>
                  <p className="text-sm font-bold text-slate-900 dark:text-white mt-1">
                    {formatMoney(customer360Data.financials.total_invoiced)}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] uppercase text-slate-500">Total Paid</span>
                  <p className="text-sm font-bold text-emerald-600 dark:text-emerald-400 mt-1">
                    {formatMoney(customer360Data.financials.paid_amount)}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] uppercase text-slate-500">Pending</span>
                  <p className="text-sm font-bold text-amber-600 dark:text-amber-400 mt-1">
                    {formatMoney(customer360Data.financials.pending_amount)}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] uppercase text-slate-500">Overdue</span>
                  <p className="text-sm font-bold text-rose-600 dark:text-rose-400 mt-1">
                    {formatMoney(customer360Data.financials.overdue_amount)}
                  </p>
                </div>
              </div>

              {/* Invoices Timeline */}
              <div>
                <h4 className="font-bold text-slate-900 dark:text-white text-xs mb-2">
                  Invoices ({customer360Data.invoices?.length || 0})
                </h4>
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {!customer360Data.invoices?.length ? (
                    <p className="text-slate-500 text-[11px] py-2">No invoices recorded for this account.</p>
                  ) : (
                    customer360Data.invoices.map((inv) => (
                      <div
                        key={inv.id}
                        className="p-2 rounded-lg bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800 flex items-center justify-between text-[11px]"
                      >
                        <span className="font-bold text-slate-900 dark:text-white">{inv.invoice_number}</span>
                        <span className="text-slate-500">Due: {inv.due_date || 'N/A'}</span>
                        <span className="font-semibold">{formatMoney(inv.amount)}</span>
                        <Badge variant={inv.status}>
                          {inv.status?.toUpperCase()}
                        </Badge>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </Modal>
      )}

      {/* Create Customer Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Create New Customer"
        maxWidth="max-w-md"
      >
        <form onSubmit={handleCreateCustomer} className="space-y-3.5">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Customer / Contact Name *
            </label>
            <input
              type="text"
              value={newCustomer.name}
              onChange={(e) => setNewCustomer({ ...newCustomer, name: e.target.value })}
              placeholder="e.g. Acme Corp or Jane Doe"
              required
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={newCustomer.email}
              onChange={(e) => setNewCustomer({ ...newCustomer, email: e.target.value })}
              placeholder="customer@example.com"
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Phone Number
            </label>
            <input
              type="text"
              value={newCustomer.phone}
              onChange={(e) => setNewCustomer({ ...newCustomer, phone: e.target.value })}
              placeholder="+1-555-0199 or +91 9876543210"
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Company Name
            </label>
            <input
              type="text"
              value={newCustomer.company}
              onChange={(e) => setNewCustomer({ ...newCustomer, company: e.target.value })}
              placeholder="Leave blank to use customer name"
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setCreateModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={submitting}
            >
              Save Profile
            </Button>
          </div>
        </form>
      </Modal>

      {/* Edit Customer Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Edit Customer Profile"
        maxWidth="max-w-md"
      >
        <form onSubmit={handleUpdateCustomer} className="space-y-3.5">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Customer Name *
            </label>
            <input
              type="text"
              value={editCustomer.name}
              onChange={(e) => setEditCustomer({ ...editCustomer, name: e.target.value })}
              required
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Email Address
            </label>
            <input
              type="email"
              value={editCustomer.email}
              onChange={(e) => setEditCustomer({ ...editCustomer, email: e.target.value })}
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Phone Number
            </label>
            <input
              type="text"
              value={editCustomer.phone}
              onChange={(e) => setEditCustomer({ ...editCustomer, phone: e.target.value })}
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
              Company
            </label>
            <input
              type="text"
              value={editCustomer.company}
              onChange={(e) => setEditCustomer({ ...editCustomer, company: e.target.value })}
              className="w-full bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setEditModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={submitting}
            >
              Update Profile
            </Button>
          </div>
        </form>
      </Modal>

      {/* Multilingual Communication Modal */}
      {commModalOpen && selectedCommCustomer && (
        <CommunicationModal
          isOpen={commModalOpen}
          onClose={() => setCommModalOpen(false)}
          customer={selectedCommCustomer}
          initialType={commModalType}
          onSuccess={() => fetchCustomers()}
        />
      )}
    </div>
  );
};

export default CustomersPage;
