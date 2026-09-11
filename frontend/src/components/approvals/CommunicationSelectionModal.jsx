import React, { useState, useEffect } from 'react';
import { Mail, MessageSquare, AlertCircle, User, FileText, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';
import api from '../../services/api';

const CommunicationSelectionModal = ({
  isOpen,
  onClose,
  context
}) => {
  const [sendState, setSendState] = useState('idle'); // 'idle' | 'sending' | 'success' | 'error'
  const [loadingChannel, setLoadingChannel] = useState(null); // 'email' | 'sms' | null
  const [resultInfo, setResultInfo] = useState(null);
  const [contactError, setContactError] = useState(null);

  useEffect(() => {
    if (isOpen) {
      setSendState('idle');
      setLoadingChannel(null);
      setResultInfo(null);
      setContactError(null);
    }
  }, [isOpen, context?.approval_id]);

  if (!isOpen || !context) return null;

  const customerName = context.customer_name || 'Customer';
  const invoiceNumber = context.invoice_number || 'N/A';
  const pendingAmount = context.pending_amount !== undefined && context.pending_amount !== null
    ? Number(context.pending_amount)
    : Number(context.invoice_total || context.total_amount || 0);

  const currency = context.currency || 'INR';
  const currencySymbol = currency === 'INR' || currency === '₹' ? '₹' : (currency === 'USD' || currency === '$' ? '$' : `${currency} `);
  const formattedPending = `${currencySymbol}${pendingAmount.toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

  // Determine contact availability
  const hasEmail = Boolean(context.has_email || (context.customer_email && context.customer_email.includes('@')));
  const rawPhone = context.customer_phone || '';
  const phoneDigits = rawPhone.replace(/\D/g, '');
  const hasPhone = Boolean(context.has_phone || phoneDigits.length >= 7);
  const hasNeither = !hasEmail && !hasPhone;

  const handleClose = (refreshNeeded = false) => {
    setSendState('idle');
    setLoadingChannel(null);
    setResultInfo(null);
    setContactError(null);
    if (onClose) {
      onClose(refreshNeeded);
    }
  };

  const handleSendEmail = async () => {
    if (sendState === 'sending') return; // Guard against double/rapid clicks

    if (!hasEmail) {
      setContactError('Email cannot be sent because this customer has no email address.');
      return;
    }

    setContactError(null);
    setSendState('sending');
    setLoadingChannel('email');

    try {
      const res = await api.post(`/approvals/${context.approval_id}/execute-email`);
      if (res.data?.success) {
        setSendState('success');
        setResultInfo({
          channel: 'Email',
          recipient: res.data.recipient || context.customer_email,
          customer: res.data.customer_name || customerName,
          message: res.data.message || 'Email sent successfully'
        });
      } else {
        setSendState('error');
        setResultInfo({
          channel: 'Email',
          error: res.data?.message || 'Email sending failed.',
          recipient: context.customer_email,
          customer: customerName
        });
      }
    } catch (err) {
      setSendState('error');
      const errMsg = err.response?.data?.detail || err.response?.data?.message || 'Email sending failed. Please check your SMTP configuration.';
      setResultInfo({
        channel: 'Email',
        error: errMsg,
        recipient: context.customer_email,
        customer: customerName
      });
    } finally {
      setLoadingChannel(null);
    }
  };

  const handleSendMessage = async () => {
    if (sendState === 'sending') return; // Guard against double/rapid clicks

    if (!hasPhone) {
      setContactError('Message cannot be sent because this customer has no phone number.');
      return;
    }

    setContactError(null);
    setSendState('sending');
    setLoadingChannel('sms');

    try {
      const res = await api.post(`/approvals/${context.approval_id}/execute-message`);
      if (res.data?.success) {
        setSendState('success');
        setResultInfo({
          channel: 'Message',
          recipient: res.data.recipient || context.customer_phone,
          customer: res.data.customer_name || customerName,
          message: res.data.message || 'Message sent successfully'
        });
      } else {
        setSendState('error');
        setResultInfo({
          channel: 'Message',
          error: res.data?.message || 'Message sending failed.',
          recipient: context.customer_phone,
          customer: customerName
        });
      }
    } catch (err) {
      setSendState('error');
      const errMsg = err.response?.data?.detail || err.response?.data?.message || 'Message sending failed.';
      setResultInfo({
        channel: 'Message',
        error: errMsg,
        recipient: context.customer_phone,
        customer: customerName
      });
    } finally {
      setLoadingChannel(null);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => handleClose(sendState === 'success')}
      title={
        sendState === 'success'
          ? 'Communication Dispatched'
          : sendState === 'error'
          ? 'Communication Dispatch Status'
          : 'Choose Communication Method'
      }
      maxWidth="max-w-lg"
    >
      <div className="text-slate-800 dark:text-slate-200">
        {/* State 1: Sending / Loading */}
        {sendState === 'sending' && (
          <div className="py-8 flex flex-col items-center justify-center text-center space-y-3">
            <Loader2 className="w-10 h-10 text-indigo-600 dark:text-indigo-400 animate-spin" />
            <p className="text-base font-bold text-slate-900 dark:text-white">
              {loadingChannel === 'sms' ? 'Sending message...' : 'Sending email...'}
            </p>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Connecting to existing backend dispatch service. Please wait...
            </p>
          </div>
        )}

        {/* State 2: Success */}
        {sendState === 'success' && (
          <div className="py-2 space-y-5 text-center">
            <div className="w-14 h-14 mx-auto rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center border border-emerald-200 dark:border-emerald-800">
              <CheckCircle2 className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                ✓ {resultInfo?.channel} sent successfully
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Dispatched to customer and recorded in Dispatched Logs.
              </p>
            </div>

            <div className="bg-slate-50 dark:bg-[#18181d] border border-slate-200 dark:border-[#2a2a32] rounded-xl p-4 text-xs space-y-2.5 text-left">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Recipient:</span>
                <span className="font-semibold text-slate-800 dark:text-slate-200 font-mono">{resultInfo?.recipient}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Customer:</span>
                <span className="font-bold text-slate-900 dark:text-white">{resultInfo?.customer}</span>
              </div>
              <div className="flex items-center justify-between pt-1 border-t border-slate-200/70 dark:border-slate-800/70">
                <span className="text-slate-500 dark:text-slate-400 font-medium">Channel:</span>
                <span className="font-semibold text-indigo-600 dark:text-indigo-400">{resultInfo?.channel}</span>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-100 dark:border-[#26262c]">
              <Button onClick={() => handleClose(true)} variant="primary" size="sm">
                Close
              </Button>
            </div>
          </div>
        )}

        {/* State 3: Failure */}
        {sendState === 'error' && (
          <div className="py-2 space-y-5 text-center">
            <div className="w-14 h-14 mx-auto rounded-full bg-rose-100 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center border border-rose-200 dark:border-rose-800">
              <XCircle className="w-8 h-8" />
            </div>

            <div>
              <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
                ✕ {resultInfo?.channel} sending failed
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                The communication could not be delivered through the backend service.
              </p>
            </div>

            <div className="bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 rounded-xl p-3.5 text-xs text-left space-y-1">
              <span className="font-bold text-rose-800 dark:text-rose-300">Reason:</span>
              <p className="text-rose-700 dark:text-rose-400 leading-relaxed break-words">{resultInfo?.error}</p>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 dark:border-[#26262c]">
              <div>
                {resultInfo?.channel === 'Email' && hasPhone && (
                  <Button onClick={handleSendMessage} variant="secondary" size="sm" icon={MessageSquare}>
                    Send by Message
                  </Button>
                )}
                {resultInfo?.channel === 'Message' && hasEmail && (
                  <Button onClick={handleSendEmail} variant="secondary" size="sm" icon={Mail}>
                    Send by Email
                  </Button>
                )}
              </div>
              <Button onClick={() => handleClose(false)} variant="ghost" size="sm">
                Close
              </Button>
            </div>
          </div>
        )}

        {/* State 4: Idle / Choice Screen */}
        {sendState === 'idle' && (
          <div className="space-y-5">
            <p className="text-sm sm:text-base font-semibold text-slate-900 dark:text-white">
              How would you like to contact the customer?
            </p>

            {/* Basic context details */}
            <div className="bg-slate-50 dark:bg-[#18181d] border border-slate-200 dark:border-[#2a2a32] rounded-xl p-4 space-y-2.5 text-xs sm:text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1.5 font-medium">
                  <User className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                  Customer:
                </span>
                <span className="font-bold text-slate-900 dark:text-white">
                  {customerName}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-slate-500 dark:text-slate-400 flex items-center gap-1.5 font-medium">
                  <FileText className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                  Invoice:
                </span>
                <span className="font-semibold text-slate-800 dark:text-slate-200 font-mono">
                  {invoiceNumber}
                </span>
              </div>

              <div className="flex items-center justify-between pt-1 border-t border-slate-200/70 dark:border-slate-800/70">
                <span className="text-slate-500 dark:text-slate-400 font-medium">
                  Pending:
                </span>
                <span className="font-extrabold text-rose-600 dark:text-rose-400">
                  {formattedPending}
                </span>
              </div>
            </div>

            {/* Inline warning for missing contact */}
            {contactError && (
              <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 text-amber-800 dark:text-amber-300 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
                <span>{contactError}</span>
              </div>
            )}

            {/* Contact Unavailable Warning if neither is available */}
            {hasNeither && !contactError && (
              <div className="flex items-start gap-2.5 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/60 text-amber-800 dark:text-amber-300 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-amber-600 dark:text-amber-400" />
                <span>No communication contact is available for this customer.</span>
              </div>
            )}

            {/* Action Choice Buttons */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              {/* Email Button */}
              <button
                type="button"
                disabled={!hasEmail || sendState === 'sending'}
                onClick={handleSendEmail}
                className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all ${
                  hasEmail && sendState !== 'sending'
                    ? 'bg-white dark:bg-[#1a1a20] border-indigo-200 dark:border-indigo-800/60 hover:border-indigo-500 dark:hover:border-indigo-500 hover:shadow-md cursor-pointer text-slate-900 dark:text-white group'
                    : 'bg-slate-100 dark:bg-[#141418] border-slate-200 dark:border-slate-800 opacity-60 cursor-not-allowed text-slate-400 dark:text-slate-500'
                }`}
              >
                <div className={`p-2 rounded-full mb-2 ${hasEmail ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 group-hover:scale-105 transition-transform' : 'bg-slate-200/60 dark:bg-slate-800 text-slate-400'}`}>
                  <Mail className="w-5 h-5" />
                </div>
                <span className="text-sm font-bold">Email</span>
                {!hasEmail && (
                  <span className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                    No email available
                  </span>
                )}
                {hasEmail && context.customer_email && (
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate max-w-full px-1">
                    {context.customer_email}
                  </span>
                )}
              </button>

              {/* Message Button */}
              <button
                type="button"
                disabled={!hasPhone || sendState === 'sending'}
                onClick={handleSendMessage}
                className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all ${
                  hasPhone && sendState !== 'sending'
                    ? 'bg-white dark:bg-[#1a1a20] border-emerald-200 dark:border-emerald-800/60 hover:border-emerald-500 dark:hover:border-emerald-500 hover:shadow-md cursor-pointer text-slate-900 dark:text-white group'
                    : 'bg-slate-100 dark:bg-[#141418] border-slate-200 dark:border-slate-800 opacity-60 cursor-not-allowed text-slate-400 dark:text-slate-500'
                }`}
              >
                <div className={`p-2 rounded-full mb-2 ${hasPhone ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 group-hover:scale-105 transition-transform' : 'bg-slate-200/60 dark:bg-slate-800 text-slate-400'}`}>
                  <MessageSquare className="w-5 h-5" />
                </div>
                <span className="text-sm font-bold">Message</span>
                {!hasPhone && (
                  <span className="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
                    No phone number available
                  </span>
                )}
                {hasPhone && context.customer_phone && (
                  <span className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 font-mono truncate max-w-full px-1">
                    {context.customer_phone}
                  </span>
                )}
              </button>
            </div>

            {/* Modal Footer / Close */}
            <div className="flex justify-end pt-3 border-t border-slate-100 dark:border-[#26262c]">
              <Button onClick={() => handleClose(false)} variant="ghost" size="sm">
                Close
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default CommunicationSelectionModal;
