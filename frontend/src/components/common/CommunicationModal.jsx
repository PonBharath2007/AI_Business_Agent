import React, { useState, useEffect } from 'react';
import {
  Mail,
  MessageSquare,
  Phone,
  Sparkles,
  Send,
  Eye,
  Edit3,
  ExternalLink,
  CheckCircle2,
  AlertCircle,
  Clock,
  Languages,
  User,
  Building,
  Receipt,
  Copy,
  Check,
  RotateCcw,
  X
} from 'lucide-react';
import api from '../../services/api';
import { useBusiness } from '../../context/BusinessContext';
import { useNotifications } from '../../context/NotificationContext';
import Button from './Button';
import Badge from './Badge';
import Modal from './Modal';

const CommunicationModal = ({
  isOpen,
  onClose,
  customer,
  initialType = 'email',
  onSuccess
}) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [commType, setCommType] = useState(initialType); // 'email', 'sms', 'call'
  const [language, setLanguage] = useState('en'); // 'en', 'ta', 'en_ta'
  const [templateType, setTemplateType] = useState('payment_reminder');
  const [tone, setTone] = useState('professional');
  const [customInstructions, setCustomInstructions] = useState('');

  // Editor states
  const [recipient, setRecipient] = useState('');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [activeView, setActiveView] = useState('editor'); // 'editor' or 'preview'
  const [deviceUri, setDeviceUri] = useState('');
  const [copied, setCopied] = useState(false);

  // Loading states
  const [generating, setGenerating] = useState(false);
  const [sending, setSending] = useState(false);
  const [generatedEngine, setGeneratedEngine] = useState('');

  // Check customer availability
  const hasEmail = Boolean(customer?.email && customer.email.includes('@'));
  const hasPhone = Boolean(customer?.phone && customer.phone.trim().length >= 4);

  // Sync recipient and defaults when customer or commType changes
  useEffect(() => {
    if (!customer) return;
    // Determine smart default type if initialType is unavailable
    let targetType = initialType;
    if (targetType === 'email' && !hasEmail && hasPhone) {
      targetType = 'sms';
    } else if (targetType === 'sms' && !hasPhone && hasEmail) {
      targetType = 'email';
    }
    setCommType(targetType);
    setDeviceUri('');
    if (targetType === 'email') {
      setRecipient(customer.email || '');
    } else {
      setRecipient(customer.phone || '');
    }
  }, [customer, initialType, isOpen, hasEmail, hasPhone]);

  useEffect(() => {
    if (!customer) return;
    if (commType === 'email') {
      setRecipient(customer.email || '');
    } else {
      setRecipient(customer.phone || '');
    }
  }, [commType, customer]);

  if (!customer) return null;

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await api.post('/communications/generate', {
        customer_id: customer.id,
        communication_type: commType,
        language: language,
        template_type: templateType,
        purpose: templateType,
        tone: tone,
        phone_number: commType !== 'email' ? recipient : undefined,
        custom_instructions: customInstructions
      });

      setSubject(res.data.subject || '');
      setMessage(res.data.body || '');
      setGeneratedEngine(res.data.engine || 'Google Gemini AI');

      // Update recipient if available
      if (commType === 'email' && res.data.recipient_email) {
        setRecipient(res.data.recipient_email);
      } else if (commType === 'sms' && res.data.recipient_phone) {
        setRecipient(res.data.recipient_phone);
      }

      const langLabel = language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'English + Tamil');
      addToast(
        'success',
        'Message Generated',
        `AI generated ${langLabel} ${commType === 'sms' ? 'Message' : commType.toUpperCase()} draft.`
      );
    } catch (err) {
      console.error('Generation error:', err);
      addToast('error', 'Generation Failed', 'Unable to generate the message. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const handleClear = () => {
    setMessage('');
    if (commType === 'email') setSubject('');
    setDeviceUri('');
    addToast('info', 'Cleared', 'Message composer cleared.');
  };

  const handleSend = async () => {
    if (commType === 'email') {
      if (!recipient || !recipient.includes('@')) {
        addToast('warning', 'Missing Email', 'Customer email address is not available or invalid.');
        return;
      }
      if (!message.trim()) {
        addToast('warning', 'Empty Message', 'Message cannot be empty.');
        return;
      }

      setSending(true);
      try {
        const res = await api.post('/communications/email', {
          customer_id: customer.id,
          communication_type: 'email',
          language: language,
          recipient: recipient,
          subject: subject || 'Business Operations Notice',
          message: message
        });

        const isLive = res.data.mode === 'live' || res.data.delivery?.mode === 'live';
        const isSimulated = res.data.mode === 'simulated' || res.data.delivery?.mode === 'simulated';
        const isFailed = res.data.status === 'failed' || res.data.delivery?.mode === 'failed';

        if (isLive) {
          addToast('success', 'Live Email Sent', res.data.message || `Email delivered to ${recipient} via Gmail SMTP.`);
        } else if (isSimulated) {
          addToast('warning', 'Simulated Mode', res.data.message || 'Email recorded locally. Set SMTP credentials in your deployment environment variables for live sending.');
        } else if (isFailed) {
          addToast('error', 'SMTP Delivery Failed', res.data.message || 'Failed to dispatch email via SMTP server.');
        } else {
          addToast('success', 'Email Processed', res.data.message || 'Email processed successfully.');
        }

        if (onSuccess) onSuccess();
        onClose();
      } catch (err) {
        console.error('Email send error:', err);
        const errMsg = err.response?.data?.detail || 'Unable to send email. Please try again.';
        addToast('error', 'Delivery Failed', errMsg);
      } finally {
        setSending(false);
      }
    } else if (commType === 'sms') {
      if (!recipient || !recipient.trim()) {
        addToast('warning', 'Missing Phone', 'Phone number is not available for this customer.');
        return;
      }
      if (!message.trim()) {
        addToast('warning', 'Empty Message', 'Message cannot be empty.');
        return;
      }

      setSending(true);
      try {
        const res = await api.post('/communications/sms', {
          customer_id: customer.id,
          communication_type: 'sms',
          language: language,
          recipient: recipient,
          subject: subject || 'Message Notice',
          message: message
        });

        setDeviceUri(res.data.device_uri || '');
        addToast('success', 'Message Processed', res.data.message || 'Message link prepared and recorded.');

        // Open native SMS app
        if (res.data.device_uri) {
          window.location.href = res.data.device_uri;
        }

        if (onSuccess) onSuccess();
      } catch (err) {
        console.error('SMS send error:', err);
        const errMsg = err.response?.data?.detail || 'Unable to open the messaging application.';
        addToast('error', 'Message Error', errMsg);
      } finally {
        setSending(false);
      }
    } else if (commType === 'call') {
      if (!recipient || !recipient.trim()) {
        addToast('warning', 'Missing Phone', 'Phone number is not available for this customer.');
        return;
      }

      setSending(true);
      try {
        const res = await api.post('/communications/call', {
          customer_id: customer.id,
          phone_number: recipient
        });

        setDeviceUri(res.data.device_uri || `tel:${recipient}`);
        addToast('info', 'Call Initiated', `Recorded phone call to ${recipient}.`);

        // Trigger native tel dialer
        window.location.href = res.data.device_uri || `tel:${recipient}`;

        if (onSuccess) onSuccess();
      } catch (err) {
        console.error('Call error:', err);
        addToast('error', 'Call Error', 'Failed to initiate phone call.');
      } finally {
        setSending(false);
      }
    }
  };

  const handleCopyMessage = () => {
    if (!message) return;
    navigator.clipboard.writeText(message);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
    addToast('info', 'Copied to Clipboard', 'Message text copied to clipboard.');
  };

  // Character calculation & segmentation
  const charCount = message.length;
  const hasTamil = /[\u0B80-\u0BFF]/.test(message);
  const segmentLimit = hasTamil ? 70 : 160;
  const segments = Math.ceil(charCount / segmentLimit) || (charCount > 0 ? 1 : 0);
  const isMultiSegment = charCount > segmentLimit;

  // Title calculation
  const modalTitle =
    commType === 'sms'
      ? 'Send Message'
      : commType === 'call'
      ? 'Direct Phone Call'
      : 'Send Email';

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={modalTitle}
      maxWidth="max-w-3xl"
    >
      <div className="space-y-4 text-xs">
        {/* Customer Context Strip */}
        <div className="p-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center font-bold text-indigo-300">
              <User className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-white">{customer.name}</span>
                <span className="text-[11px] text-slate-400">({customer.company || 'Direct Client'})</span>
              </div>
              <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-400 mt-0.5">
                <span className="flex items-center gap-1">
                  <Mail className="w-3 h-3 text-slate-500" />
                  {customer.email || <em className="text-amber-400 font-normal">Email not available</em>}
                </span>
                <span className="flex items-center gap-1">
                  <Phone className="w-3 h-3 text-slate-500" />
                  {customer.phone || <em className="text-amber-400 font-normal">Phone not available</em>}
                </span>
              </div>
            </div>
          </div>

          {(customer.overdue_amount > 0 || customer.pending_amount > 0) && (
            <div className="text-right sm:border-l sm:border-slate-800 sm:pl-4">
              <span className="text-[10px] uppercase font-bold text-slate-500 block">Overdue Balance</span>
              <span className="text-xs font-bold text-rose-400">
                {formatMoney(customer.overdue_amount || customer.pending_amount || 0)}
              </span>
            </div>
          )}
        </div>

        {/* Global Warnings based on customer data */}
        {!hasEmail && !hasPhone && (
          <div className="p-3 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>No communication details available for this customer. Please update customer contact information.</span>
          </div>
        )}
        {!hasEmail && hasPhone && commType === 'email' && (
          <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-500/30 text-amber-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
            <span>Email is not available for this customer. You can switch to <strong>Message</strong> or <strong>Call</strong> to contact them directly.</span>
          </div>
        )}
        {!hasPhone && hasEmail && (commType === 'sms' || commType === 'call') && (
          <div className="p-3 rounded-xl bg-amber-950/30 border border-amber-500/30 text-amber-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
            <span>Phone number is not available for this customer. You can use <strong>Email</strong> to contact them.</span>
          </div>
        )}

        {/* Communication Type & Language Selection Toolbar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Communication Type */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Communication Option
            </label>
            <div className="grid grid-cols-3 gap-1.5 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
              {[
                { id: 'email', label: 'Email', icon: Mail, disabled: !hasEmail, reason: 'Email not available' },
                { id: 'call', label: 'Phone', icon: Phone, disabled: !hasPhone, reason: 'Phone not available' },
                { id: 'sms', label: 'Message', icon: MessageSquare, disabled: !hasPhone, reason: 'Phone not available' }
              ].map((t) => {
                const Icon = t.icon;
                const active = commType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    disabled={t.disabled}
                    title={t.disabled ? t.reason : t.label}
                    onClick={() => {
                      if (t.disabled) return;
                      setCommType(t.id);
                      setDeviceUri('');
                    }}
                    className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg font-semibold transition-all ${
                      t.disabled
                        ? 'opacity-40 cursor-not-allowed text-slate-600 bg-transparent'
                        : active
                        ? 'bg-indigo-600 text-white shadow-md'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{t.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Language Selector (Disabled for Call) */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 flex items-center justify-between">
              <span>Message Language</span>
              <span className="text-[10px] text-indigo-400 normal-case">UI remains English</span>
            </label>
            <div className="grid grid-cols-3 gap-1.5 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
              {[
                { id: 'en', label: 'English' },
                { id: 'ta', label: 'Tamil' },
                { id: 'en_ta', label: 'English + Tamil' }
              ].map((l) => {
                const active = language === l.id;
                return (
                  <button
                    key={l.id}
                    type="button"
                    disabled={commType === 'call'}
                    onClick={() => setLanguage(l.id)}
                    className={`py-2 px-2 text-center rounded-lg font-semibold transition-all ${
                      commType === 'call'
                        ? 'opacity-40 cursor-not-allowed text-slate-500'
                        : active
                        ? 'bg-indigo-600 text-white shadow-md'
                        : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
                    }`}
                  >
                    {l.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* AI Generation Control Bar (For Email and Message / SMS) */}
        {commType !== 'call' && (
          <div className="p-3.5 rounded-2xl bg-indigo-950/20 border border-indigo-500/20 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-indigo-500/10">
              <div className="flex items-center gap-1.5 text-indigo-300 font-bold">
                <Sparkles className="w-4 h-4" />
                <span>AI Message Generator</span>
                <Badge variant="ai">Gemini</Badge>
              </div>
              <span className="text-[11px] text-slate-400">
                Context: {customer.overdue_amount > 0 ? 'Overdue Invoice Detected' : 'Active Account'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                  Message Purpose
                </label>
                <select
                  value={templateType}
                  onChange={(e) => setTemplateType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="payment_reminder">Payment Reminder</option>
                  <option value="overdue_invoice">Overdue Invoice</option>
                  <option value="appointment_reminder">Appointment Reminder</option>
                  <option value="followup">Follow-up</option>
                  <option value="customer_notification">Customer Notification</option>
                  <option value="order_update">Order / Update Notification</option>
                  <option value="general">General Message</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                  Tone Profile
                </label>
                <select
                  value={tone}
                  onChange={(e) => setTone(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="professional">Professional (Default)</option>
                  <option value="urgent">Urgent / Action Required</option>
                  <option value="friendly">Friendly & Courteous</option>
                  <option value="formal">Formal Executive</option>
                </select>
              </div>

              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                  Custom Instructions (Optional)
                </label>
                <input
                  type="text"
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  placeholder="e.g. mention invoice INV-1001"
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex justify-end pt-1">
              <Button
                type="button"
                onClick={handleGenerate}
                loading={generating}
                variant="primary"
                size="sm"
                icon={Sparkles}
                className="font-bold text-xs"
              >
                AI Generate ({language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'English + Tamil')})
              </Button>
            </div>
          </div>
        )}

        {/* Message Composition / Call Section */}
        {commType === 'call' ? (
          <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800 text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 flex items-center justify-center mx-auto">
              <Phone className="w-7 h-7" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Direct Phone Call</h3>
              <p className="text-slate-400 text-xs mt-1">
                Initiate a call to {customer.name} using your device's native calling application (tel:).
              </p>
            </div>

            <div className="max-w-xs mx-auto">
              <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1 text-left">
                Recipient Phone Number
              </label>
              <input
                type="tel"
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
                placeholder="+91XXXXXXXXXX"
                className="w-full bg-slate-950 border border-slate-700 rounded-xl px-3 py-2 text-white font-mono text-sm focus:outline-none focus:border-indigo-500 text-center"
              />
            </div>

            <div className="pt-2 flex justify-center gap-3">
              <Button
                onClick={handleSend}
                loading={sending}
                variant="success"
                size="md"
                icon={Phone}
                className="font-bold"
              >
                Call Customer Now (tel:)
              </Button>
            </div>
          </div>
        ) : (
          /* Email / Message Editor Area */
          <div className="space-y-3">
            {/* Recipient & Subject Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                  {commType === 'email' ? 'To (Email)' : 'To (Phone Number)'}
                </label>
                <input
                  type={commType === 'email' ? 'email' : 'tel'}
                  value={recipient}
                  onChange={(e) => setRecipient(e.target.value)}
                  placeholder={commType === 'email' ? 'customer@example.com' : '+91XXXXXXXXXX'}
                  required
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 font-mono text-xs"
                />
              </div>

              {commType === 'email' && (
                <div>
                  <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                    Subject Line
                  </label>
                  <input
                    type="text"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    placeholder="e.g. Payment Reminder - Invoice INV-1001"
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-white focus:outline-none focus:border-indigo-500 text-xs"
                  />
                </div>
              )}
            </div>

            {/* View Mode Toggle: Editor vs Live Preview & Copy / Clear */}
            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-bold text-slate-400">
                  {commType === 'email' ? 'Email Body' : 'Message Content'} ({language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'English + Tamil')})
                </span>
                {generatedEngine && (
                  <Badge variant="ai">{generatedEngine}</Badge>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleClear}
                  disabled={!message && !subject}
                  className="px-2 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-[11px] transition-colors disabled:opacity-40"
                  title="Clear composer"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Clear</span>
                </button>
                <button
                  type="button"
                  onClick={handleCopyMessage}
                  disabled={!message}
                  className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-[11px] transition-colors disabled:opacity-40"
                >
                  {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
                <div className="bg-slate-900 p-0.5 rounded-lg border border-slate-800 flex items-center">
                  <button
                    type="button"
                    onClick={() => setActiveView('editor')}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                      activeView === 'editor' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveView('preview')}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-semibold transition-all ${
                      activeView === 'preview' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
                    }`}
                  >
                    Preview
                  </button>
                </div>
              </div>
            </div>

            {/* Editor Textarea / Preview Box */}
            {activeView === 'editor' ? (
              <div className="space-y-1.5">
                <div className="relative">
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    rows={commType === 'email' ? 7 : 5}
                    placeholder={
                      commType === 'email'
                        ? 'Write or generate your business email in English, Tamil, or English + Tamil...'
                        : 'Write or generate normal message in English, Tamil, or English + Tamil...'
                    }
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed font-sans text-xs"
                  />
                </div>

                {/* Character Counter & Segment Warning for SMS / Normal Message */}
                {commType === 'sms' && (
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
                )}
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                {commType === 'email' && subject && (
                  <div className="pb-2 border-b border-slate-800 text-slate-300 font-bold">
                    Subject: {subject}
                  </div>
                )}
                <div className="whitespace-pre-wrap text-slate-200 font-sans leading-relaxed text-xs">
                  {message || <em className="text-slate-500">No message content to preview.</em>}
                </div>
              </div>
            )}

            {/* Device SMS Application Link Notice if Generated */}
            {commType === 'sms' && deviceUri && (
              <div className="p-3 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex items-center justify-between gap-3 text-indigo-300">
                <div className="flex items-center gap-2">
                  <ExternalLink className="w-4 h-4 shrink-0 text-indigo-400" />
                  <span>Device SMS link ready. You can open your phone's messaging application directly.</span>
                </div>
                <a
                  href={deviceUri}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shrink-0 transition-colors"
                >
                  Open Messaging App
                </a>
              </div>
            )}
          </div>
        )}

        {/* Modal Footer Actions */}
        <div className="flex items-center justify-between pt-3 border-t border-slate-800">
          <Button onClick={onClose} variant="ghost" size="sm">
            Cancel
          </Button>

          {commType !== 'call' && (
            <div className="flex items-center gap-2">
              <Button
                onClick={() => setActiveView(activeView === 'editor' ? 'preview' : 'editor')}
                variant="secondary"
                size="sm"
                icon={activeView === 'editor' ? Eye : Edit3}
              >
                {activeView === 'editor' ? 'Preview' : 'Back to Edit'}
              </Button>
              <Button
                onClick={handleSend}
                loading={sending}
                variant="primary"
                size="sm"
                icon={Send}
                className="font-bold"
              >
                {commType === 'email' ? 'Send Email (SMTP)' : 'Send Message'}
              </Button>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default CommunicationModal;
