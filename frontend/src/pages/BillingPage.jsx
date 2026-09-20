import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  CreditCard,
  Plus,
  Trash2,
  Search,
  CheckCircle2,
  AlertCircle,
  Clock,
  Sparkles,
  Eye,
  RefreshCw,
  FileText,
  User,
  Building,
  Mail,
  Phone,
  Calendar,
  DollarSign,
  ArrowRight,
  ListOrdered
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const BillingPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  // Active view: 'create' for Create Billing workflow, 'records' for Billing records list
  const [activeView, setActiveView] = useState('create');

  // Customer state & selection
  const [customers, setCustomers] = useState([]);
  const [customerMode, setCustomerMode] = useState('existing'); // 'existing' | 'new'
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [customerForm, setCustomerForm] = useState({
    name: '',
    email: '',
    phone: '',
    address: '',
    company: ''
  });

  // Billing Details state
  const [autoInvoiceNumber, setAutoInvoiceNumber] = useState('');
  const [numberLoading, setNumberLoading] = useState(false);
  const [billingDate, setBillingDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [dueDate, setDueDate] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() + 30);
    return d.toISOString().split('T')[0];
  });
  const [billingDescription, setBillingDescription] = useState('');
  const [notes, setNotes] = useState('');

  // Line items
  const [items, setItems] = useState([
    { id: 1, description: 'Website Development', quantity: 1, unit_price: 5000 }
  ]);
  const [discount, setDiscount] = useState(0);
  const [taxRate, setTaxRate] = useState(0); // percentage

  // Payment Details state
  const [paidAmount, setPaidAmount] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  // Billing records state
  const [invoices, setInvoices] = useState([]);
  const [loadingInvoices, setLoadingInvoices] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [viewRecord, setViewRecord] = useState(null);
  const [actionLoadingId, setActionLoadingId] = useState(null);

  // 1. Fetch next authoritative invoice number
  const fetchNextInvoiceNumber = useCallback(async () => {
    setNumberLoading(true);
    try {
      const res = await api.get('/invoices/next-number');
      if (res.data?.invoice_number) {
        setAutoInvoiceNumber(res.data.invoice_number);
      }
    } catch (err) {
      console.error('Error fetching next invoice number:', err);
      // Fallback format matching pattern INV-YYYY-XXXX
      const yr = new Date().getFullYear();
      setAutoInvoiceNumber(`INV-${yr}-0001`);
    } finally {
      setNumberLoading(false);
    }
  }, []);

  // 2. Fetch existing customers
  const fetchCustomers = useCallback(async () => {
    try {
      const res = await api.get('/customers');
      setCustomers(res.data || []);
    } catch (err) {
      console.error('Error fetching customers:', err);
    }
  }, []);

  // 3. Fetch billing/invoice records
  const fetchRecords = useCallback(async () => {
    setLoadingInvoices(true);
    try {
      const res = await api.get('/invoices');
      setInvoices(res.data || []);
    } catch (err) {
      console.error('Error fetching billing records:', err);
    } finally {
      setLoadingInvoices(false);
    }
  }, []);

  useEffect(() => {
    fetchCustomers();
    fetchNextInvoiceNumber();
    fetchRecords();
  }, [fetchCustomers, fetchNextInvoiceNumber, fetchRecords]);

  // Handle existing customer selection
  const handleSelectCustomer = (id) => {
    setSelectedCustomerId(id);
    if (!id) {
      setCustomerForm({ name: '', email: '', phone: '', address: '', company: '' });
      return;
    }
    const found = customers.find((c) => String(c.id) === String(id));
    if (found) {
      setCustomerForm({
        name: found.name || '',
        email: found.email || '',
        phone: found.phone || '',
        address: found.address || found.company || '',
        company: found.company || found.name || ''
      });
    }
  };

  // Add / remove line item
  const handleAddItem = () => {
    setItems((prev) => [
      ...prev,
      { id: Date.now(), description: '', quantity: 1, unit_price: 0 }
    ]);
  };

  const handleRemoveItem = (id) => {
    if (items.length <= 1) {
      addToast('warning', 'Item Required', 'A billing record must contain at least one item.');
      return;
    }
    setItems((prev) => prev.filter((item) => item.id !== id));
  };

  const handleItemChange = (id, field, value) => {
    setItems((prev) =>
      prev.map((item) => {
        if (item.id === id) {
          return { ...item, [field]: value };
        }
        return item;
      })
    );
  };

  // Calculations
  const subtotal = useMemo(() => {
    return items.reduce((sum, item) => {
      const q = parseFloat(item.quantity) || 0;
      const u = parseFloat(item.unit_price) || 0;
      return sum + q * u;
    }, 0);
  }, [items]);

  const discountAmount = useMemo(() => {
    const d = parseFloat(discount) || 0;
    return Math.min(subtotal, Math.max(0, d));
  }, [discount, subtotal]);

  const taxAmount = useMemo(() => {
    const rate = parseFloat(taxRate) || 0;
    const taxable = Math.max(0, subtotal - discountAmount);
    return (taxable * rate) / 100;
  }, [taxRate, subtotal, discountAmount]);

  const totalAmount = useMemo(() => {
    return Math.max(0, subtotal - discountAmount + taxAmount);
  }, [subtotal, discountAmount, taxAmount]);

  const numericPaid = useMemo(() => {
    const p = parseFloat(paidAmount);
    return isNaN(p) ? 0 : Math.max(0, p);
  }, [paidAmount]);

  const remainingAmount = useMemo(() => {
    return Math.max(0, totalAmount - numericPaid);
  }, [totalAmount, numericPaid]);

  // Payment status calculation according to exact rules:
  // Paid Amount = 0 -> Unpaid (pending)
  // Paid Amount > 0 and Paid Amount < Total Amount -> Partially Paid (partially_paid)
  // Paid Amount = Total Amount -> Paid (paid)
  const paymentStatusInfo = useMemo(() => {
    if (totalAmount <= 0) {
      return { title: 'Unpaid', key: 'pending', variant: 'pending' };
    }
    if (numericPaid <= 0) {
      return { title: 'Unpaid', key: 'pending', variant: 'pending' };
    }
    if (numericPaid >= totalAmount) {
      return { title: 'Paid', key: 'paid', variant: 'paid' };
    }
    return { title: 'Partially Paid', key: 'partially_paid', variant: 'partially_paid' };
  }, [totalAmount, numericPaid]);

  // Create & Save Billing Handler
  const handleCreateBilling = async (e) => {
    e.preventDefault();

    // 1. Validate Customer
    let targetCustomerId = selectedCustomerId;
    const nameToValidate = customerForm.name.trim();
    const emailToValidate = customerForm.email.trim();
    const phoneToValidate = customerForm.phone.trim();

    if (!nameToValidate) {
      addToast('warning', 'Missing Details', 'Customer Name is required.');
      return;
    }

    if (!emailToValidate) {
      addToast('warning', 'Missing Details', 'Valid Email Address is required.');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailToValidate)) {
      addToast('warning', 'Invalid Email', 'Please enter a valid email address (e.g. name@example.com).');
      return;
    }

    // 2. Validate Billing Items
    if (!items.length) {
      addToast('warning', 'No Items', 'Please add at least one billing item.');
      return;
    }

    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      if (!it.description?.trim()) {
        addToast('warning', 'Item Description Missing', `Please enter a description for item #${i + 1}.`);
        return;
      }
      if (parseFloat(it.quantity) <= 0 || isNaN(parseFloat(it.quantity))) {
        addToast('warning', 'Invalid Quantity', `Item #${i + 1} must have a quantity greater than 0.`);
        return;
      }
      if (parseFloat(it.unit_price) < 0 || isNaN(parseFloat(it.unit_price))) {
        addToast('warning', 'Invalid Price', `Item #${i + 1} cannot have a negative unit price.`);
        return;
      }
    }

    // 3. Validate Paid Amount
    if (numericPaid > totalAmount && totalAmount > 0) {
      addToast('warning', 'Invalid Paid Amount', `Paid Amount (${formatMoney(numericPaid)}) cannot exceed Total Amount (${formatMoney(totalAmount)}).`);
      return;
    }

    setSubmitting(true);
    try {
      // Create new customer if mode is 'new' and doesn't already exist by email
      if (customerMode === 'new' || !targetCustomerId) {
        const existingCust = customers.find(
          (c) => c.email && c.email.toLowerCase() === emailToValidate.toLowerCase()
        );

        if (existingCust) {
          targetCustomerId = existingCust.id;
        } else {
          const custPayload = {
            name: nameToValidate,
            email: emailToValidate,
            phone: phoneToValidate,
            company: customerForm.company?.trim() || customerForm.address?.trim() || nameToValidate,
            status: 'active'
          };
          const custRes = await api.post('/customers', custPayload);
          targetCustomerId = custRes.data.id;
          setCustomers((prev) => [...prev, custRes.data]);
        }
      }

      // Prepare Line items payload
      const lineItemsPayload = items.map((it) => ({
        description: it.description.trim(),
        quantity: parseFloat(it.quantity) || 1,
        unit_price: parseFloat(it.unit_price) || 0,
        total_price: (parseFloat(it.quantity) || 1) * (parseFloat(it.unit_price) || 0)
      }));

      // Combined notes
      let combinedNotes = billingDescription.trim();
      if (customerForm.address?.trim()) {
        combinedNotes += `\nBilling Address: ${customerForm.address.trim()}`;
      }
      if (notes.trim()) {
        combinedNotes += `\n${notes.trim()}`;
      }

      const invoicePayload = {
        customer_id: parseInt(targetCustomerId),
        invoice_number: autoInvoiceNumber || 'AUTO',
        amount: parseFloat(totalAmount.toFixed(2)),
        paid_amount: parseFloat(numericPaid.toFixed(2)),
        pending_amount: parseFloat(remainingAmount.toFixed(2)),
        subtotal: parseFloat(subtotal.toFixed(2)),
        tax_amount: parseFloat(taxAmount.toFixed(2)),
        discount_amount: parseFloat(discountAmount.toFixed(2)),
        currency: business.currency || 'INR',
        issue_date: billingDate,
        due_date: dueDate,
        status: paymentStatusInfo.key,
        line_items: lineItemsPayload,
        notes: combinedNotes.trim() || null
      };

      const invRes = await api.post('/invoices', invoicePayload);
      const createdNumber = invRes.data.invoice_number || autoInvoiceNumber;

      addToast(
        'success',
        'Billing Created',
        `Billing saved! Invoice ${createdNumber} created successfully.`
      );

      // Refresh data
      await fetchRecords();
      await fetchNextInvoiceNumber();

      // Reset form to fresh state
      setCustomerMode('existing');
      setSelectedCustomerId('');
      setCustomerForm({ name: '', email: '', phone: '', address: '', company: '' });
      setItems([{ id: Date.now(), description: 'Website Development', quantity: 1, unit_price: 5000 }]);
      setPaidAmount(0);
      setDiscount(0);
      setTaxRate(0);
      setBillingDescription('');
      setNotes('');

      // Switch to records list to show new billing
      setActiveView('records');
    } catch (err) {
      console.error('Error saving billing:', err);
      const errMsg = err.response?.data?.detail || 'Failed to create billing record.';
      addToast('error', 'Billing Save Failed', errMsg);
    } finally {
      setSubmitting(false);
    }
  };

  // Generate reminder for a billing record
  const handleGenerateReminder = async (record) => {
    setActionLoadingId(record.id);
    try {
      await api.post(`/invoices/${record.id}/reminder`);
      addToast(
        'success',
        'AI Reminder Drafted',
        `Payment reminder queued for ${record.customer_name} (${record.invoice_number}) in Approval Center.`
      );
      if (onNavigate) {
        onNavigate('approvals');
      }
    } catch (err) {
      console.error('Reminder generation error:', err);
      addToast('error', 'Action Error', 'Could not draft payment reminder.');
    } finally {
      setActionLoadingId(null);
    }
  };

  // Filtered records
  const filteredRecords = useMemo(() => {
    return invoices.filter((inv) => {
      const q = searchQuery.toLowerCase();
      const matchesSearch =
        !searchQuery ||
        inv.invoice_number?.toLowerCase().includes(q) ||
        inv.customer_name?.toLowerCase().includes(q) ||
        inv.customer_email?.toLowerCase().includes(q);

      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'unpaid' && (inv.status === 'pending' || inv.payment_status === 'Unpaid')) ||
        (statusFilter === 'partially_paid' && inv.status === 'partially_paid') ||
        (statusFilter === 'paid' && inv.status === 'paid') ||
        (statusFilter === 'overdue' && inv.status === 'overdue');

      return matchesSearch && matchesStatus;
    });
  }, [invoices, searchQuery, statusFilter]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2.5">
            <span className="p-2 rounded-xl bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400">
              <CreditCard className="w-5 h-5" />
            </span>
            Billing & Payments
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Create customer billings, configure line-item services, record partial payments, and track receivables.
          </p>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-slate-800/80 p-1 rounded-xl self-start sm:self-auto border border-slate-200 dark:border-slate-700">
          <button
            onClick={() => setActiveView('create')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeView === 'create'
                ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-2xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Plus className="w-3.5 h-3.5" />
            Create Billing
          </button>
          <button
            onClick={() => setActiveView('records')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 cursor-pointer ${
              activeView === 'records'
                ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-2xs'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <ListOrdered className="w-3.5 h-3.5" />
            Billing Records ({invoices.length})
          </button>
        </div>
      </div>

      {/* VIEW 1: CREATE BILLING WORKFLOW */}
      {activeView === 'create' && (
        <form onSubmit={handleCreateBilling} className="space-y-6">
          {/* Workflow Header Indicator */}
          <div className="flex items-center gap-2 text-xs font-bold text-slate-400 uppercase tracking-wider">
            <span className="text-indigo-600 dark:text-indigo-400">1. Customer Details</span>
            <span>&rarr;</span>
            <span className="text-indigo-600 dark:text-indigo-400">2. Billing Details</span>
            <span>&rarr;</span>
            <span className="text-indigo-600 dark:text-indigo-400">3. Payment Details</span>
            <span>&rarr;</span>
            <span>4. Save Billing</span>
          </div>

          {/* SECTION 1: CUSTOMER DETAILS */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-xs space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">
                  1
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Customer Details</h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Select an existing client or enter new customer details.
                  </p>
                </div>
              </div>

              {/* Toggle Existing vs New Customer */}
              <div className="flex items-center gap-1 bg-slate-100 dark:bg-slate-800 p-1 rounded-xl self-start sm:self-auto">
                <button
                  type="button"
                  onClick={() => setCustomerMode('existing')}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    customerMode === 'existing'
                      ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-2xs'
                      : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Select Existing Customer
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setCustomerMode('new');
                    setSelectedCustomerId('');
                  }}
                  className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                    customerMode === 'new'
                      ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-2xs'
                      : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
                  }`}
                >
                  Create New Customer
                </button>
              </div>
            </div>

            {/* Existing Customer Dropdown */}
            {customerMode === 'existing' && (
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  Select Existing Customer <span className="text-rose-500">*</span>
                </label>
                <select
                  value={selectedCustomerId}
                  onChange={(e) => handleSelectCustomer(e.target.value)}
                  required
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">-- Choose a registered customer --</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} {c.email ? `(${c.email})` : ''} {c.phone ? `— ${c.phone}` : ''}
                    </option>
                  ))}
                </select>
                {!customers.length && (
                  <p className="text-[11px] text-slate-400 mt-1">
                    No customers found yet. Switch to "Create New Customer" above to register your first client.
                  </p>
                )}
              </div>
            )}

            {/* Customer Inputs Grid (Auto-populated if existing, editable if new) */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 pt-1">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Customer Name <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <User className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={customerForm.name}
                    onChange={(e) => setCustomerForm({ ...customerForm, name: e.target.value })}
                    disabled={customerMode === 'existing' && Boolean(selectedCustomerId)}
                    placeholder="e.g. Bharath"
                    required
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 disabled:opacity-80"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Phone Number
                </label>
                <div className="relative">
                  <Phone className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="tel"
                    value={customerForm.phone}
                    onChange={(e) => setCustomerForm({ ...customerForm, phone: e.target.value })}
                    disabled={customerMode === 'existing' && Boolean(selectedCustomerId)}
                    placeholder="e.g. 9566860154"
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 disabled:opacity-80"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Email Address <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Mail className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="email"
                    value={customerForm.email}
                    onChange={(e) => setCustomerForm({ ...customerForm, email: e.target.value })}
                    disabled={customerMode === 'existing' && Boolean(selectedCustomerId)}
                    placeholder="e.g. ponbharathramesh26@gmail.com"
                    required
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 disabled:opacity-80"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Customer Address / Company
                </label>
                <div className="relative">
                  <Building className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={customerForm.address}
                    onChange={(e) => setCustomerForm({ ...customerForm, address: e.target.value, company: e.target.value })}
                    disabled={customerMode === 'existing' && Boolean(selectedCustomerId)}
                    placeholder="e.g. Tech Studio, Chennai"
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500 disabled:opacity-80"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* SECTION 2: BILLING DETAILS */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">
                  2
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Billing Details</h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    Specify billing schedule, itemized services, tax, and discount.
                  </p>
                </div>
              </div>

              {/* Authoritative Auto-generated Invoice Number */}
              <div className="flex items-center gap-2 bg-slate-50 dark:bg-slate-800/90 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  Invoice Number:
                </span>
                <span className="font-mono font-bold text-xs text-indigo-600 dark:text-indigo-400">
                  {numberLoading ? 'Generating...' : autoInvoiceNumber || 'INV-2026-0001'}
                </span>
                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300">
                  Auto-generated
                </span>
              </div>
            </div>

            {/* Dates & Billing Description Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Billing Date <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Calendar className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="date"
                    value={billingDate}
                    onChange={(e) => setBillingDate(e.target.value)}
                    required
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Payment Due Date <span className="text-rose-500">*</span>
                </label>
                <div className="relative">
                  <Clock className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="date"
                    value={dueDate}
                    onChange={(e) => setDueDate(e.target.value)}
                    required
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Billing Description / Memo
                </label>
                <input
                  type="text"
                  value={billingDescription}
                  onChange={(e) => setBillingDescription(e.target.value)}
                  placeholder="e.g. Q3 Software Development & Hosting"
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Multiple Itemized Services Table */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider">
                  Billing Items / Services
                </span>
                <Button
                  type="button"
                  onClick={handleAddItem}
                  variant="secondary"
                  size="sm"
                  icon={Plus}
                  className="text-xs"
                >
                  Add Item / Service
                </Button>
              </div>

              <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-slate-50 dark:bg-slate-800/70 border-b border-slate-200 dark:border-slate-800 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                      <th className="p-3 w-1/2">Service / Item Description</th>
                      <th className="p-3 w-24">Quantity</th>
                      <th className="p-3 w-36">Unit Price ({business.currency || 'INR'})</th>
                      <th className="p-3 w-36 text-right">Total ({business.currency || 'INR'})</th>
                      <th className="p-3 w-12 text-center">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                    {items.map((item, idx) => {
                      const itemTotal = (parseFloat(item.quantity) || 0) * (parseFloat(item.unit_price) || 0);
                      return (
                        <tr key={item.id} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/30">
                          <td className="p-2.5">
                            <input
                              type="text"
                              value={item.description}
                              onChange={(e) => handleItemChange(item.id, 'description', e.target.value)}
                              placeholder={`e.g. ${idx === 0 ? 'Website Development' : (idx === 1 ? 'Hosting' : 'Maintenance')}`}
                              required
                              className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                            />
                          </td>
                          <td className="p-2.5">
                            <input
                              type="number"
                              min="1"
                              step="1"
                              value={item.quantity}
                              onChange={(e) => handleItemChange(item.id, 'quantity', e.target.value)}
                              required
                              className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                            />
                          </td>
                          <td className="p-2.5">
                            <input
                              type="number"
                              min="0"
                              step="0.01"
                              value={item.unit_price}
                              onChange={(e) => handleItemChange(item.id, 'unit_price', e.target.value)}
                              placeholder="5000"
                              required
                              className="w-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                            />
                          </td>
                          <td className="p-2.5 text-right font-bold text-slate-900 dark:text-white">
                            {formatMoney(itemTotal)}
                          </td>
                          <td className="p-2.5 text-center">
                            <button
                              type="button"
                              onClick={() => handleRemoveItem(item.id)}
                              disabled={items.length <= 1}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors disabled:opacity-30 cursor-pointer"
                              title="Delete Item"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Subtotal, Discount, and Tax Row */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 pt-1">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Discount ({business.currency || 'INR'})
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={discount}
                  onChange={(e) => setDiscount(e.target.value)}
                  placeholder="0.00"
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Tax / GST Rate (%)
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={taxRate}
                  onChange={(e) => setTaxRate(e.target.value)}
                  placeholder="0"
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Internal Notes
                </label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Net 30 days payment agreement"
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-900 dark:text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>

          {/* SECTION 3: TOTAL & PAYMENT DETAILS */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 p-5 shadow-xs space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="w-7 h-7 rounded-lg bg-indigo-50 dark:bg-indigo-950/40 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold text-xs">
                3
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Payment Details</h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  Record advance or partial payments. The system automatically calculates remaining amount and sets payment status.
                </p>
              </div>
            </div>

            {/* Paid Amount Input */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                  Paid Amount ({business.currency || 'INR'}) <span className="text-slate-400 font-normal">(Enter amount already paid)</span>
                </label>
                <div className="relative">
                  <DollarSign className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-3" />
                  <input
                    type="number"
                    min="0"
                    max={totalAmount || undefined}
                    step="0.01"
                    value={paidAmount}
                    onChange={(e) => setPaidAmount(e.target.value)}
                    placeholder="e.g. 3500"
                    required
                    className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-3 py-2.5 text-xs text-slate-900 dark:text-white font-semibold focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <span className="text-[10px] text-slate-400 mt-1 block">
                  Enter 0 if unpaid. Remaining amount will be used for AI payment reminders.
                </span>
              </div>

              {/* Dynamic Payment Status Feedback */}
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 flex flex-col justify-center">
                <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">
                  Payment Status
                </span>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant={paymentStatusInfo.variant}>
                    {paymentStatusInfo.title}
                  </Badge>
                  <span className="text-xs text-slate-600 dark:text-slate-400">
                    {numericPaid === 0
                      ? 'No payment received yet'
                      : numericPaid < totalAmount
                      ? `${formatMoney(numericPaid)} received, ${formatMoney(remainingAmount)} pending`
                      : 'Full invoice amount settled'}
                  </span>
                </div>
              </div>
            </div>

            {/* Calculation Summary Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700/60">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Subtotal</span>
                <span className="text-base font-bold text-slate-900 dark:text-white mt-1 block">
                  {formatMoney(subtotal)}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700/60">
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider block">Total Amount</span>
                <span className="text-base font-bold text-slate-900 dark:text-white mt-1 block">
                  {formatMoney(totalAmount)}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/40">
                <span className="text-[10px] text-emerald-700 dark:text-emerald-400 font-bold uppercase tracking-wider block">Paid Amount</span>
                <span className="text-base font-bold text-emerald-600 dark:text-emerald-400 mt-1 block">
                  {formatMoney(numericPaid)}
                </span>
              </div>

              <div className="p-3.5 rounded-xl bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-800/40">
                <span className="text-[10px] text-rose-700 dark:text-rose-400 font-bold uppercase tracking-wider block">Remaining Amount</span>
                <span className="text-base font-bold text-rose-600 dark:text-rose-400 mt-1 block">
                  {formatMoney(remainingAmount)}
                </span>
              </div>
            </div>
          </div>

          {/* Action Footer */}
          <div className="flex items-center justify-between p-4 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
              <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
              <span>
                Saving will create customer record (if new), allocate authoritative invoice{' '}
                <strong>{autoInvoiceNumber}</strong>, and calculate payment status.
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => setActiveView('records')}
              >
                View Records
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                loading={submitting}
                icon={CreditCard}
                className="text-xs"
              >
                Create Billing
              </Button>
            </div>
          </div>
        </form>
      )}

      {/* VIEW 2: BILLING RECORDS LIST */}
      {activeView === 'records' && (
        <div className="space-y-4">
          {/* Controls Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-white dark:bg-slate-900 p-3 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs">
            {/* Filter Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
              {['all', 'unpaid', 'partially_paid', 'paid', 'overdue'].map((status) => (
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
                placeholder="Search billing by customer, invoice #..."
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-9 pr-4 py-1.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Billing Records Table */}
          <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 overflow-hidden shadow-xs">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 dark:bg-slate-800/80 text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-800">
                    <th className="p-3.5 font-bold uppercase tracking-wider">Customer</th>
                    <th className="p-3.5 font-bold uppercase tracking-wider">Invoice No.</th>
                    <th className="p-3.5 font-bold uppercase tracking-wider">Total</th>
                    <th className="p-3.5 font-bold uppercase tracking-wider">Paid</th>
                    <th className="p-3.5 font-bold uppercase tracking-wider">Remaining</th>
                    <th className="p-3.5 font-bold uppercase tracking-wider">Due Date</th>
                    <th className="p-3.5 font-bold uppercase tracking-wider">Status</th>
                    <th className="p-3.5 font-bold uppercase tracking-wider text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {loadingInvoices ? (
                    <tr>
                      <td colSpan={8} className="text-center py-12 text-slate-400">
                        <div className="flex flex-col items-center gap-2">
                          <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                          <span>Loading billing records...</span>
                        </div>
                      </td>
                    </tr>
                  ) : !filteredRecords.length ? (
                    <tr>
                      <td colSpan={8} className="p-8">
                        <EmptyState
                          icon={CreditCard}
                          title="No billing records found"
                          description={
                            statusFilter !== 'all'
                              ? `No ${statusFilter.replace('_', ' ')} billing records found.`
                              : "Create your first billing with customer, itemized services, and payment details."
                          }
                          actionText="Create Billing"
                          onAction={() => setActiveView('create')}
                        />
                      </td>
                    </tr>
                  ) : (
                    filteredRecords.map((record) => {
                      const isOverdue = record.status === 'overdue';
                      const tot = record.total_amount !== undefined ? record.total_amount : (record.amount || 0);
                      const paid = record.paid_amount || 0;
                      const rem = record.pending_amount !== undefined ? record.pending_amount : Math.max(0, tot - paid);

                      return (
                        <tr
                          key={record.id}
                          onClick={() => setViewRecord(record)}
                          className={`hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors cursor-pointer ${
                            isOverdue ? 'bg-rose-50/20 dark:bg-rose-950/10' : ''
                          }`}
                        >
                          <td className="p-3.5">
                            <div className="font-semibold text-slate-900 dark:text-white">{record.customer_name}</div>
                            <div className="text-[10px] text-slate-400">{record.customer_email || 'No email provided'}</div>
                          </td>
                          <td className="p-3.5 font-mono font-bold text-slate-900 dark:text-white">
                            {record.invoice_number}
                          </td>
                          <td className="p-3.5 font-bold text-slate-900 dark:text-slate-100">
                            {formatMoney(tot)}
                          </td>
                          <td className="p-3.5 font-semibold text-emerald-600 dark:text-emerald-400">
                            {formatMoney(paid)}
                          </td>
                          <td className="p-3.5 font-semibold text-rose-600 dark:text-rose-400">
                            {formatMoney(rem)}
                          </td>
                          <td className="p-3.5 text-slate-600 dark:text-slate-300">
                            {record.due_date}
                          </td>
                          <td className="p-3.5">
                            <Badge variant={record.status}>
                              {record.payment_status || record.status?.replace('_', ' ')}
                            </Badge>
                          </td>
                          <td className="p-3.5 text-right space-x-1" onClick={(e) => e.stopPropagation()}>
                            {record.status !== 'paid' && rem > 0 && (
                              <Button
                                onClick={() => handleGenerateReminder(record)}
                                variant={isOverdue ? 'danger' : 'secondary'}
                                size="sm"
                                loading={actionLoadingId === record.id}
                                icon={Sparkles}
                                className="text-xs"
                              >
                                AI Reminder
                              </Button>
                            )}
                            <button
                              onClick={() => setViewRecord(record)}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
                              title="View Billing Details"
                            >
                              <Eye className="w-4 h-4" />
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
        </div>
      )}

      {/* View Billing Details Modal */}
      {viewRecord && (
        <Modal
          isOpen={Boolean(viewRecord)}
          onClose={() => setViewRecord(null)}
          title={`Billing Details – ${viewRecord.invoice_number}`}
        >
          <div className="space-y-4">
            {/* Customer Details */}
            <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-800 text-xs">
              <div>
                <span className="text-slate-500 font-semibold block uppercase text-[10px]">Customer</span>
                <span className="text-slate-900 dark:text-white font-bold text-sm">{viewRecord.customer_name}</span>
                <span className="text-slate-500 block">{viewRecord.customer_email || 'No email provided'}</span>
                {viewRecord.customer_phone && (
                  <span className="text-slate-500 block">{viewRecord.customer_phone}</span>
                )}
              </div>
              <div>
                <span className="text-slate-500 font-semibold block uppercase text-[10px]">Schedule</span>
                <div className="mt-0.5 space-y-1">
                  <div className="text-slate-700 dark:text-slate-300">Billing Date: <strong>{viewRecord.issue_date}</strong></div>
                  <div className="text-rose-600 dark:text-rose-400">Payment Due: <strong>{viewRecord.due_date}</strong></div>
                </div>
              </div>
            </div>

            {/* Line Items if present */}
            {viewRecord.line_items && viewRecord.line_items.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Billing Items / Services
                </span>
                <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden text-xs">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-slate-50 dark:bg-slate-800/80 text-slate-500 font-bold uppercase tracking-wider text-[10px] border-b border-slate-200 dark:border-slate-800">
                        <th className="p-2.5">Item / Service</th>
                        <th className="p-2.5 w-16">Qty</th>
                        <th className="p-2.5 w-24">Price</th>
                        <th className="p-2.5 w-28 text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                      {viewRecord.line_items.map((it, idx) => (
                        <tr key={idx}>
                          <td className="p-2.5 text-slate-900 dark:text-white">{it.description || it.name || 'Service Item'}</td>
                          <td className="p-2.5 text-slate-600 dark:text-slate-300">{it.quantity || 1}</td>
                          <td className="p-2.5 text-slate-600 dark:text-slate-300">{formatMoney(it.unit_price || 0)}</td>
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

            {/* Payment Summary */}
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-800 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-700/60 pb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
                  Payment Details
                </span>
                <Badge variant={viewRecord.status}>
                  {viewRecord.payment_status || viewRecord.status?.replace('_', ' ')}
                </Badge>
              </div>

              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                  <span className="text-[10px] text-slate-500 block font-semibold uppercase">Total Amount</span>
                  <span className="text-sm font-bold text-slate-900 dark:text-white mt-0.5 block">
                    {formatMoney(viewRecord.total_amount ?? viewRecord.amount)}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                  <span className="text-[10px] text-slate-500 block font-semibold uppercase">Paid Amount</span>
                  <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400 mt-0.5 block">
                    {formatMoney(viewRecord.paid_amount || 0)}
                  </span>
                </div>
                <div className="p-2.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                  <span className="text-[10px] text-slate-500 block font-semibold uppercase">Remaining</span>
                  <span className="text-sm font-bold text-rose-600 dark:text-rose-400 mt-0.5 block">
                    {formatMoney(
                      viewRecord.pending_amount !== undefined
                        ? viewRecord.pending_amount
                        : Math.max(0, (viewRecord.total_amount ?? viewRecord.amount) - (viewRecord.paid_amount || 0))
                    )}
                  </span>
                </div>
              </div>
            </div>

            {viewRecord.notes && (
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300">
                <span className="font-semibold text-slate-500 block mb-1">Notes:</span>
                {viewRecord.notes}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-100 dark:border-slate-800">
              {viewRecord.status !== 'paid' && (
                <Button
                  onClick={() => {
                    handleGenerateReminder(viewRecord);
                    setViewRecord(null);
                  }}
                  variant="danger"
                  size="sm"
                  icon={Sparkles}
                >
                  Generate AI Reminder
                </Button>
              )}
              <Button onClick={() => setViewRecord(null)} variant="secondary" size="sm">
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default BillingPage;
