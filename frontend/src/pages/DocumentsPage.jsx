import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  UploadCloud,
  FileText,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Clock,
  Eye,
  Trash2,
  ArrowRight,
  RefreshCw,
  FileCode,
  Download
} from 'lucide-react';
import api from '../services/api';
import { useBusiness } from '../context/BusinessContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Badge from '../components/common/Badge';
import Modal from '../components/common/Modal';
import EmptyState from '../components/common/EmptyState';

const DocumentsPage = ({ onNavigate }) => {
  const { business, formatMoney } = useBusiness();
  const { addToast } = useNotifications();

  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [analyzingDocId, setAnalyzingDocId] = useState(null);

  const fileInputRef = useRef(null);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await api.get('/documents');
      setDocuments(res.data || []);
      if (res.data && res.data.length > 0 && !selectedDoc) {
        setSelectedDoc(res.data[0]);
      }
    } catch (err) {
      console.error('Error fetching documents:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedDoc]);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_analyze', 'true');

    try {
      const res = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      addToast('success', 'Document Processed', `${file.name} uploaded and analyzed by AI.`);
      setSelectedDoc(res.data);
      await fetchDocuments();
    } catch (err) {
      console.error('Upload error:', err);
      addToast('error', 'Upload Failed', err.response?.data?.detail || 'Could not upload document.');
    } finally {
      setUploading(false);
    }
  };

  const handleSampleInvoiceUpload = async () => {
    setUploading(true);
    try {
      // Create a mock sample invoice file in memory and upload
      const sampleText = `INVOICE
Invoice Number: INV-1001
Customer: ABC Ltd
Email: accounts@abc.example
Date: July 10, 2026
Due Date: August 10, 2026
Status: OVERDUE

Description: Enterprise Cloud Operations Architecture & Automation
Total Amount Due: $5,000.00 (USD)

Payment Terms: Net 30 days. Late fee of 1.5% applies for overdue balances.`;

      const blob = new Blob([sampleText], { type: 'text/plain' });
      const file = new File([blob], 'sample_invoice_ABC_Ltd.txt', { type: 'text/plain' });
      await handleFileUpload(file);
    } catch (err) {
      console.error('Sample upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  const handleReanalyze = async (docId) => {
    setAnalyzingDocId(docId);
    try {
      const res = await api.post(`/documents/${docId}/analyze`);
      addToast('success', 'Analysis Complete', 'AI workflow executed successfully.');
      await fetchDocuments();
      if (selectedDoc && selectedDoc.id === docId) {
        setSelectedDoc((prev) => ({
          ...prev,
          extracted_data: res.data.data.extracted_data,
          processing_status: 'completed'
        }));
      }
    } catch (err) {
      addToast('error', 'Analysis Error', 'Failed to re-analyze document.');
    } finally {
      setAnalyzingDocId(null);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await api.delete(`/documents/${docId}`);
      addToast('info', 'Document Removed', 'Document deleted successfully.');
      if (selectedDoc?.id === docId) setSelectedDoc(null);
      await fetchDocuments();
    } catch (err) {
      addToast('error', 'Error', 'Failed to delete document.');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            Document Intelligence & OCR
            <Badge variant="ai">AI Engine</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Upload invoices, receipts, and contracts. AI automatically extracts fields, detects overdue items, and queues approvals.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            onClick={handleSampleInvoiceUpload}
            variant="secondary"
            size="sm"
            loading={uploading}
            icon={Sparkles}
            className="text-xs border-indigo-500/30 text-indigo-300 hover:bg-indigo-600/20"
          >
            Quick Demo: Upload ABC Ltd Invoice
          </Button>

          <Button
            onClick={() => fileInputRef.current?.click()}
            variant="primary"
            size="sm"
            loading={uploading}
            icon={UploadCloud}
            className="text-xs"
          >
            Upload File
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg,.webp,.docx,.txt"
            onChange={(e) => {
              if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
            }}
            className="hidden"
          />
        </div>
      </div>

      {/* Drag and Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`p-8 rounded-2xl border-2 border-dashed transition-all duration-200 cursor-pointer flex flex-col items-center justify-center text-center ${
          dragActive
            ? 'border-indigo-500 bg-indigo-500/10 scale-[1.01]'
            : 'border-slate-800 bg-slate-900/30 hover:border-slate-700 hover:bg-slate-900/50'
        }`}
      >
        <div className="p-3.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 mb-3">
          <UploadCloud className="w-8 h-8 animate-bounce" />
        </div>
        <h4 className="text-sm font-semibold text-white">
          Drag & drop invoices, PDFs, or images here
        </h4>
        <p className="text-xs text-slate-400 mt-1">
          Supported formats: PDF, PNG, JPG, JPEG, DOCX, TXT (up to 25MB)
        </p>
        <span className="mt-3 text-[11px] text-indigo-400 font-medium">
          Uploaded Document → AI OCR / Text Analysis → Extracted Data & Action Queue
        </span>
      </div>

      {/* Document Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Document List (Left 5 cols) */}
        <div className="lg:col-span-5 glass-panel rounded-2xl p-4 border border-slate-800 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-400" />
              Processed Documents ({documents.length})
            </h3>
            <Button
              onClick={fetchDocuments}
              variant="ghost"
              size="sm"
              icon={RefreshCw}
              className="text-xs"
            />
          </div>

          <div className="mt-3 space-y-2 max-h-[520px] overflow-y-auto pr-1">
            {!documents.length ? (
              <EmptyState
                icon={FileText}
                title="No documents yet"
                description="Upload an invoice or click the Quick Demo button above."
                actionText="Upload Sample Invoice"
                onAction={handleSampleInvoiceUpload}
              />
            ) : (
              documents.map((doc) => {
                const isSelected = selectedDoc?.id === doc.id;
                const ext = doc.file_type?.toUpperCase() || 'DOC';
                const status = doc.processing_status;

                return (
                  <div
                    key={doc.id}
                    onClick={() => setSelectedDoc(doc)}
                    className={`p-3 rounded-xl border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-indigo-600/20 border-indigo-500/50 shadow-md'
                        : 'bg-slate-900/50 border-slate-800/80 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2.5 min-w-0">
                        <div className="p-2 rounded-lg bg-slate-800 text-indigo-300 font-bold text-[10px] shrink-0 uppercase">
                          {ext}
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-xs font-bold text-white truncate">{doc.file_name}</h4>
                          <span className="text-[10px] text-slate-400 mt-0.5 block">
                            {new Date(doc.created_at).toLocaleDateString()} • {(doc.file_size / 1024).toFixed(1)} KB
                          </span>
                        </div>
                      </div>

                      <Badge variant={status === 'completed' ? 'success' : 'pending'}>
                        {status}
                      </Badge>
                    </div>

                    <div className="mt-2.5 pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                      <span className="text-slate-400 capitalize">
                        Type: <strong className="text-slate-200">{doc.document_type || 'Invoice'}</strong>
                      </span>
                      <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => handleReanalyze(doc.id)}
                          disabled={analyzingDocId === doc.id}
                          className="p-1 text-slate-400 hover:text-indigo-300 rounded"
                          title="Re-run AI Analysis"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${analyzingDocId === doc.id ? 'animate-spin' : ''}`} />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id)}
                          className="p-1 text-slate-400 hover:text-rose-400 rounded"
                          title="Delete"
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
        </div>

        {/* Extracted Intelligence Details (Right 7 cols) */}
        <div className="lg:col-span-7 glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col">
          {!selectedDoc ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-8 text-slate-400">
              <FileText className="w-12 h-12 text-slate-600 mb-3" />
              <p className="text-sm">Select a document from the left to view extracted AI metadata.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Top Details Bar */}
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">{selectedDoc.file_name}</h3>
                    <Badge variant={selectedDoc.extracted_data?.is_overdue ? 'urgent' : 'success'}>
                      {selectedDoc.extracted_data?.is_overdue ? '🔴 Overdue' : '🟢 Active'}
                    </Badge>
                  </div>
                  <span className="text-xs text-slate-400">
                    Uploaded {new Date(selectedDoc.created_at).toLocaleString()}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    onClick={() => setPreviewModalOpen(true)}
                    variant="secondary"
                    size="sm"
                    icon={Eye}
                    className="text-xs"
                  >
                    View OCR Text
                  </Button>
                  <Button
                    onClick={() => handleReanalyze(selectedDoc.id)}
                    variant="primary"
                    size="sm"
                    loading={analyzingDocId === selectedDoc.id}
                    icon={Sparkles}
                    className="text-xs"
                  >
                    Re-Analyze
                  </Button>
                </div>
              </div>

              {/* Extraction Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Customer / Vendor</span>
                  <p className="text-xs font-bold text-white mt-1 truncate">
                    {selectedDoc.extracted_data?.customer_name || 'ABC Ltd'}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Invoice Number</span>
                  <p className="text-xs font-bold text-indigo-400 mt-1 truncate">
                    {selectedDoc.extracted_data?.invoice_number || 'INV-1001'}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Total Amount</span>
                  <p className="text-xs font-bold text-emerald-400 mt-1 truncate">
                    {formatMoney(selectedDoc.extracted_data?.amount || 50000)}
                  </p>
                </div>
                <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                  <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Due Date</span>
                  <p className="text-xs font-bold text-rose-400 mt-1 truncate">
                    {selectedDoc.extracted_data?.due_date || 'August 10, 2026'}
                  </p>
                </div>
              </div>

              {/* AI Summary Box */}
              {selectedDoc.extracted_data?.summary && (
                <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/20">
                  <span className="text-xs font-semibold text-indigo-300 flex items-center gap-1.5 mb-1">
                    <Sparkles className="w-3.5 h-3.5" /> AI Executive Summary:
                  </span>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    {selectedDoc.extracted_data.summary}
                  </p>
                </div>
              )}

              {/* Recommended Action & Workflow trigger */}
              {selectedDoc.extracted_data?.recommended_action && (
                <div className="p-3.5 rounded-xl bg-rose-950/20 border border-rose-500/30 flex items-center justify-between gap-3">
                  <div>
                    <span className="text-xs font-semibold text-rose-300 flex items-center gap-1.5">
                      <AlertCircle className="w-3.5 h-3.5" /> AI Recommended Action:
                    </span>
                    <p className="text-xs text-slate-300 mt-0.5">
                      {selectedDoc.extracted_data.recommended_action}
                    </p>
                  </div>
                  <Button
                    onClick={() => onNavigate('approvals')}
                    variant="danger"
                    size="sm"
                    className="text-xs shrink-0"
                  >
                    Go to Approvals <ArrowRight className="w-3 h-3 ml-1" />
                  </Button>
                </div>
              )}

              {/* Extracted Line Items */}
              {selectedDoc.extracted_data?.items && selectedDoc.extracted_data.items.length > 0 && (
                <div className="pt-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
                    Extracted Line Items
                  </h4>
                  <div className="border border-slate-800 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
                        <tr>
                          <th className="p-2.5 font-semibold">Description</th>
                          <th className="p-2.5 font-semibold text-right">Qty</th>
                          <th className="p-2.5 font-semibold text-right">Total</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 bg-slate-900/30">
                        {selectedDoc.extracted_data.items.map((item, idx) => (
                          <tr key={idx}>
                            <td className="p-2.5 text-slate-200">{item.description}</td>
                            <td className="p-2.5 text-right text-slate-400">{item.quantity}</td>
                            <td className="p-2.5 text-right font-semibold text-slate-100">{formatMoney(item.total)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Important Clauses */}
              {selectedDoc.extracted_data?.important_clauses && selectedDoc.extracted_data.important_clauses.length > 0 && (
                <div className="pt-2">
                  <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                    Important Terms & Clauses
                  </h4>
                  <ul className="space-y-1 text-xs text-slate-300">
                    {selectedDoc.extracted_data.important_clauses.map((clause, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-indigo-400">•</span>
                        <span>{clause}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Raw OCR Text Modal */}
      <Modal
        isOpen={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        title={`Extracted Text / OCR – ${selectedDoc?.file_name || 'Document'}`}
        maxWidth="max-w-3xl"
      >
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 whitespace-pre-wrap max-h-96 overflow-y-auto leading-relaxed">
          {selectedDoc?.ocr_text || 'No extractable text extracted.'}
        </div>
      </Modal>
    </div>
  );
};

export default DocumentsPage;
