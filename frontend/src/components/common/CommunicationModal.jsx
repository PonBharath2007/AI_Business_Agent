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
  Check
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

  // Sync recipient and defaults when customer or commType changes
  useEffect(() => {
    if (!customer) return;
    setCommType(initialType);
    setDeviceUri('');
    if (initialType === 'email') {
      setRecipient(customer.email || '');
    } else {
      setRecipient(customer.phone || '');
    }
  }, [customer, initialType, isOpen]);

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
        tone: tone,
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

      addToast(
        'success',
        'Message Generated',
        `AI generated ${language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'Bilingual')} ${commType.toUpperCase()} content.`
      );
    } catch (err) {
      console.error('Generation error:', err);
      addToast('error', 'Generation Failed', 'Could not generate message. Please verify inputs.');
    } finally {
      setGenerating(false);
    }
  };

  const handleSend = async () => {
    if (commType === 'email') {
      if (!recipient || !recipient.includes('@')) {
        addToast('warning', 'Missing Email', 'Customer email address is not available or invalid.');
        return;
      }
      if (!message.trim()) {
        addToast('warning', 'Empty Message', 'Please enter or generate message content before sending.');
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

        addToast('success', 'Email Sent', res.data.message || 'Email successfully dispatched.');
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
        addToast('warning', 'Missing Phone', 'Customer phone number is not available.');
        return;
      }
      if (!message.trim()) {
        addToast('warning', 'Empty Message', 'Please enter or generate SMS message content.');
        return;
      }

      setSending(true);
      try {
        const res = await api.post('/communications/sms', {
          customer_id: customer.id,
          communication_type: 'sms',
          language: language,
          recipient: recipient,
          subject: subject || 'SMS Notice',
          message: message
        });

        setDeviceUri(res.data.device_uri || '');
        addToast('success', 'SMS Processed', res.data.message || 'SMS link generated and logged.');

        // If on mobile or device supports direct URI
        if (res.data.device_uri) {
          window.location.href = res.data.device_uri;
        }

        if (onSuccess) onSuccess();
      } catch (err) {
        console.error('SMS send error:', err);
        const errMsg = err.response?.data?.detail || 'Unable to process SMS. Please try again.';
        addToast('error', 'SMS Error', errMsg);
      } finally {
        setSending(false);
      }
    } else if (commType === 'call') {
      if (!recipient || !recipient.trim()) {
        addToast('warning', 'Missing Phone', 'Customer phone number is not available.');
        return;
      }

      setSending(true);
      try {
        const res = await api.post('/communications/call', {
          customer_id: customer.id,
          phone_number: recipient
        });

        setDeviceUri(res.data.device_uri || `tel:${recipient}`);
        addToast('info', 'Call Logged', `Recorded phone call to ${recipient}.`);

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

  const isEmailMissing = commType === 'email' && (!customer.email || !customer.email.includes('@'));
  const isPhoneMissing = (commType === 'sms' || commType === 'call') && (!customer.phone || !customer.phone.trim());

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Customer Communication"
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
                  {customer.email || <em className="text-rose-400">No email</em>}
                </span>
                <span className="flex items-center gap-1">
                  <Phone className="w-3 h-3 text-slate-500" />
                  {customer.phone || <em className="text-rose-400">No phone</em>}
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

        {/* Validation Warning Alert if Required Field Missing */}
        {isEmailMissing && (
          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>Customer email address is not available. Please edit customer profile or enter recipient email manually below.</span>
          </div>
        )}
        {isPhoneMissing && (
          <div className="p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>Customer phone number is not available. Please edit customer profile or enter recipient phone manually below.</span>
          </div>
        )}

        {/* Communication Type & Language Selection Toolbar */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {/* Communication Type */}
          <div>
            <label className="block text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
              Communication Type
            </label>
            <div className="grid grid-cols-3 gap-1.5 bg-slate-900/80 p-1 rounded-xl border border-slate-800">
              {[
                { id: 'email', label: 'Email', icon: Mail },
                { id: 'sms', label: 'SMS', icon: MessageSquare },
                { id: 'call', label: 'Call', icon: Phone }
              ].map((t) => {
                const Icon = t.icon;
                const active = commType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    onClick={() => {
                      setCommType(t.id);
                      setDeviceUri('');
                    }}
                    className={`flex items-center justify-center gap-1.5 py-2 px-2 rounded-lg font-semibold transition-all ${
                      active
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
              <span className="text-[10px] text-indigo-400 normal-case">UI stays English</span>
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

        {/* AI Generation Control Bar (Only for Email and SMS) */}
        {commType !== 'call' && (
          <div className="p-3.5 rounded-2xl bg-indigo-950/20 border border-indigo-500/20 space-y-3">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-indigo-500/10">
              <div className="flex items-center gap-1.5 text-indigo-300 font-bold">
                <Sparkles className="w-4 h-4" />
                <span>AI Message Assistant</span>
                <Badge variant="ai">Gemini</Badge>
              </div>
              <span className="text-[11px] text-slate-400">
                Context: {customer.overdue_amount > 0 ? 'Overdue Invoices Detected' : 'Active Account'}
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                  Template Goal
                </label>
                <select
                  value={templateType}
                  onChange={(e) => setTemplateType(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl px-2.5 py-1.5 text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="payment_reminder">Payment Reminder</option>
                  <option value="customer_followup">Customer Follow-up</option>
                  <option value="appointment_confirmation">Meeting / Milestone Confirmation</option>
                  <option value="general_inquiry">General Business Notice</option>
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
                  Special Instructions
                </label>
                <input
                  type="text"
                  value={customInstructions}
                  onChange={(e) => setCustomInstructions(e.target.value)}
                  placeholder="e.g. mention 5% prompt discount"
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
                Generate with AI ({language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'English + Tamil')})
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
                Initiate a call to {customer.name} using your device's native calling application.
              </p>
            </div>

            <div className="max-w-xs mx-auto">
              <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1 text-left">
                Phone Number
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
          /* Email / SMS Editor Area */
          <div className="space-y-3">
            {/* Recipient & Subject Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[10px] uppercase font-bold text-slate-400 mb-1">
                  {commType === 'email' ? 'Recipient Email' : 'Recipient Phone Number'}
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

            {/* View Mode Toggle: Editor vs Live Preview */}
            <div className="flex items-center justify-between pt-1">
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-bold text-slate-400">
                  {commType === 'email' ? 'Email Body' : 'SMS Message'} ({language === 'en' ? 'English' : (language === 'ta' ? 'Tamil' : 'English + Tamil')})
                </span>
                {generatedEngine && (
                  <Badge variant="ai">{generatedEngine}</Badge>
                )}
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={handleCopyMessage}
                  disabled={!message}
                  className="px-2 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 flex items-center gap-1 text-[11px] transition-colors"
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
              <div className="relative">
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  rows={commType === 'email' ? 7 : 4}
                  placeholder={
                    commType === 'email'
                      ? 'Write or generate your business email in English, Tamil, or English + Tamil...'
                      : 'Write or generate SMS text in English, Tamil, or English + Tamil...'
                  }
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed font-sans text-xs"
                />
                {commType === 'sms' && (
                  <div className="absolute right-3 bottom-2.5 text-[10px] text-slate-500">
                    {message.length} characters • {Math.ceil(message.length / 160) || 1} SMS part(s)
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
                {commType === 'email' ? 'Send Email (SMTP)' : 'Send SMS (Device App)'}
              </Button>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
};

export default CommunicationModal;
