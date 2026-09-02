import React, { useState, useEffect, useCallback } from 'react';
import {
  Mail,
  Sparkles,
  Send,
  User,
  Receipt,
  CheckCircle2,
  Copy,
  RefreshCw,
  Sliders,
  ShieldCheck,
  History,
  Eye,
  Trash2,
  Calendar,
  Layers,
  ArrowRight,
  Check,
  Info,
  Clock
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const EmailAssistantPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [activeTab, setActiveTab] = useState('studio'); // 'studio' or 'history'
  const [customers, setCustomers] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [selectedCustomerId, setSelectedCustomerId] = useState('');
  const [selectedInvoiceId, setSelectedInvoiceId] = useState('');
  const [templateType, setTemplateType] = useState('payment_reminder');
  const [tone, setTone] = useState('professional');
  const [language, setLanguage] = useState('en'); // 'en', 'ta', 'en_ta'
  const [customInstructions, setCustomInstructions] = useState('');

  // Draft state
  const [recipientEmail, setRecipientEmail] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [generationSteps, setGenerationSteps] = useState([]);
  const [currentStepIndex, setCurrentStepIndex] = useState(-1);
  const [previewMode, setPreviewMode] = useState('editor'); // 'editor' or 'preview'
  const [generatedEngine, setGeneratedEngine] = useState('');

  // Email History state
  const [emailHistory, setEmailHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [viewingEmail, setViewingEmail] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [custRes, invRes] = await Promise.all([
        api.get('/customers'),
        api.get('/invoices')
      ]);
      setCustomers(custRes.data || []);
      setInvoices(invRes.data || []);

      if (custRes.data?.length > 0 && !selectedCustomerId) {
        setSelectedCustomerId(String(custRes.data[0].id));
        setRecipientEmail(custRes.data[0].email || '');
      }
    } catch (err) {
      console.error('Error fetching data:', err);
    }
  }, []);

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const res = await api.get('/ai/emails');
      setEmailHistory(res.data || []);
    } catch (err) {
      console.error('Error fetching email history:', err);
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

  const handleCustomerChange = (e) => {
    const cid = e.target.value;
    setSelectedCustomerId(cid);
    if (!cid) {
      setRecipientEmail('');
      return;
    }
    const found = customers.find((c) => c.id === parseInt(cid));
    if (found) {
      setRecipientEmail(found.email || '');
    }
  };

  const handleInvoiceChange = (e) => {
    const invId = e.target.value;
    setSelectedInvoiceId(invId);
    if (invId) {
      const foundInv = invoices.find((i) => i.id === parseInt(invId));
      if (foundInv && foundInv.customer_id) {
        setSelectedCustomerId(String(foundInv.customer_id));
        if (foundInv.customer_email) {
          setRecipientEmail(foundInv.customer_email);
        }
      }
    }
  };

  const handleGenerateDraft = async () => {
    setLoading(true);
    setCurrentStepIndex(0);

    const simulationSteps = [
      '🔍 Accessing customer record and account ledger...',
      '📊 Analyzing invoice status, amounts, and payment terms...',
      `🧠 Synthesizing message tailored with ${tone.toUpperCase()} tone...`,
      '✨ Compiling final executive email draft...'
    ];
    setGenerationSteps(simulationSteps);

    // Step simulation for rich visual feedback
    const stepInterval = setInterval(() => {
      setCurrentStepIndex((prev) => {
        if (prev < simulationSteps.length - 1) return prev + 1;
        clearInterval(stepInterval);
        return prev;
      });
    }, 450);

    try {
      const res = await api.post('/ai/generate-email', {
        customer_id: selectedCustomerId ? parseInt(selectedCustomerId) : null,
        invoice_id: selectedInvoiceId ? parseInt(selectedInvoiceId) : null,
        template_type: templateType,
        tone: tone,
        language: language,
        custom_instructions: customInstructions
      });

      clearInterval(stepInterval);
      setCurrentStepIndex(simulationSteps.length - 1);

      setSubject(res.data.subject || '');
      setBody(res.data.body || '');
      setGeneratedEngine(res.data.engine || 'Intelligent Operations Agent');
      if (res.data.recipient_email) {
        setRecipientEmail(res.data.recipient_email);
      }

      addToast('success', 'AI Draft Generated', 'Tailored email generated based on business context.');
    } catch (err) {
      clearInterval(stepInterval);
      addToast('error', 'Error', 'Failed to generate email draft.');
    } finally {
      setTimeout(() => {
        setLoading(false);
      }, 500);
    }
  };

  const handleSendOrQueueApproval = async (createApprovalOnly = false) => {
    if (!recipientEmail || !subject || !body) {
      addToast('warning', 'Incomplete Form', 'Please enter recipient email, subject, and body.');
      return;
    }

    setSending(true);
    try {
      const cust = customers.find((c) => c.id === parseInt(selectedCustomerId));
      const inv = invoices.find((i) => i.id === parseInt(selectedInvoiceId));

      if (createApprovalOnly) {
        const approvalPayload = {
          action_type: 'send_payment_reminder',
          action_data: {
            customer_id: cust ? cust.id : null,
            customer_name: cust ? cust.name : 'Customer',
            customer_email: recipientEmail,
            invoice_id: inv ? inv.id : null,
            invoice_number: inv ? inv.invoice_number : 'INV-GENERAL',
            amount: inv ? parseFloat(inv.amount) : 0,
            currency: business.currency || 'USD',
            subject: subject,
            body: body,
            recipient_email: recipientEmail
          },
          status: 'pending',
          recommendation: `Payment correspondence draft for ${cust?.name || recipientEmail}.`
        };

        await api.post('/approvals', approvalPayload);
        addToast('info', 'Queued for Approval', 'Email draft submitted to Approval Center.');
        onNavigate('approvals');
      } else {
        const res = await api.post('/ai/send-email', {
          recipient_email: recipientEmail,
          subject: subject,
          body: body,
          customer_id: cust ? cust.id : null
        });
        if (res.data?.success || res.data?.status === 'sent') {
          addToast('success', 'Email Delivered', res.data?.message || `Email successfully dispatched to ${recipientEmail}.`);
        } else if (res.data?.status === 'simulated') {
          addToast('warning', 'Simulated Mode', res.data?.message || `Email recorded locally for ${recipientEmail}.`);
        } else {
          addToast('error', 'Delivery Failed', res.data?.message || `Email delivery failed for ${recipientEmail}.`);
        }
        fetchHistory();
      }
    } catch (err) {
      console.error('Email dispatch error:', err);
      const errMsg = err.response?.data?.detail || 'Failed to dispatch email.';
      addToast('error', 'Delivery Error', errMsg);
    } finally {
      setSending(false);
    }
  };

  const renderStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    if (s === 'sent') {
      return <Badge variant="success">Sent</Badge>;
    }
    if (s === 'pending') {
      return <Badge variant="pending">Pending</Badge>;
    }
    if (s === 'failed') {
      return <Badge variant="danger">Failed</Badge>;
    }
    if (s === 'simulated') {
      return <Badge variant="warning">Simulated</Badge>;
    }
    return <Badge variant={s === 'approved' ? 'success' : 'info'}>{status ? status.charAt(0).toUpperCase() + status.slice(1) : 'Unknown'}</Badge>;
  };

  const handleDeleteEmailLog = async (emailId) => {
    if (!window.confirm('Delete this email record from logs?')) return;
    try {
      await api.delete(`/ai/emails/${emailId}`);
      addToast('info', 'Log Removed', 'Email record deleted.');
      fetchHistory();
      if (viewingEmail?.id === emailId) setViewingEmail(null);
    } catch (err) {
      addToast('error', 'Error', 'Could not delete email log.');
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(`Subject: ${subject}\n\n${body}`);
    addToast('info', 'Copied to Clipboard', 'Subject and body copied.');
  };

  const handleTransformEmail = async (action, lang = 'Hindi') => {
    if (!body) {
      addToast('warning', 'No Content', 'Please generate or write email text first.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.post('/ai/transform-email', {
        text: body,
        action: action,
        target_language: lang
      });
      if (res.data?.transformed_text) {
        setBody(res.data.transformed_text);
        addToast('success', 'AI Transform Applied', `Email updated with action: ${action.replace('_', ' ')}.`);
      }
    } catch (err) {
      addToast('error', 'Transform Error', 'Failed to transform email content.');
    } finally {
      setLoading(false);
    }
  };

  const wordCount = body.trim() ? body.trim().split(/\s+/).length : 0;
  const charCount = body.length;

  return (
    <div className="space-y-6">
      {/* Header & Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            AI Email Assistant & Dispatch Studio
            <Badge variant="ai">GenAI Operations</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Generate customized, context-aware correspondence, reminders, and manage communication logs.
          </p>
        </div>

        {/* Studio vs History Nav */}
        <div className="flex items-center gap-1.5 bg-slate-900/90 p-1 rounded-xl border border-slate-800 self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('studio')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
              activeTab === 'studio'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Email Studio</span>
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all cursor-pointer ${
              activeTab === 'history'
                ? 'bg-indigo-600 text-white shadow-md'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <History className="w-3.5 h-3.5" />
            <span>Dispatched Logs ({emailHistory.length})</span>
          </button>
        </div>
      </div>

      {activeTab === 'studio' ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Form Controls (5 cols) */}
          <div className="lg:col-span-5 glass-panel rounded-2xl p-5 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Sliders className="w-4 h-4 text-indigo-400" />
                <span>Generation Parameters</span>
              </div>
              <span className="text-[11px] text-slate-500 font-medium">Step 1: Configure</span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Target Customer</label>
              <select
                value={selectedCustomerId}
                onChange={handleCustomerChange}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">-- Custom / Direct Recipient --</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.email})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Related Invoice (Optional)</label>
              <select
                value={selectedInvoiceId}
                onChange={handleInvoiceChange}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="">-- None / General Account --</option>
                {invoices.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.invoice_number} – {inv.customer_name} ({formatMoney(inv.amount)}) [{inv.status.toUpperCase()}]
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Template Objective</label>
              <select
                value={templateType}
                onChange={(e) => setTemplateType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="payment_reminder">Payment Reminder (Overdue / Upcoming)</option>
                <option value="invoice_followup">Invoice Follow-Up & Statement</option>
                <option value="customer_reply">Client Inquiry Reply</option>
                <option value="appointment_confirmation">Appointment & Milestone Review Confirmation</option>
                <option value="thank_you">Customer Appreciation & Partnership Thank You</option>
                <option value="complaint_response">Complaint Resolution & Executive Response</option>
                <option value="contract_expiry">Contract Expiry & Agreement Renewal</option>
                <option value="general_inquiry">General Business Inquiry & Account Update</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Message Language</label>
              <div className="grid grid-cols-3 gap-1.5 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
                {[
                  { id: 'en', label: 'English' },
                  { id: 'ta', label: 'Tamil' },
                  { id: 'en_ta', label: 'EN + தமிழ்' }
                ].map((l) => (
                  <button
                    key={l.id}
                    type="button"
                    onClick={() => setLanguage(l.id)}
                    className={`py-1.5 px-2 text-center rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                      language === l.id
                        ? 'bg-indigo-600 text-white shadow-md'
                        : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    {l.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Desired Tone</label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { id: 'professional', label: '👔 Professional' },
                  { id: 'friendly', label: '🤝 Friendly' },
                  { id: 'urgent', label: '⚠️ Urgent' },
                  { id: 'formal', label: '📜 Formal' }
                ].map((t) => (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => setTone(t.id)}
                    className={`py-1.5 px-2.5 rounded-xl border text-xs font-semibold transition-all cursor-pointer ${
                      tone === t.id
                        ? 'border-indigo-500 bg-indigo-500/20 text-white'
                        : 'border-slate-800 bg-slate-900/60 text-slate-400 hover:text-white'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Custom Notes / Instructions</label>
              <textarea
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
                placeholder="e.g. Mention 10% discount on next phase if paid by Friday, or reference invoice details..."
                rows={3}
                className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
              />
            </div>

            <Button
              onClick={handleGenerateDraft}
              variant="primary"
              size="md"
              loading={loading}
              icon={Sparkles}
              className="w-full font-bold cursor-pointer shadow-lg shadow-indigo-500/20"
            >
              {loading ? 'AI Reasoning in Progress...' : 'Generate AI Email Draft'}
            </Button>

            {/* Live Progress Stepper during generation */}
            {loading && (
              <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-indigo-500/30 space-y-2 animate-fadeIn">
                <div className="flex items-center gap-2 text-xs font-bold text-indigo-400">
                  <div className="w-2.5 h-2.5 rounded-full bg-indigo-400 animate-ping" />
                  <span>AI Generation Pipeline</span>
                </div>
                <div className="space-y-1.5 pt-1">
                  {generationSteps.map((step, idx) => (
                    <div
                      key={idx}
                      className={`flex items-center gap-2 text-[11px] transition-all ${
                        idx <= currentStepIndex ? 'text-slate-200 font-medium' : 'text-slate-600'
                      }`}
                    >
                      {idx < currentStepIndex ? (
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                      ) : idx === currentStepIndex ? (
                        <div className="w-3.5 h-3.5 border-2 border-indigo-400 border-t-transparent rounded-full animate-spin shrink-0" />
                      ) : (
                        <div className="w-3.5 h-3.5 rounded-full border border-slate-700 shrink-0" />
                      )}
                      <span>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Right Editor & Preview (7 cols) */}
          <div className="lg:col-span-7 glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between space-y-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800">
                <div className="flex items-center gap-2 text-sm font-bold text-white">
                  <Mail className="w-4 h-4 text-indigo-400" />
                  <span>Interactive Email Composer</span>
                  {generatedEngine && (
                    <Badge variant="ai">{generatedEngine}</Badge>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex items-center bg-slate-900 p-0.5 rounded-lg border border-slate-800">
                    <button
                      type="button"
                      onClick={() => setPreviewMode('editor')}
                      className={`px-2 py-1 rounded text-[11px] font-semibold transition-all ${
                        previewMode === 'editor' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Editor
                    </button>
                    <button
                      type="button"
                      onClick={() => setPreviewMode('preview')}
                      className={`px-2 py-1 rounded text-[11px] font-semibold transition-all ${
                        previewMode === 'preview' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                      }`}
                    >
                      Preview
                    </button>
                  </div>

                  {subject && (
                    <Button
                      onClick={handleCopy}
                      variant="ghost"
                      size="sm"
                      icon={Copy}
                      className="text-xs"
                    >
                      Copy
                    </Button>
                  )}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Recipient Email</label>
                <input
                  type="email"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  placeholder="recipient@example.com"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">Subject Line</label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="e.g. Payment Reminder – Invoice INV-1001"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs font-semibold text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              {previewMode === 'editor' ? (
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-1.5">
                    <label className="block text-xs font-semibold text-slate-300">Email Body Content</label>
                    
                    {/* AI Quick Transformation Bar */}
                    <div className="flex flex-wrap items-center gap-1">
                      <span className="text-[10px] text-indigo-400 font-bold uppercase mr-1">AI Edit:</span>
                      <button
                        type="button"
                        onClick={() => handleTransformEmail('make_urgent')}
                        disabled={loading || !body}
                        className="px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-300 border border-rose-500/20 text-[10px] font-semibold hover:bg-rose-500/20 transition-all cursor-pointer"
                        title="Enhance urgency"
                      >
                        ⚡ Make Urgent
                      </button>
                      <button
                        type="button"
                        onClick={() => handleTransformEmail('make_professional')}
                        disabled={loading || !body}
                        className="px-2 py-0.5 rounded-md bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 text-[10px] font-semibold hover:bg-indigo-500/20 transition-all cursor-pointer"
                        title="Refine professional tone"
                      >
                        👔 Executive
                      </button>
                      <button
                        type="button"
                        onClick={() => handleTransformEmail('shorten')}
                        disabled={loading || !body}
                        className="px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20 text-[10px] font-semibold hover:bg-amber-500/20 transition-all cursor-pointer"
                        title="Shorten to concise length"
                      >
                        ✂️ Shorten
                      </button>
                      <button
                        type="button"
                        onClick={() => handleTransformEmail('translate', 'Tamil')}
                        disabled={loading || !body}
                        className="px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 text-[10px] font-semibold hover:bg-emerald-500/20 transition-all cursor-pointer"
                        title="Translate body to Tamil"
                      >
                        🌐 Translate to தமிழ்
                      </button>
                    </div>
                  </div>
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    placeholder="Click 'Generate AI Email Draft' on the left to start, or type directly here..."
                    rows={11}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 font-sans leading-relaxed transition-all"
                  />
                  <div className="flex justify-end text-[10px] text-slate-500 mt-1">
                    <span>{wordCount} words | {charCount} characters</span>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl bg-slate-950 border border-slate-800 p-4 space-y-3 min-h-[260px]">
                  <div className="pb-3 border-b border-slate-800/80 text-xs text-slate-400 space-y-1">
                    <div><strong className="text-slate-300">From:</strong> {business.name} &lt;{business.email || 'noreply@company.com'}&gt;</div>
                    <div><strong className="text-slate-300">To:</strong> {recipientEmail || '(No recipient set)'}</div>
                    <div><strong className="text-slate-300">Subject:</strong> {subject || '(No subject)'}</div>
                  </div>
                  <div className="text-xs text-slate-200 whitespace-pre-wrap font-sans leading-relaxed py-2">
                    {body || <em>(No content yet. Click Generate on the left to build draft.)</em>}
                  </div>
                </div>
              )}
            </div>

            {/* Bottom Actions & Controls */}
            <div className="pt-3 border-t border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-[11px] text-slate-400">
                <span>Step 2: Choose Dispatch Mode</span>
                <span className="text-indigo-400 font-medium">Human-in-the-Loop Supported</span>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3">
                <Button
                  onClick={() => handleSendOrQueueApproval(true)}
                  variant="secondary"
                  size="sm"
                  disabled={!subject || !body || sending}
                  icon={ShieldCheck}
                  className="text-xs cursor-pointer hover:border-indigo-500"
                >
                  Send to Approval Center
                </Button>

                <Button
                  onClick={() => handleSendOrQueueApproval(false)}
                  variant="success"
                  size="sm"
                  loading={sending}
                  disabled={!subject || !body}
                  icon={Send}
                  className="text-xs font-bold cursor-pointer shadow-md shadow-emerald-600/20"
                >
                  Send Immediately
                </Button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* History & Dispatched Logs View */
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="text-xs text-slate-400">
              Audit log of all AI generated and dispatched client correspondence.
            </div>
            <Button
              onClick={fetchHistory}
              variant="ghost"
              size="sm"
              icon={RefreshCw}
              loading={historyLoading}
              className="text-xs"
            >
              Refresh
            </Button>
          </div>

          {!emailHistory.length ? (
            <EmptyState
              icon={Mail}
              title="No Email Logs Yet"
              description="Generated and sent emails will automatically be recorded here with delivery diagnostics."
              actionText="Create AI Email"
              onAction={() => setActiveTab('studio')}
            />
          ) : (
            <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-300">
                  <thead className="bg-slate-900/80 border-b border-slate-800 text-[11px] uppercase tracking-wider text-slate-400">
                    <tr>
                      <th className="py-3.5 px-4">Recipient / Customer</th>
                      <th className="py-3.5 px-4">Subject</th>
                      <th className="py-3.5 px-4">Status</th>
                      <th className="py-3.5 px-4">Dispatched At</th>
                      <th className="py-3.5 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {emailHistory.map((em) => (
                      <tr key={em.id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="py-3.5 px-4 font-medium text-white">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center">
                              <Mail className="w-3.5 h-3.5" />
                            </div>
                            <div>
                              <div>{em.customer_name}</div>
                              <div className="text-[11px] text-slate-400">{em.recipient_email}</div>
                            </div>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 font-semibold text-slate-200 max-w-xs truncate">
                          {em.subject}
                        </td>
                        <td className="py-3.5 px-4">
                          {renderStatusBadge(em.status)}
                        </td>
                        <td className="py-3.5 px-4 text-slate-400">
                          {em.created_at ? new Date(em.created_at).toLocaleString() : 'Recent'}
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-1.5">
                            <button
                              onClick={() => setViewingEmail(em)}
                              className="p-1.5 rounded-lg bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-all cursor-pointer"
                              title="View Full Content"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleDeleteEmailLog(em.id)}
                              className="p-1.5 rounded-lg bg-slate-800 text-rose-400 hover:text-rose-300 hover:bg-rose-950/40 transition-all cursor-pointer"
                              title="Delete Record"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}

      {/* View Email Content Modal */}
      {viewingEmail && (
        <Modal
          isOpen={Boolean(viewingEmail)}
          onClose={() => setViewingEmail(null)}
          title="Dispatched Email Details"
          maxWidth="max-w-2xl"
        >
          <div className="space-y-4">
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-1.5">
              <div><strong className="text-slate-400">Recipient:</strong> <span className="text-white">{viewingEmail.recipient_email}</span></div>
              <div><strong className="text-slate-400">Customer:</strong> <span className="text-white">{viewingEmail.customer_name}</span></div>
              <div><strong className="text-slate-400">Subject:</strong> <span className="text-white font-semibold">{viewingEmail.subject}</span></div>
              <div><strong className="text-slate-400">Status:</strong> {renderStatusBadge(viewingEmail.status)}</div>
              <div><strong className="text-slate-400">Date:</strong> <span className="text-slate-300">{new Date(viewingEmail.created_at).toLocaleString()}</span></div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Message Body</label>
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 whitespace-pre-wrap font-sans leading-relaxed max-h-96 overflow-y-auto">
                {viewingEmail.body}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <Button
                onClick={() => {
                  setSubject(viewingEmail.subject);
                  setBody(viewingEmail.body);
                  setRecipientEmail(viewingEmail.recipient_email);
                  setActiveTab('studio');
                  setViewingEmail(null);
                  addToast('info', 'Loaded into Composer', 'Email draft loaded into Studio for editing.');
                }}
                variant="primary"
                size="sm"
                icon={Sparkles}
              >
                Load into Studio
              </Button>
              <Button onClick={() => setViewingEmail(null)} variant="ghost" size="sm">
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default EmailAssistantPage;
