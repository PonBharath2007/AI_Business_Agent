import React, { useState, useEffect, useCallback } from 'react';
import {
  MessageSquare,
  Sparkles,
  Send,
  User,
  Receipt,
  CheckCircle2,
  Copy,
  RefreshCw,
  Sliders,
  History,
  Eye,
  Trash2,
  Calendar,
  Layers,
  ArrowRight,
  Check,
  Info,
  Clock,
  Phone,
  Search,
  AlertCircle,
  ExternalLink,
  RotateCcw,
  Languages,
  Plus
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const MessageCenterPage = ({ onNavigate, preSelectedCustomerId = null }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [activeTab, setActiveTab] = useState('studio'); // 'studio' or 'history'
  const [customers, setCustomers] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState(preSelectedCustomerId ? String(preSelectedCustomerId) : '');
  const [selectedInvoiceId, setSelectedInvoiceId] = useState('');
  const [templateType, setTemplateType] = useState('payment_reminder');
  const [tone, setTone] = useState('professional');
  const [language, setLanguage] = useState('en'); // 'en', 'ta', 'en_ta'
  const [customInstructions, setCustomInstructions] = useState('');
  const [customerSearch, setCustomerSearch] = useState('');

  // Draft state
  const [recipientPhone, setRecipientPhone] = useState('');
  const [messageBody, setMessageBody] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [previewMode, setPreviewMode] = useState('editor'); // 'editor' or 'preview'
  const [generatedEngine, setGeneratedEngine] = useState('');
  const [copied, setCopied] = useState(false);
  const [deviceUri, setDeviceUri] = useState('');

  // History state
  const [messageHistory, setMessageHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [viewingMessage, setViewingMessage] = useState(null);

  // Fetch initial customer and invoice directory
  const fetchData = useCallback(async () => {
    try {
      const [custRes, invRes] = await Promise.all([
        api.get('/customers'),
        api.get('/invoices')
      ]);
      const custData = custRes.data || [];
      setCustomers(custData);
      setInvoices(invRes.data || []);

      if (custData.length > 0 && !selectedCustomerId) {
        // Default to first customer with a phone number or first customer
        const withPhone = custData.find((c) => c.phone && c.phone.trim().length > 3) || custData[0];
        setSelectedCustomerId(String(withPhone.id));
        setRecipientPhone(withPhone.phone || '');
      } else if (selectedCustomerId) {
        const found = custData.find((c) => String(c.id) === String(selectedCustomerId));
        if (found) {
          setRecipientPhone(found.phone || '');
        }
      }
    } catch (err) {
      console.error('Error fetching customers/invoices:', err);
    }
  }, [selectedCustomerId]);

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await api.get('/communications/messages');
      setMessageHistory(res.data || []);
    } catch (err) {
      console.error('Error fetching message history:', err);
      // Fallback: fetch general communications and filter
      try {
        const fallbackRes = await api.get('/communications?type=sms');
        setMessageHistory(fallbackRes.data || []);
      } catch (fallbackErr) {
        console.error('Fallback fetch error:', fallbackErr);
      }
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (activeTab === 'history') {
      fetchHistory();
    }
  }, [activeTab, fetchHistory]);

  const handleCustomerChange = (cid) => {
    setSelectedCustomerId(cid);
    setSelectedInvoiceId('');
    if (!cid) {
      setRecipientPhone('');
      return;
    }
    const found = customers.find((c) => String(c.id) === String(cid));
    if (found) {
      setRecipientPhone(found.phone || '');
    }
  };

  const handleInvoiceChange = (invId) => {
    setSelectedInvoiceId(invId);
    if (invId) {
      const foundInv = invoices.find((i) => String(i.id) === String(invId));
      if (foundInv && foundInv.customer_id) {
        setSelectedCustomerId(String(foundInv.customer_id));
        if (foundInv.customer?.phone) {
          setRecipientPhone(foundInv.customer.phone);
        }
      }
    }
  };

  // AI Message Generation
  const handleGenerateMessage = async () => {
    setLoading(true);
    setDeviceUri('');

    try {
      const res = await api.post('/communications/generate', {
        customer_id: selectedCustomerId ? parseInt(selectedCustomerId) : undefined,
        invoice_id: selectedInvoiceId ? parseInt(selectedInvoiceId) : undefined,
        communication_type: 'sms',
        language: language,
        template_type: templateType,
        purpose: templateType,
        tone: tone,
        phone_number: recipientPhone || undefined,
        custom_instructions: customInstructions || undefined
      });

      setMessageBody(res.data.body || '');
      setGeneratedEngine(res.data.engine || 'Google Gemini AI');
      if (res.data.recipient_phone) {
        setRecipientPhone(res.data.recipient_phone);
      }

      const langLabel = language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'English + Tamil');
      addToast('success', 'SMS Draft Ready', `AI generated ${langLabel} SMS message draft.`);
    } catch (err) {
      console.error('Message generation failed:', err);
      addToast('error', 'Generation Error', 'Unable to generate the message. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessageBody('');
    setDeviceUri('');
    addToast('info', 'Cleared', 'Message composer cleared.');
  };

  useEffect(() => {
    if (preSelectedCustomerId) {
      setSelectedCustomerId(String(preSelectedCustomerId));
      if (customers.length > 0) {
        const found = customers.find((c) => String(c.id) === String(preSelectedCustomerId));
        if (found) {
          setRecipientPhone(found.phone || '');
        }
      }
    }
  }, [preSelectedCustomerId, customers]);

  // Send SMS Message
  const handleSendMessage = async () => {
    const cleanPhone = recipientPhone?.trim();
    if (!cleanPhone) {
      addToast('warning', 'Missing Phone', 'Phone number is not available for this customer.');
      return;
    }
    if (!messageBody || !messageBody.trim()) {
      addToast('warning', 'Empty Message', 'Message cannot be empty.');
      return;
    }

    setSending(true);
    try {
      const res = await api.post('/communications/sms', {
        customer_id: selectedCustomerId ? parseInt(selectedCustomerId) : undefined,
        communication_type: 'sms',
        language: language,
        recipient: cleanPhone,
        subject: 'SMS Notice',
        message: messageBody
      });

      setDeviceUri(res.data.device_uri || '');

      const isLiveProvider = res.data.delivery?.mode === 'live';
      if (isLiveProvider) {
        addToast('success', 'Message Sent', 'Message sent successfully.');
      } else {
        addToast('success', 'SMS Composer Ready', 'SMS composer opened with the message and recipient.');
      }

      // Automatically trigger device native SMS messaging application
      if (res.data.device_uri) {
        window.location.href = res.data.device_uri;
      }

      // Refresh history in background
      fetchHistory();
    } catch (err) {
      console.error('Send error:', err);
      const errMsg = err.response?.data?.detail || 'Unable to send the message. Please try again.';
      addToast('error', 'SMS Failure', errMsg);
    } finally {
      setSending(false);
    }
  };

  const handleCopy = () => {
    if (!messageBody) return;
    navigator.clipboard.writeText(messageBody);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    addToast('info', 'Copied', 'Message text copied to clipboard.');
  };

  // Character calculation & segmentation
  const charCount = messageBody.length;
  const hasTamil = /[\u0B80-\u0BFF]/.test(messageBody);
  const segmentLimit = hasTamil ? 70 : 160;
  const segments = Math.ceil(charCount / segmentLimit) || (charCount > 0 ? 1 : 0);
  const isMultiSegment = charCount > segmentLimit;

  // Selected customer object
  const currentCustomer = customers.find((c) => String(c.id) === String(selectedCustomerId));
  const customerInvoices = invoices.filter((i) => String(i.customer_id) === String(selectedCustomerId));

  // Filtered customer list for quick selection
  const filteredCustomers = customers.filter((c) => {
    const q = customerSearch.toLowerCase();
    return (
      c.name?.toLowerCase().includes(q) ||
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
            Message Center
            <Badge variant="ai">SMS • English • தமிழ் • EN+TA</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Compose, AI-generate, and dispatch customer SMS/messages directly to phone numbers with Unicode Tamil preservation.
          </p>
        </div>

        {/* Tab Switcher & Refresh */}
        <div className="flex items-center gap-2">
          <div className="bg-slate-900 p-1 rounded-xl border border-slate-800 flex items-center">
            <button
              onClick={() => setActiveTab('studio')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === 'studio'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Composer Studio</span>
            </button>
            <button
              onClick={() => setActiveTab('history')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all ${
                activeTab === 'history'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <History className="w-3.5 h-3.5" />
              <span>Message History</span>
              {messageHistory.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-slate-800 text-[10px] text-slate-300 font-bold">
                  {messageHistory.length}
                </span>
              )}
            </button>
          </div>

          <Button
            onClick={() => (activeTab === 'studio' ? fetchData() : fetchHistory())}
            variant="secondary"
            size="sm"
            icon={RefreshCw}
            className="text-xs"
          >
            Refresh
          </Button>
        </div>
      </div>

      {activeTab === 'studio' ? (
        /* ======================== TAB 1: COMPOSER STUDIO ======================== */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Quick Customer Directory & Context (4 cols) */}
          <div className="lg:col-span-4 space-y-4">
            {/* Quick Customer Picker */}
            <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
                  <User className="w-4 h-4 text-indigo-400" />
                  Select Customer
                </span>
                <span className="text-[10px] text-slate-400">{customers.length} Accounts</span>
              </div>

              {/* Search Bar */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  value={customerSearch}
                  onChange={(e) => setCustomerSearch(e.target.value)}
                  placeholder="Search customer name or phone..."
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              {/* Customer List */}
              <div className="space-y-1 max-h-64 overflow-y-auto pr-1">
                {!filteredCustomers.length ? (
                  <p className="text-slate-500 text-xs py-3 text-center">No customers matching search.</p>
                ) : (
                  filteredCustomers.map((cust) => {
                    const isSelected = String(cust.id) === String(selectedCustomerId);
                    const hasPhone = Boolean(cust.phone && cust.phone.trim().length > 3);
                    return (
                      <button
                        key={cust.id}
                        type="button"
                        onClick={() => handleCustomerChange(String(cust.id))}
                        className={`w-full text-left p-2.5 rounded-xl text-xs transition-all flex items-center justify-between border ${
                          isSelected
                            ? 'bg-indigo-600/20 border-indigo-500/50 text-white shadow-sm'
                            : 'bg-slate-900/50 border-slate-800/80 text-slate-300 hover:bg-slate-800/60 hover:text-white'
                        }`}
                      >
                        <div className="min-w-0 flex-1">
                          <p className="font-bold truncate">{cust.name}</p>
                          <div className="flex items-center gap-2 text-[10px] text-slate-400 mt-0.5">
                            <span className="flex items-center gap-1">
                              <Phone className="w-2.5 h-2.5" />
                              {cust.phone || <em className="text-amber-400 font-normal">No Phone</em>}
                            </span>
                            {(cust.overdue_amount || 0) > 0 && (
                              <span className="text-rose-400 font-semibold">
                                {formatMoney(cust.overdue_amount)} Due
                              </span>
                            )}
                          </div>
                        </div>
                        {hasPhone ? (
                          <span className="px-1.5 py-0.5 rounded bg-emerald-950 text-[9px] font-bold text-emerald-400 uppercase">
                            SMS
                          </span>
                        ) : (
                          <span className="px-1.5 py-0.5 rounded bg-amber-950 text-[9px] font-bold text-amber-400 uppercase">
                            No Phone
                          </span>
                        )}
                      </button>
                    );
                  })
                )}
              </div>
            </div>

            {/* Selected Customer Financial & Billing Summary Card */}
            {currentCustomer && (
              <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-3">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                  <div>
                    <h4 className="font-bold text-white text-xs">{currentCustomer.name}</h4>
                    <p className="text-[10px] text-slate-400">{currentCustomer.company || 'Direct Client'}</p>
                  </div>
                  <Badge variant={currentCustomer.overdue_amount > 0 ? 'urgent' : 'success'}>
                    {currentCustomer.overdue_amount > 0 ? 'Overdue' : 'Good Standing'}
                  </Badge>
                </div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2 rounded-xl bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase block font-semibold">Phone</span>
                    <span className="font-mono text-slate-200 text-[11px] truncate block">
                      {currentCustomer.phone || <em className="text-amber-400">Not Available</em>}
                    </span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase block font-semibold">Email</span>
                    <span className="text-slate-200 text-[11px] truncate block">
                      {currentCustomer.email || <em className="text-slate-500">Not Available</em>}
                    </span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase block font-semibold">Pending</span>
                    <span className="font-bold text-amber-400 text-xs">
                      {formatMoney(currentCustomer.pending_amount || 0)}
                    </span>
                  </div>
                  <div className="p-2 rounded-xl bg-slate-900 border border-slate-800">
                    <span className="text-[10px] text-slate-500 uppercase block font-semibold">Overdue</span>
                    <span className="font-bold text-rose-400 text-xs">
                      {formatMoney(currentCustomer.overdue_amount || 0)}
                    </span>
                  </div>
                </div>

                {/* Linked Invoices dropdown if customer has invoices */}
                {customerInvoices.length > 0 && (
                  <div>
                    <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                      Attach Specific Invoice Context (Optional)
                    </label>
                    <select
                      value={selectedInvoiceId}
                      onChange={(e) => handleInvoiceChange(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500"
                    >
                      <option value="">General Account Notice (No invoice attached)</option>
                      {customerInvoices.map((inv) => (
                        <option key={inv.id} value={inv.id}>
                          {inv.invoice_number} - {formatMoney(inv.amount)} ({inv.status.toUpperCase()})
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column: AI Generator & Message Composer (8 cols) */}
          <div className="lg:col-span-8 space-y-4">
            {/* AI Control Configuration Card */}
            <div className="glass-panel p-4 sm:p-5 rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/20 via-slate-900/90 to-slate-900 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-indigo-500/20">
                <div className="flex items-center gap-2 text-indigo-300 font-bold text-sm">
                  <Sparkles className="w-4 h-4 text-indigo-400" />
                  <span>AI Message Generator</span>
                  <Badge variant="ai">Gemini</Badge>
                </div>
                <span className="text-[11px] text-slate-400">
                  Select language & purpose to craft an optimal SMS draft
                </span>
              </div>

              {/* Language Selector: English | Tamil | English + Tamil */}
              <div>
                <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
                  <span>1. Select Message Language</span>
                  <span className="text-[10px] text-indigo-400 normal-case">UI remains in English</span>
                </label>
                <div className="grid grid-cols-3 gap-2 bg-slate-950/60 p-1.5 rounded-xl border border-slate-800">
                  {[
                    { id: 'en', label: 'English', desc: 'English only' },
                    { id: 'ta', label: 'Tamil', desc: 'தமிழ் only' },
                    { id: 'en_ta', label: 'English + Tamil', desc: 'Combined Bilingual in 1 SMS' }
                  ].map((l) => {
                    const active = language === l.id;
                    return (
                      <button
                        key={l.id}
                        type="button"
                        onClick={() => setLanguage(l.id)}
                        className={`py-2 px-2 text-center rounded-lg font-semibold transition-all ${
                          active
                            ? 'bg-indigo-600 text-white shadow-md'
                            : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                        }`}
                      >
                        <div className="text-xs font-bold">{l.label}</div>
                        <div className="text-[10px] opacity-75">{l.desc}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Purpose & Tone Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                    2. Message Purpose
                  </label>
                  <select
                    value={templateType}
                    onChange={(e) => setTemplateType(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="payment_reminder">Payment Reminder</option>
                    <option value="overdue_invoice">Overdue Invoice</option>
                    <option value="appointment_reminder">Appointment Reminder</option>
                    <option value="followup">Customer Follow-up</option>
                    <option value="order_update">Order Update</option>
                    <option value="payment_confirmation">Payment Confirmation</option>
                    <option value="customer_notification">Customer Notification</option>
                    <option value="general">General Customer Message</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                    3. Tone Profile
                  </label>
                  <select
                    value={tone}
                    onChange={(e) => setTone(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    <option value="professional">Professional (Default)</option>
                    <option value="urgent">Urgent / Action Required</option>
                    <option value="friendly">Friendly & Courteous</option>
                    <option value="formal">Formal Executive</option>
                  </select>
                </div>

                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                    Custom Prompt / Note (Optional)
                  </label>
                  <input
                    type="text"
                    value={customInstructions}
                    onChange={(e) => setCustomInstructions(e.target.value)}
                    placeholder="e.g. mention invoice #1001"
                    className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              {/* AI Generate Action */}
              <div className="flex justify-end pt-1">
                <Button
                  onClick={handleGenerateMessage}
                  loading={loading}
                  variant="primary"
                  size="md"
                  icon={Sparkles}
                  className="font-bold text-xs"
                >
                  AI Generate ({language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'English + Tamil')})
                </Button>
              </div>
            </div>

            {/* Message Composer Area */}
            <div className="glass-panel p-4 sm:p-5 rounded-2xl border border-slate-800 space-y-3">
              {/* Recipient Phone Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-center">
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                    Recipient Phone Number
                  </label>
                  <div className="relative">
                    <Phone className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
                    <input
                      type="tel"
                      value={recipientPhone}
                      onChange={(e) => setRecipientPhone(e.target.value)}
                      placeholder="+91XXXXXXXXXX"
                      required
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-9 pr-3 py-2 text-white font-mono text-xs focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                <div className="flex items-center sm:justify-end gap-2 pt-4 sm:pt-0">
                  {/* Copy Button */}
                  <button
                    type="button"
                    onClick={handleCopy}
                    disabled={!messageBody}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-xs transition-colors disabled:opacity-40"
                  >
                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>

                  {/* Clear Button */}
                  <button
                    type="button"
                    onClick={handleClear}
                    disabled={!messageBody}
                    className="px-2.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-xs transition-colors disabled:opacity-40"
                    title="Clear composer"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Clear</span>
                  </button>

                  {/* Edit vs Preview Toggle */}
                  <div className="bg-slate-900 p-0.5 rounded-xl border border-slate-800 flex items-center">
                    <button
                      type="button"
                      onClick={() => setPreviewMode('editor')}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                        previewMode === 'editor' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      onClick={() => setPreviewMode('preview')}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
                        previewMode === 'preview' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Preview
                    </button>
                  </div>
                </div>
              </div>

              {/* Message Editor Textarea / Preview Box */}
              {previewMode === 'editor' ? (
                <div className="space-y-1.5">
                  <label className="block text-[10px] uppercase font-bold text-slate-400">
                    Message Body ({language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'English + Tamil')})
                  </label>
                  <textarea
                    value={messageBody}
                    onChange={(e) => setMessageBody(e.target.value)}
                    rows={6}
                    placeholder="Type your message or click 'AI Generate' above to create a professional message..."
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed font-sans text-xs"
                  />

                  {/* Character Counter & SMS Segment Warning */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 px-1">
                    <div className="text-[11px] text-slate-400 flex items-center gap-2">
                      <span>Characters: <strong className="text-white">{charCount}</strong></span>
                      <span>•</span>
                      <span>Segments: <strong className="text-white">{segments}</strong></span>
                      {hasTamil && (
                        <span className="text-indigo-400 text-[10px]">(Tamil Unicode detected)</span>
                      )}
                    </div>
                    {isMultiSegment && (
                      <div className="text-[11px] text-amber-400 flex items-center gap-1 font-medium">
                        <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                        <span>This message may be split into multiple SMS segments.</span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <span className="text-[10px] uppercase font-bold text-slate-500 block">Live Message Preview</span>
                  <div className="whitespace-pre-wrap text-slate-200 font-sans leading-relaxed text-xs">
                    {messageBody || <em className="text-slate-500">No message content to preview.</em>}
                  </div>
                </div>
              )}

              {/* Ready Device URI Link */}
              {deviceUri && (
                <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex items-center justify-between gap-3 text-indigo-300">
                  <div className="flex items-center gap-2 text-xs">
                    <ExternalLink className="w-4 h-4 shrink-0 text-indigo-400" />
                    <span>SMS link prepared. You can launch your native messaging app directly.</span>
                  </div>
                  <a
                    href={deviceUri}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shrink-0 transition-colors"
                  >
                    Open SMS App
                  </a>
                </div>
              )}

              {/* Send Button Toolbar */}
              <div className="flex items-center justify-between pt-3 border-t border-slate-800">
                <Button onClick={handleClear} variant="ghost" size="sm">
                  Cancel
                </Button>

                <Button
                  onClick={handleSendMessage}
                  loading={sending}
                  variant="primary"
                  size="md"
                  icon={Send}
                  className="font-bold text-xs"
                >
                  Send Message
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* ======================== TAB 2: MESSAGE HISTORY ======================== */
        <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <History className="w-4 h-4 text-indigo-400" />
                SMS Communication History
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Audit log of all SMS messages dispatched to customers.
              </p>
            </div>
            <Button
              onClick={fetchHistory}
              variant="secondary"
              size="sm"
              loading={historyLoading}
              icon={RefreshCw}
              className="text-xs"
            >
              Refresh Log
            </Button>
          </div>

          <div className="overflow-x-auto">
            {historyLoading ? (
              <div className="py-16 flex flex-col items-center justify-center space-y-3">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                <p className="text-xs text-slate-400">Loading message history...</p>
              </div>
            ) : !messageHistory.length ? (
              <div className="p-8">
                <EmptyState
                  icon={MessageSquare}
                  title="No SMS messages sent yet"
                  description="Use the Composer Studio to generate and dispatch your first customer SMS message."
                  actionText="Compose New Message"
                  onAction={() => setActiveTab('studio')}
                />
              </div>
            ) : (
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 uppercase font-semibold text-[10px] border-b border-slate-800">
                  <tr>
                    <th className="py-3 px-4">Customer</th>
                    <th className="py-3 px-4">Recipient Phone</th>
                    <th className="py-3 px-4">Language</th>
                    <th className="py-3 px-4">Message Preview</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Sent At</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 text-slate-300">
                  {messageHistory.map((msg) => (
                    <tr key={msg.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-white">
                        {msg.customer_name || 'Direct Recipient'}
                      </td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {msg.recipient}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-indigo-950 text-indigo-300 border border-indigo-800">
                          {msg.language === 'en_ta' ? 'English+Tamil' : (msg.language === 'ta' ? 'Tamil' : 'English')}
                        </span>
                      </td>
                      <td className="py-3 px-4 max-w-xs truncate text-slate-300">
                        {msg.message}
                      </td>
                      <td className="py-3 px-4">
                        <Badge variant={msg.status === 'sent' ? 'success' : (msg.status === 'failed' ? 'urgent' : 'warning')}>
                          {msg.status.toUpperCase()}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                        {new Date(msg.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Button
                          onClick={() => setViewingMessage(msg)}
                          variant="ghost"
                          size="sm"
                          icon={Eye}
                          className="text-xs"
                        >
                          View
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* View Message Content Modal */}
      {viewingMessage && (
        <Modal
          isOpen={Boolean(viewingMessage)}
          onClose={() => setViewingMessage(null)}
          title={`Message Details: ${viewingMessage.customer_name || viewingMessage.recipient}`}
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-2 text-slate-300 p-3 rounded-xl bg-slate-900 border border-slate-800">
              <div>
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Recipient Phone</span>
                <span className="font-mono text-white font-bold">{viewingMessage.recipient}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Language</span>
                <span className="text-indigo-400 font-bold uppercase">{viewingMessage.language}</span>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Status</span>
                <Badge variant={viewingMessage.status === 'sent' ? 'success' : 'warning'}>
                  {viewingMessage.status.toUpperCase()}
                </Badge>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase block font-semibold">Timestamp</span>
                <span className="text-slate-400">{new Date(viewingMessage.created_at).toLocaleString()}</span>
              </div>
            </div>

            <div>
              <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                Full Message Text
              </label>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 whitespace-pre-wrap text-slate-200 leading-relaxed font-sans">
                {viewingMessage.message}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
              <Button
                onClick={() => {
                  navigator.clipboard.writeText(viewingMessage.message);
                  addToast('info', 'Copied', 'Message text copied to clipboard.');
                }}
                variant="secondary"
                size="sm"
                icon={Copy}
              >
                Copy Content
              </Button>
              <Button onClick={() => setViewingMessage(null)} variant="primary" size="sm">
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default MessageCenterPage;
