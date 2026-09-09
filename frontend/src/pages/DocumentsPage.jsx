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
  Download,
  UserCheck,
  Receipt
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
  const [uploadStep, setUploadStep] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [analyzingDocId, setAnalyzingDocId] = useState(null);

  const fileInputRef = useRef(null);

  const renderDocStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    if (s === 'completed') return <Badge variant="success">Completed</Badge>;
    if (s === 'needs_review') return <Badge variant="warning">Needs Review</Badge>;
    if (s === 'failed') return <Badge variant="danger">Failed</Badge>;
    if (s === 'ocr_completed') return <Badge variant="ai">OCR Completed</Badge>;
    if (s === 'validating') return <Badge variant="info">Validating</Badge>;
    if (s === 'processing') return <Badge variant="pending">Processing...</Badge>;
    return <Badge variant="neutral">{status ? status.toUpperCase() : 'UPLOADED'}</Badge>;
  };

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await api.get('/documents');
      const docs = res.data || [];
      setDocuments(docs);
      setSelectedDoc((prev) => {
        if (prev) {
          const match = docs.find((d) => d.id === prev.id);
          return match || docs[0] || null;
        }
        return docs[0] || null;
      });
    } catch (err) {
      console.error('Error fetching documents:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setUploadStep('Uploading...');

    // Multi-step progress simulation for responsive feedback
    const stepTimer1 = setTimeout(() => setUploadStep('Reading invoice...'), 600);
    const stepTimer2 = setTimeout(() => setUploadStep('Extracting data...'), 1500);
    const stepTimer3 = setTimeout(() => setUploadStep('Validating...'), 2600);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('auto_analyze', 'true');

    try {
      const res = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);
      setUploadStep('Completed');
      addToast('success', 'Document Processed', `${file.name} uploaded and analyzed by AI.`);
      setSelectedDoc(res.data);
      await fetchDocuments();
    } catch (err) {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);
      console.error('Upload error:', err);
      addToast('error', 'Upload Failed', err.response?.data?.detail || 'Unable to process this invoice. Please verify the uploaded file.');
    } finally {
      setUploading(false);
      setTimeout(() => setUploadStep(''), 1500);
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
          extracted_data: res.data?.data?.extracted_data,
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
      addToast('error', 'Error', 'Could not delete document.');
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

  const extracted = selectedDoc?.extracted_data || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            Document Intelligence & OCR
            <Badge variant="ai">AI Engine</Badge>
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Upload invoices, receipts, and contracts. AI automatically extracts fields, detects overdue items, and queues approvals.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Button
            onClick={() => fileInputRef.current?.click()}
            variant="primary"
            size="sm"
            loading={uploading}
            icon={UploadCloud}
            className="text-xs"
          >
            {uploadStep || 'Upload File'}
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

      {/* Multi-step processing indicator banner (if active) */}
      {uploading && (
        <div className="p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/60 flex items-center justify-between gap-4 animate-in fade-in">
          <div className="flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin shrink-0" />
            <div>
              <h4 className="text-xs font-bold text-indigo-900 dark:text-indigo-200">
                AI OCR Pipeline Active
              </h4>
              <p className="text-[11px] text-indigo-700 dark:text-indigo-300 mt-0.5">
                Current step: <strong>{uploadStep}</strong>
              </p>
            </div>
          </div>
          <span className="text-xs font-mono font-bold text-indigo-600 dark:text-indigo-400">
            Keep window open
          </span>
        </div>
      )}

      {/* Drag and Drop Zone */}
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`p-8 rounded-2xl border-2 border-dashed transition-all duration-200 cursor-pointer flex flex-col items-center justify-center text-center ${
          dragActive
            ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20'
            : 'border-slate-300 dark:border-slate-800 bg-white dark:bg-slate-900/40 hover:border-slate-400 dark:hover:border-slate-700'
        }`}
      >
        <div className="p-3.5 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-100 dark:border-indigo-900/50 text-indigo-600 dark:text-indigo-400 mb-3">
          <UploadCloud className="w-8 h-8" />
        </div>
        <h4 className="text-sm font-semibold text-slate-900 dark:text-white">
          Drag & drop invoices, PDFs, or images here
        </h4>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Supported formats: PDF, PNG, JPG, JPEG, DOCX, TXT (up to 25MB)
        </p>
        <span className="mt-3 text-[11px] text-indigo-600 dark:text-indigo-400 font-medium">
          Uploaded Document → AI OCR / Text Analysis → Extracted Data & Action Queue
        </span>
      </div>

      {/* Document Workspace Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Document List (Left 5 cols) */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200 dark:border-slate-800 flex flex-col">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
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
                description="Upload an invoice, receipt, or bill to begin automated extraction."
                actionText="Upload Document"
                onAction={() => fileInputRef.current?.click()}
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
                        ? 'bg-indigo-50/70 border-indigo-300 dark:bg-indigo-950/40 dark:border-indigo-800/80 shadow-xs'
                        : 'bg-slate-50/50 dark:bg-slate-850/40 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-start gap-2.5 min-w-0">
                        <div className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 font-bold text-[10px] shrink-0 uppercase border border-slate-200 dark:border-slate-700">
                          {ext}
                        </div>
                        <div className="min-w-0">
                          <h4 className="text-xs font-bold text-slate-900 dark:text-white truncate">{doc.file_name}</h4>
                          <span className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 block">
                            {new Date(doc.created_at).toLocaleDateString()} • {((doc.file_size || 0) / 1024).toFixed(1)} KB
                          </span>
                        </div>
                      </div>
                      <div className="shrink-0">{renderDocStatusBadge(status)}</div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Selected Document Details & Extracted Fields (Right 7 cols) */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-900 rounded-2xl p-5 border border-slate-200 dark:border-slate-800 flex flex-col justify-between space-y-4">
          {!selectedDoc ? (
            <div className="flex flex-col items-center justify-center py-20 text-slate-400 space-y-3">
              <FileCode className="w-12 h-12 stroke-[1.2] text-slate-300 dark:text-slate-600" />
              <p className="text-xs">Select a document on the left to view extracted AI metadata.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-start justify-between gap-3 pb-3 border-b border-slate-100 dark:border-slate-800">
                <div className="min-w-0">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white truncate">{selectedDoc.file_name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-500">Status:</span>
                    {renderDocStatusBadge(selectedDoc.processing_status)}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
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
                    variant="secondary"
                    size="sm"
                    loading={analyzingDocId === selectedDoc.id}
                    icon={Sparkles}
                    className="text-xs"
                  >
                    Re-analyze
                  </Button>
                  <button
                    onClick={() => handleDelete(selectedDoc.id)}
                    className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Extracted Key Metadata Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase font-bold">Invoice #</span>
                  <span className="text-xs font-mono font-bold text-slate-900 dark:text-white truncate block mt-0.5">
                    {extracted.invoice_number || 'N/A'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase font-bold">Total Amount</span>
                  <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 block mt-0.5">
                    {extracted.total_amount ? formatMoney(extracted.total_amount) : 'N/A'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase font-bold">Issue Date</span>
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-200 block mt-0.5">
                    {extracted.issue_date || 'N/A'}
                  </span>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-850 border border-slate-200 dark:border-slate-800">
                  <span className="text-[10px] text-slate-500 block uppercase font-bold">Due Date</span>
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-200 block mt-0.5">
                    {extracted.due_date || 'N/A'}
                  </span>
                </div>
              </div>

              {/* Customer Linkage Banner */}
              <div className="p-3.5 rounded-xl bg-indigo-50/60 dark:bg-indigo-950/20 border border-indigo-200 dark:border-indigo-800/40 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs">
                  <UserCheck className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />
                  <span className="text-slate-700 dark:text-slate-300">
                    Vendor / Customer: <strong>{extracted.customer_name || extracted.vendor_name || 'Identified via AI'}</strong>
                  </span>
                </div>
                <Button
                  onClick={() => onNavigate('invoices')}
                  variant="ghost"
                  size="sm"
                  className="text-xs text-indigo-600 dark:text-indigo-400 font-semibold"
                >
                  View Invoices <ArrowRight className="w-3.5 h-3.5 ml-1" />
                </Button>
              </div>

              {/* Raw JSON Extracted preview */}
              <div className="space-y-1.5">
                <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                  Extracted JSON Payload
                </span>
                <pre className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-[11px] font-mono text-slate-700 dark:text-slate-300 max-h-56 overflow-y-auto">
                  {JSON.stringify(extracted, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* OCR Text Preview Modal */}
      <Modal
        isOpen={previewModalOpen}
        onClose={() => setPreviewModalOpen(false)}
        title={`OCR Content: ${selectedDoc?.file_name}`}
        maxWidth="max-w-3xl"
      >
        <div className="space-y-3">
          <p className="text-xs text-slate-500">
            Raw text extracted via OCR engine before structured parsing:
          </p>
          <pre className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs font-mono text-slate-800 dark:text-slate-200 max-h-96 overflow-y-auto whitespace-pre-wrap leading-relaxed">
            {selectedDoc?.ocr_text || 'No raw OCR text available.'}
          </pre>
        </div>
      </Modal>
    </div>
  );
};

export default DocumentsPage;
