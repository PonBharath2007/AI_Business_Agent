import React from 'react';
import { Mail, MessageSquare, AlertCircle, User, FileText } from 'lucide-react';
import Modal from '../common/Modal';
import Button from '../common/Button';

const CommunicationSelectionModal = ({
  isOpen,
  onClose,
  context,
  onSelectEmail,
  onSelectMessage
}) => {
  if (!isOpen || !context) return null;

  const customerName = context.customer_name || 'N/A';
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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Choose Communication Method"
      maxWidth="max-w-lg"
    >
      <div className="space-y-5 text-slate-800 dark:text-slate-200">
        {/* Prompt message */}
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

        {/* Contact Unavailable Warning */}
        {hasNeither && (
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
            disabled={!hasEmail}
            onClick={() => onSelectEmail(context)}
            className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all ${
              hasEmail
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
            disabled={!hasPhone}
            onClick={() => onSelectMessage(context)}
            className={`flex flex-col items-center justify-center p-4 rounded-xl border text-center transition-all ${
              hasPhone
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
          <Button onClick={onClose} variant="ghost" size="sm">
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default CommunicationSelectionModal;
