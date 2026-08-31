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

  const handleRefresh = () => {
    setRefreshing(true);
    fetchCustomers();
  };

  const handleOpenCommunication = (customer, type = 'email') => {
    setSelectedCommCustomer(customer);
    setCommModalType(type);
    setCommModalOpen(true);
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
    // Fire and forget server-side call logging
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Customers & Multilingual Communication
            <Badge variant="ai">EN • தமிழ் • EN+TA</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
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
      <div className="glass-panel p-3 rounded-2xl border border-slate-800 flex items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, company, email, phone..."
            className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-9 pr-4 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <span className="text-xs text-slate-400 hidden sm:inline">
          Showing <strong>{filteredCustomers.length}</strong> of <strong>{customers.length}</strong> clients
        </span>
      </div>

      {/* Customers Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-full flex flex-col items-center justify-center py-16 text-slate-400 space-y-3">
            <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
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
          filteredCustomers.map((cust) => {
            const hasOverdue = (cust.overdue_amount || 0) > 0;
            return (
              <div
                key={cust.id}
                className="glass-panel rounded-2xl p-5 border border-slate-800 hover:border-indigo-500/40 transition-all flex flex-col justify-between space-y-4"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h3 className="text-sm font-bold text-white truncate">{cust.name}</h3>
                      <p className="text-xs text-slate-400 truncate flex items-center gap-1 mt-0.5">
                        <Building className="w-3 h-3 text-slate-500" />
                        {cust.company || 'Direct Client'}
                      </p>
                    </div>
                    <Badge variant={hasOverdue ? 'urgent' : 'success'}>
                      {hasOverdue ? 'Overdue' : 'Good Standing'}
                    </Badge>
                  </div>

                  <div className="mt-3.5 space-y-1.5 text-xs text-slate-300">
                    <div className="flex items-center gap-2 truncate">
                      <Mail className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                      <span className="truncate text-slate-300">{cust.email || 'No email'}</span>
                    </div>
                    {cust.phone && (
                      <div className="flex items-center gap-2">
                        <Phone className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                        <span>{cust.phone}</span>
                      </div>
                    )}
                  </div>

                  {/* Financial Stats strip */}
                  <div className="mt-3.5 pt-3 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <span className="text-[10px] text-slate-500 block">Total Invoices</span>
                      <span className="font-semibold text-slate-200">{cust.total_invoices || 0}</span>
                    </div>
                    <div>
                      <span className="text-[10px] text-slate-500 block">Overdue Balance</span>
                      <span className={`font-bold ${hasOverdue ? 'text-rose-400' : 'text-slate-400'}`}>
                        {formatMoney(cust.overdue_amount || 0)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Communication Action Buttons Strip */}
                <div className="space-y-2 pt-2 border-t border-slate-800/80">
                  <div className="flex items-center justify-between text-[11px] text-slate-400 font-bold uppercase tracking-wider">
                    <span>Communication</span>
                    <span className="text-[10px] text-indigo-400 normal-case font-normal">Multilingual AI</span>
                  </div>

                  <div className="grid grid-cols-3 gap-1.5">
                    {/* [ Email ] */}
                    <button
                      type="button"
                      disabled={!cust.email || !cust.email.includes('@')}
                      onClick={() => handleOpenCommunication(cust, 'email')}
                      className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-xl text-xs font-semibold transition-all shadow-sm ${
                        cust.email && cust.email.includes('@')
                          ? 'bg-slate-900 border border-slate-700/80 hover:border-indigo-500 text-slate-200 hover:text-white cursor-pointer'
                          : 'bg-slate-950/60 border border-slate-800/70 text-slate-500 opacity-50 cursor-not-allowed'
                      }`}
                      title={cust.email && cust.email.includes('@') ? `Email ${cust.email}` : 'Email not available'}
                    >
                      <Mail className={`w-3.5 h-3.5 ${cust.email && cust.email.includes('@') ? 'text-indigo-400' : 'text-slate-500'}`} />
                      <span>Email</span>
                    </button>

                    {/* [ Phone ] */}
                    <button
                      type="button"
                      disabled={!cust.phone || !cust.phone.trim()}
                      onClick={() => handleInitiateCall(cust)}
                      className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-xl text-xs font-semibold transition-all shadow-sm ${
                        cust.phone && cust.phone.trim()
                          ? 'bg-slate-900 border border-slate-700/80 hover:border-amber-500 text-slate-200 hover:text-white cursor-pointer'
                          : 'bg-slate-950/60 border border-slate-800/70 text-slate-500 opacity-50 cursor-not-allowed'
                      }`}
                      title={cust.phone && cust.phone.trim() ? `Call ${cust.phone} (tel:)` : 'Phone number not available'}
                    >
                      <Phone className={`w-3.5 h-3.5 ${cust.phone && cust.phone.trim() ? 'text-amber-400' : 'text-slate-500'}`} />
                      <span>Phone</span>
                    </button>

                    {/* [ Message ] */}
                    <button
                      type="button"
                      disabled={!cust.phone || !cust.phone.trim()}
                      onClick={() => handleOpenCommunication(cust, 'sms')}
                      className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-xl text-xs font-semibold transition-all shadow-sm ${
                        cust.phone && cust.phone.trim()
                          ? 'bg-slate-900 border border-slate-700/80 hover:border-emerald-500 text-slate-200 hover:text-white cursor-pointer'
                          : 'bg-slate-950/60 border border-slate-800/70 text-slate-500 opacity-50 cursor-not-allowed'
                      }`}
                      title={cust.phone && cust.phone.trim() ? `Send Message / SMS to ${cust.phone}` : 'Phone number not available'}
                    >
                      <MessageSquare className={`w-3.5 h-3.5 ${cust.phone && cust.phone.trim() ? 'text-emerald-400' : 'text-slate-500'}`} />
                      <span>Message</span>
                    </button>
                  </div>

                  {!cust.email && !cust.phone && (
                    <p className="text-[10px] text-amber-400/90 text-center font-medium pt-0.5">
                      No communication details available for this customer.
                    </p>
                  )}
                </div>

                {/* Bottom Tools */}
                <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
                  <Button
                    onClick={() => handleOpen360(cust)}
                    variant="primary"
                    size="sm"
                    icon={BrainCircuit}
                    className="text-xs font-semibold"
                  >
                    Customer 360°
                  </Button>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => handleEditClick(cust)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                      title="Edit Profile"
                    >
                      <Edit2 className="w-3.5 h-3.5" />
                    </button>
                    <button
                      onClick={() => handleDelete(cust.id, cust.name)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition-colors"
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

      {/* Customer 360 Deep-Dive Modal */}
      {customer360ModalOpen && (
        <Modal
          isOpen={customer360ModalOpen}
          onClose={() => setCustomer360ModalOpen(false)}
          title={`Customer 360° View: ${customer360Data?.customer?.name || 'Loading...'}`}
          maxWidth="max-w-4xl"
        >
          {loading360 ? (
            <div className="py-16 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
              <p className="text-xs text-slate-400">Synthesizing 360° behavioral timeline...</p>
            </div>
          ) : !customer360Data ? (
            <div className="text-center py-8 text-xs text-slate-400">Failed to load customer details.</div>
          ) : (
            <div className="space-y-4 text-xs">
              {/* Top Banner: Behavioral Tag & Score */}
              <div className="p-4 rounded-2xl bg-gradient-to-r from-indigo-950/50 via-slate-900 to-slate-900 border border-indigo-500/30 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center font-bold text-white text-lg">
                    {customer360Data.behavior.score}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-white">{customer360Data.customer.name}</span>
                      <Badge variant={customer360Data.behavior.badge || 'ai'}>
                        {customer360Data.behavior.tag}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      {customer360Data.customer.company} • {customer360Data.customer.email} • {customer360Data.customer.phone || 'No phone'}
                    </p>
                  </div>
                </div>

                {/* Quick 1-Click Multilingual Communication Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    onClick={() => {
                      setCustomer360ModalOpen(false);
                      handleOpenCommunication(customer360Data.customer, 'email');
                    }}
                    disabled={!customer360Data.customer.email || !customer360Data.customer.email.includes('@')}
                    title={customer360Data.customer.email ? `Email ${customer360Data.customer.email}` : 'Email not available'}
                    variant="secondary"
                    size="sm"
                    icon={Mail}
                  >
                    Email
                  </Button>
                  <Button
                    onClick={() => {
                      handleInitiateCall(customer360Data.customer);
                    }}
                    disabled={!customer360Data.customer.phone || !customer360Data.customer.phone.trim()}
                    title={customer360Data.customer.phone ? `Call ${customer360Data.customer.phone} (tel:)` : 'Phone number not available'}
                    variant="secondary"
                    size="sm"
                    icon={Phone}
                  >
                    Phone
                  </Button>
                  <Button
                    onClick={() => {
                      setCustomer360ModalOpen(false);
                      handleOpenCommunication(customer360Data.customer, 'sms');
                    }}
                    disabled={!customer360Data.customer.phone || !customer360Data.customer.phone.trim()}
                    title={customer360Data.customer.phone ? `Send Message to ${customer360Data.customer.phone}` : 'Phone number not available'}
                    variant="secondary"
                    size="sm"
                    icon={MessageSquare}
                  >
                    Message
                  </Button>
                </div>
              </div>

              {/* Financial Breakdown Tiles */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase text-slate-400">Total Billed</span>
                  <p className="text-sm font-bold text-white mt-1">
                    {formatMoney(customer360Data.financials.total_invoiced)}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase text-slate-400">Total Paid</span>
                  <p className="text-sm font-bold text-emerald-400 mt-1">
                    {formatMoney(customer360Data.financials.paid_amount)}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase text-slate-400">Pending Amount</span>
                  <p className="text-sm font-bold text-amber-400 mt-1">
                    {formatMoney(customer360Data.financials.pending_amount)}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  <span className="text-[10px] uppercase text-slate-400">Overdue Balance</span>
                  <p className="text-sm font-bold text-rose-400 mt-1">
                    {formatMoney(customer360Data.financials.overdue_amount)}
                  </p>
                </div>
              </div>

              {/* AI Insight & Action Strip */}
              <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 space-y-2">
                <div className="flex items-center gap-1.5 text-indigo-300 font-bold text-xs">
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>AI Account Intelligence</span>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed">
                  {customer360Data.behavior.ai_insight}
                </p>
                <div className="flex items-center justify-between pt-2 border-t border-indigo-500/20">
                  <span className="text-[11px] text-slate-400">
                    💡 Next Recommended: <strong className="text-white">{customer360Data.behavior.next_action}</strong>
                  </span>
                  <Button
                    onClick={() => {
                      setCustomer360ModalOpen(false);
                      handleOpenCommunication(customer360Data.customer, 'email');
                    }}
                    variant="primary"
                    size="sm"
                    icon={Send}
                    className="text-xs"
                  >
                    Compose Notice
                  </Button>
                </div>
              </div>

              {/* Invoices Timeline */}
              <div>
                <h4 className="font-bold text-white text-xs mb-2 flex items-center gap-1.5">
                  <Receipt className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Invoices & Settlement History ({customer360Data.invoices?.length || 0})</span>
                </h4>
                <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                  {!customer360Data.invoices?.length ? (
                    <p className="text-slate-500 text-[11px] py-2">No invoices recorded for this account.</p>
                  ) : (
                    customer360Data.invoices.map((inv) => (
                      <div
                        key={inv.id}
                        className="p-2 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-between text-[11px]"
                      >
                        <span className="font-bold text-white">{inv.invoice_number}</span>
                        <span className="text-slate-400">Due: {inv.due_date || 'N/A'}</span>
                        <span className="font-semibold text-slate-200">{formatMoney(inv.amount)}</span>
                        <Badge variant={inv.status === 'overdue' ? 'urgent' : (inv.status === 'paid' ? 'success' : 'warning')}>
                          {inv.status.toUpperCase()}
                        </Badge>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Multilingual Communication History Timeline */}
              <div>
                <h4 className="font-bold text-white text-xs mb-2 flex items-center gap-1.5">
                  <History className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Communication History (Email / SMS / Call) ({customerCommunications.length})</span>
                </h4>
                <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1">
                  {!customerCommunications.length ? (
                    <p className="text-slate-500 text-[11px] py-2">No communications recorded yet for this client.</p>
                  ) : (
                    customerCommunications.map((comm) => (
                      <div
                        key={comm.id}
                        className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1 text-[11px]"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-1.5">
                            <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px] font-bold text-indigo-300 uppercase">
                              {comm.communication_type}
                            </span>
                            <span className="px-1.5 py-0.5 rounded bg-indigo-950 text-[10px] font-semibold text-indigo-400 uppercase">
                              {comm.language}
                            </span>
                            <span className="font-semibold text-white truncate max-w-xs">
                              {comm.subject || comm.recipient}
                            </span>
                          </div>
                          <Badge variant={comm.status === 'sent' ? 'success' : (comm.status === 'approved' ? 'success' : 'warning')}>
                            {comm.status.toUpperCase()}
                          </Badge>
                        </div>
                        <p className="text-slate-300 text-[11px] line-clamp-2 leading-relaxed">
                          {comm.message}
                        </p>
                        <span className="text-[10px] text-slate-500 block">
                          {new Date(comm.created_at).toLocaleString()}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Modal Footer */}
              <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
                <Button onClick={() => setCustomer360ModalOpen(false)} variant="secondary" size="sm">
                  Close
                </Button>
              </div>
            </div>
          )}
        </Modal>
      )}

      {/* Reusable Customer Communication Modal */}
      {commModalOpen && selectedCommCustomer && (
        <CommunicationModal
          isOpen={commModalOpen}
          onClose={() => setCommModalOpen(false)}
          customer={selectedCommCustomer}
          initialType={commModalType}
          onSuccess={fetchCustomers}
        />
      )}

      {/* Create Customer Modal */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title="Add New Customer Profile"
      >
        <form onSubmit={handleCreateCustomer} className="space-y-3.5 text-xs">
          <div>
            <label className="block font-semibold text-slate-300 mb-1">
              Customer Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              value={newCustomer.name}
              onChange={(e) => setNewCustomer({ ...newCustomer, name: e.target.value })}
              placeholder="e.g. ABC Ltd or Jane Doe"
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Email Address <span className="text-slate-500 font-normal text-[10px]">(Optional)</span>
              </label>
              <input
                type="email"
                value={newCustomer.email}
                onChange={(e) => setNewCustomer({ ...newCustomer, email: e.target.value })}
                placeholder="accounts@example.com"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Phone Number <span className="text-slate-500 font-normal text-[10px]">(Optional)</span>
              </label>
              <input
                type="text"
                value={newCustomer.phone}
                onChange={(e) => setNewCustomer({ ...newCustomer, phone: e.target.value })}
                placeholder="+91XXXXXXXXXX"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1">Company</label>
            <input
              type="text"
              value={newCustomer.company}
              onChange={(e) => setNewCustomer({ ...newCustomer, company: e.target.value })}
              placeholder="Company legal name"
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
            <Button onClick={() => setCreateModalOpen(false)} variant="ghost" size="sm">
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" loading={submitting}>
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
      >
        <form onSubmit={handleUpdateCustomer} className="space-y-3.5 text-xs">
          <div>
            <label className="block font-semibold text-slate-300 mb-1">Customer Name</label>
            <input
              type="text"
              value={editCustomer.name}
              onChange={(e) => setEditCustomer({ ...editCustomer, name: e.target.value })}
              required
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Email Address <span className="text-slate-500 font-normal text-[10px]">(Optional)</span>
              </label>
              <input
                type="email"
                value={editCustomer.email}
                onChange={(e) => setEditCustomer({ ...editCustomer, email: e.target.value })}
                placeholder="accounts@example.com"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block font-semibold text-slate-300 mb-1">
                Phone Number <span className="text-slate-500 font-normal text-[10px]">(Optional)</span>
              </label>
              <input
                type="text"
                value={editCustomer.phone}
                onChange={(e) => setEditCustomer({ ...editCustomer, phone: e.target.value })}
                placeholder="+91XXXXXXXXXX"
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block font-semibold text-slate-300 mb-1">Company</label>
            <input
              type="text"
              value={editCustomer.company}
              onChange={(e) => setEditCustomer({ ...editCustomer, company: e.target.value })}
              className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
            <Button onClick={() => setEditModalOpen(false)} variant="ghost" size="sm">
              Cancel
            </Button>
            <Button type="submit" variant="primary" size="sm" loading={submitting}>
              Update Profile
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default CustomersPage;
