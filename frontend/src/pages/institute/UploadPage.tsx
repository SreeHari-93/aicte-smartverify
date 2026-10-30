import React, { useState, useEffect, useRef } from 'react';
import {
  FileUp,
  UploadCloud,
  File,
  Trash2,
  Download,
  AlertCircle,
  CheckCircle2,
  Loader2,
  CheckSquare,
  Clock,
  Eye,
  Edit2,
  Save,
  X,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  XCircle,
  RefreshCw,
} from 'lucide-react';
import {
  instituteApi,
  DocumentItem,
  InstituteChecklistItem,
  DocumentExtractionData,
  ApplicationReadinessData,
  InstituteAnomalyFlag,
} from '../../api/institute';
import { StatusPill } from '../../components/StatusPill';
import { Drawer } from '../../components/Drawer';

export const UploadPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [checklistItems, setChecklistItems] = useState<InstituteChecklistItem[]>([]);
  const [checklistStats, setChecklistStats] = useState({ total: 0, uploaded: 0, missing: 0 });
  const [selectedDocType, setSelectedDocType] = useState<string>('FIRE_NOC');
  const [selectedCategory, setSelectedCategory] = useState<string>('EOA');
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Readiness State
  const [readinessData, setReadinessData] = useState<ApplicationReadinessData | null>(null);
  const [selectedAppId, setSelectedAppId] = useState<number | null>(null);

  // Drawer State for Extracted Data
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [drawerDoc, setDrawerDoc] = useState<DocumentItem | null>(null);
  const [extractionData, setExtractionData] = useState<DocumentExtractionData | null>(null);
  const [isLoadingExtraction, setIsLoadingExtraction] = useState(false);
  const [editingFieldKey, setEditingFieldKey] = useState<string | null>(null);
  const [fieldEditValue, setFieldEditValue] = useState<string>('');
  const [isSavingField, setIsSavingField] = useState(false);
  const [fieldSaveSuccess, setFieldSaveSuccess] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [verifyNotice, setVerifyNotice] = useState<string | null>(null);
  const [docAnomalies, setDocAnomalies] = useState<InstituteAnomalyFlag[]>([]);

  const formatVerificationStatus = (raw?: string): string => {
    if (!raw) return 'Pending';
    const u = raw.toUpperCase().trim();
    switch (u) {
      case 'VERIFIED':
        return 'Verified';
      case 'MISMATCH_DETECTED':
        return 'Mismatch Detected';
      case 'EXPIRED':
        return 'Expired';
      case 'SOURCE_UNAVAILABLE':
        return 'Source Unavailable';
      case 'MANUAL_REVIEW_REQUIRED':
        return 'Manual Review Required';
      case 'VERIFICATION_PENDING':
      default:
        return 'Pending';
    }
  };

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [docsRes, checklistRes, appsRes] = await Promise.all([
        instituteApi.getDocuments(),
        instituteApi.getChecklist(selectedCategory),
        instituteApi.getApplications(),
      ]);
      setDocuments(docsRes);
      if (checklistRes && checklistRes.items) {
        setChecklistItems(checklistRes.items);
        setChecklistStats({
          total: checklistRes.total_required,
          uploaded: checklistRes.uploaded_count,
          missing: checklistRes.missing_count,
        });
      }

      // Fetch readiness for primary active application
      if (appsRes && appsRes.items && appsRes.items.length > 0) {
        const primaryApp = appsRes.items[0];
        setSelectedAppId(primaryApp.id);
        try {
          const rData = await instituteApi.getApplicationReadiness(primaryApp.id);
          setReadinessData(rData);
        } catch (rErr) {
          console.error('Failed to load readiness:', rErr);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [selectedCategory]);

  const handleFileUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    // Client-side quick check
    if (file.size > 20 * 1024 * 1024) {
      setUploadError('File size exceeds the permitted limit.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const docTypeCode = selectedDocType === 'GENERAL' ? undefined : selectedDocType;
      const newDoc = await instituteApi.uploadDocument(file, selectedAppId || undefined, docTypeCode);
      setUploadSuccess(`"${file.name}" uploaded successfully for type ${docTypeCode || 'General'}!`);
      setDocuments((prev) => [newDoc, ...prev]);

      // Refresh checklist & readiness
      const chk = await instituteApi.getChecklist(selectedCategory);
      if (chk && chk.items) {
        setChecklistItems(chk.items);
        setChecklistStats({
          total: chk.total_required,
          uploaded: chk.uploaded_count,
          missing: chk.missing_count,
        });
      }
      if (selectedAppId) {
        const rData = await instituteApi.getApplicationReadiness(selectedAppId);
        setReadinessData(rData);
      }
    } catch (err: any) {
      setUploadError(
        err.response?.data?.detail || 'Failed to upload document. Please ensure it is authentic PDF, JPG, or PNG.'
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (docId: number, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) return;
    try {
      await instituteApi.deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      const chk = await instituteApi.getChecklist(selectedCategory);
      if (chk && chk.items) {
        setChecklistItems(chk.items);
        setChecklistStats({
          total: chk.total_required,
          uploaded: chk.uploaded_count,
          missing: chk.missing_count,
        });
      }
      if (selectedAppId) {
        const rData = await instituteApi.getApplicationReadiness(selectedAppId);
        setReadinessData(rData);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete document.');
    }
  };

  const handleOpenDrawer = async (doc: DocumentItem) => {
    setDrawerDoc(doc);
    setIsDrawerOpen(true);
    setIsLoadingExtraction(true);
    setFieldSaveSuccess(null);
    setEditingFieldKey(null);
    setDocAnomalies([]);
    try {
      const [data, anomalies] = await Promise.all([
        instituteApi.getDocumentExtraction(doc.id),
        instituteApi.getDocumentAnomalies(doc.id).catch(() => []),
      ]);
      setExtractionData(data);
      setDocAnomalies(anomalies || []);
    } catch (err) {
      console.error('Failed to load extraction:', err);
    } finally {
      setIsLoadingExtraction(false);
    }
  };

  const handleStartEditField = (key: string, currentVal: string) => {
    setEditingFieldKey(key);
    setFieldEditValue(currentVal || '');
    setFieldSaveSuccess(null);
  };

  const handleSaveField = async (key: string) => {
    if (!drawerDoc) return;
    setIsSavingField(true);
    try {
      await instituteApi.correctField(drawerDoc.id, key, fieldEditValue);
      setFieldSaveSuccess(`Field "${key}" updated successfully!`);
      if (extractionData) {
        setExtractionData({
          ...extractionData,
          fields: extractionData.fields.map((f) =>
            f.key === key
              ? {
                  ...f,
                  corrected_value: fieldEditValue,
                  effective_value: fieldEditValue,
                  verified_by_user: true,
                  needs_review: false,
                }
              : f
          ),
        });
      }
      setEditingFieldKey(null);
      if (selectedAppId) {
        const rData = await instituteApi.getApplicationReadiness(selectedAppId);
        setReadinessData(rData);
      }
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update field.');
    } finally {
      setIsSavingField(false);
    }
  };

  const handleVerifyNow = async () => {
    if (!drawerDoc || isVerifying) return;
    setIsVerifying(true);
    setVerifyNotice(null);
    try {
      await instituteApi.verifyDocument(drawerDoc.id);
      const [updatedExt, updatedAnom, updatedDocs] = await Promise.all([
        instituteApi.getDocumentExtraction(drawerDoc.id),
        instituteApi.getDocumentAnomalies(drawerDoc.id).catch(() => []),
        instituteApi.getDocuments(),
      ]);
      setExtractionData(updatedExt);
      setDocAnomalies(updatedAnom || []);
      setDocuments(updatedDocs);
      const freshDoc = updatedDocs.find((d) => d.id === drawerDoc.id);
      if (freshDoc) setDrawerDoc(freshDoc);
      setVerifyNotice('Statutory verification completed successfully.');
    } catch (err: any) {
      console.error('Verification failed:', err);
      setVerifyNotice('Verification encountered an issue or requires manual scrutiny.');
    } finally {
      setIsVerifying(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Page Title Card */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <FileUp size={22} className="text-[#0B3C9D]" />
            <h2 className="text-xl font-bold text-[#0B3C9D] tracking-tight">
              Institutional Document Repository & Regulatory Checklists
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Dynamic regulatory checklist requirements, OCR verification, and readiness tracking with SHA-256 verification.
          </p>
        </div>

        {/* Category Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-[#0F2A5C] whitespace-nowrap">Category:</label>
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="text-xs font-semibold px-3 py-1.5 rounded-[6px] border border-slate-200 bg-slate-50 text-[#0F2A5C] focus:outline-none focus:border-[#F58220]"
          >
            <option value="EOA">Extension of Approval (EoA)</option>
            <option value="CHANGE_OF_NAME">Change of Name / Site</option>
            <option value="INTAKE_CHANGE">Intake Change / New Course</option>
            <option value="CLOSURE_MERGER">Closure / Merger</option>
          </select>
        </div>
      </div>

      {/* Application Readiness Card */}
      {readinessData && (
        <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <ShieldCheck size={20} className="text-[#0B3C9D]" />
              <div>
                <h3 className="text-base font-bold text-[#0B3C9D] tracking-tight flex items-center gap-2">
                  Application Readiness Assessment
                  <span className="text-[10px] font-semibold font-mono bg-blue-50 text-[#0B3C9D] border border-blue-200 px-2 py-0.5 rounded-full">
                    {readinessData.ruleset_name} ({readinessData.ruleset_version})
                  </span>
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Verified against the official Approval Process Handbook regulatory checklist.
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <StatusPill status={readinessData.status} />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-5">
            {/* Percentage Block */}
            <div className="p-4 bg-gradient-to-br from-slate-50 to-orange-50/40 rounded-[10px] border border-slate-200 flex flex-col justify-center items-center text-center">
              <div className="text-3xl font-extrabold text-[#F58220]">
                {readinessData.readiness_percentage}%
              </div>
              <div className="text-xs font-semibold text-[#0F2A5C] mt-1">Readiness Score</div>
              <div className="w-full bg-slate-200 h-1.5 rounded-full mt-3 overflow-hidden">
                <div
                  className="bg-[#F58220] h-full rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(readinessData.readiness_percentage, 100)}%` }}
                />
              </div>
              <span className="text-[11px] text-slate-500 mt-1.5">
                {readinessData.ready_items} of {readinessData.total_items} items ready
              </span>
            </div>

            {/* Missing or Expired Items List */}
            <div className="md:col-span-3 space-y-3">
              <h4 className="text-xs font-bold text-[#0F2A5C] uppercase tracking-wider flex items-center justify-between">
                <span>Regulatory Items Status & Deficiencies</span>
                <span className="text-[11px] text-slate-400 font-normal">
                  {readinessData.missing_items.length} missing / pending
                </span>
              </h4>

              {readinessData.items.filter((i) => i.status !== 'READY').length === 0 ? (
                <div className="p-4 bg-green-50 border border-green-200 rounded-[8px] text-xs font-medium text-[#1E7036] flex items-center gap-2">
                  <CheckCircle2 size={16} />
                  <span>All regulatory checklist items are verified, valid, and ready for review.</span>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-[180px] overflow-y-auto pr-1">
                  {readinessData.items
                    .filter((i) => i.status !== 'READY')
                    .map((item) => (
                      <div
                        key={item.checklist_item_id}
                        className="p-2.5 rounded-[8px] border border-slate-200 bg-slate-50/60 flex items-start justify-between gap-2 text-xs"
                      >
                        <div>
                          <div className="font-semibold text-[#0F2A5C] leading-snug line-clamp-1">
                            {item.document_type_name}
                          </div>
                          <div className="text-[11px] text-slate-500 font-mono mt-0.5">
                            {item.document_type_code}
                          </div>
                          {item.expiry_date && (
                            <div className="text-[10px] text-amber-700 mt-0.5">
                              Exp: {item.expiry_date} ({item.days_remaining}d left)
                            </div>
                          )}
                        </div>
                        <StatusPill status={item.status} className="text-[10px] py-0.5 px-2" />
                      </div>
                    ))}
                </div>
              )}

              {/* Specific Field Problems Alert */}
              {readinessData.field_problems.length > 0 && (
                <div className="mt-2 text-[11px] text-amber-800 bg-amber-50/80 border border-amber-200 rounded-lg p-2.5 flex items-start gap-2">
                  <AlertCircle size={14} className="shrink-0 mt-0.5 text-amber-600" />
                  <div className="space-y-0.5">
                    <span className="font-bold">Specific Field Discrepancies:</span>
                    <ul className="list-disc list-inside space-y-0.5">
                      {readinessData.field_problems.slice(0, 3).map((fp, idx) => (
                        <li key={idx}>
                          <span className="font-mono text-slate-700">{fp.document_type}</span>: {fp.problem}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Mandatory Checklist Status Strip */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <CheckSquare size={18} className="text-[#F58220]" />
            <h3 className="text-sm font-bold text-[#0F2A5C] tracking-tight">
              Required Documents Checklist for {selectedCategory} ({checklistStats.uploaded}/{checklistStats.total} Complete)
            </h3>
          </div>
          <div className="flex items-center gap-3 text-xs">
            <span className="px-2.5 py-1 rounded-full font-semibold bg-[#E2F6E6] text-[#1E7036]">
              Uploaded: {checklistStats.uploaded}
            </span>
            <span className="px-2.5 py-1 rounded-full font-semibold bg-[#FDE7E9] text-[#C62828]">
              Missing: {checklistStats.missing}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
          {checklistItems.map((item) => (
            <div
              key={item.id}
              onClick={() => setSelectedDocType(item.document_type_code)}
              className={`p-3 rounded-[8px] border text-xs cursor-pointer transition-all ${
                selectedDocType === item.document_type_code
                  ? 'border-[#F58220] bg-orange-50/40 shadow-sm'
                  : 'border-slate-100 hover:border-slate-300 bg-slate-50/40'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="font-semibold text-[#0F2A5C] leading-snug line-clamp-1">
                  {item.document_type_name}
                </div>
                <span
                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase shrink-0 ${
                    item.status === 'uploaded'
                      ? 'bg-[#E2F6E6] text-[#1E7036]'
                      : item.status === 'expired'
                      ? 'bg-[#FFF0D6] text-[#B25E00]'
                      : 'bg-[#FDE7E9] text-[#C62828]'
                  }`}
                >
                  {item.status}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1.5 text-[11px] text-slate-500">
                <span className="font-mono text-[#0B3C9D]">{item.document_type_code}</span>
                {item.min_validity_days_remaining ? (
                  <span className="flex items-center gap-1 text-[10px] text-amber-700">
                    <Clock size={10} /> min {item.min_validity_days_remaining}d
                  </span>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Drag-and-Drop Zone Card */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <label className="text-xs font-bold text-[#0F2A5C] flex items-center gap-1.5">
            Document Type to Attach:
          </label>
          <select
            value={selectedDocType}
            onChange={(e) => setSelectedDocType(e.target.value)}
            className="text-xs font-semibold px-3 py-1.5 rounded-[6px] border border-slate-200 bg-slate-50 text-[#0F2A5C] focus:outline-none focus:border-[#F58220]"
          >
            {checklistItems.map((ci) => (
              <option key={ci.id} value={ci.document_type_code}>
                {ci.document_type_code} — {ci.document_type_name}
              </option>
            ))}
            <option value="GENERAL">GENERAL — Other Institutional Document</option>
          </select>
        </div>

        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragging(false);
            handleFileUpload(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`w-full border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all ${
            isDragging
              ? 'border-[#F58220] bg-orange-50/50 scale-[0.99]'
              : 'border-[#F58220]/70 hover:border-[#F58220] hover:bg-slate-50/60'
          }`}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={(e) => handleFileUpload(e.target.files)}
            accept=".pdf,.jpg,.jpeg,.png"
            className="hidden"
          />

          <div className="w-14 h-14 rounded-full bg-[#FFF0D6] text-[#F58220] flex items-center justify-center mb-3 shadow-sm">
            {isUploading ? <Loader2 size={28} className="animate-spin" /> : <UploadCloud size={28} />}
          </div>

          <h3 className="text-sm font-bold text-[#0F2A5C]">
            {isUploading
              ? 'Validating Magic Bytes & Hashing...'
              : `Upload Document for ${selectedDocType}`}
          </h3>
          <p className="text-xs text-[#7A8699] max-w-md mt-1 leading-relaxed">
            Support formats: <strong className="text-slate-700">PDF, JPG, PNG</strong>.
            Files undergo magic byte inspection, SHA-256 integrity digest, and off-root storage.
          </p>

          <button
            type="button"
            className="mt-3 px-5 py-1.5 bg-[#F58220] hover:bg-[#E06F0F] text-white text-xs font-semibold rounded-[6px] shadow-sm select-none"
          >
            Browse File
          </button>
        </div>

        {/* Feedback Alerts */}
        {uploadSuccess && (
          <div className="mt-4 p-3 bg-green-50 border border-green-200 text-[#1E7036] text-xs font-semibold rounded-lg flex items-center gap-2">
            <CheckCircle2 size={16} />
            <span>{uploadSuccess}</span>
          </div>
        )}
        {uploadError && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 text-[#C62828] text-xs font-semibold rounded-lg flex items-center gap-2">
            <AlertCircle size={16} />
            <span>{uploadError}</span>
          </div>
        )}
      </div>

      {/* List of Uploaded Documents */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
        <h3 className="text-base font-bold text-[#0B3C9D] pb-4 border-b border-slate-100 tracking-tight">
          Uploaded Documents Archive ({documents.length})
        </h3>

        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#E3F0FF] text-[#0B3C9D] uppercase text-[11px] font-bold tracking-wider">
                <th className="py-3 px-4 rounded-l-md">File Details</th>
                <th className="py-3 px-4">Doc Type</th>
                <th className="py-3 px-4">MIME Type</th>
                <th className="py-3 px-4">Size</th>
                <th className="py-3 px-4">Uploaded On</th>
                <th className="py-3 px-4">SHA-256 Digest</th>
                <th className="py-3 px-4">OCR Status</th>
                <th className="py-3 px-4">Verification</th>
                <th className="py-3 px-4 text-center rounded-r-md">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={9} className="py-12 text-center text-slate-400">
                    <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                    Loading archive records...
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-10 text-center text-slate-400">
                    No documents uploaded yet. Use the drop zone above to attach institutional proofs.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => {
                  const ocrPillStatus =
                    doc.ocr_status === 'PROCESSING'
                      ? 'Processing'
                      : doc.ocr_status === 'DONE'
                      ? doc.status === 'Needs Attention'
                        ? 'Needs Attention'
                        : 'Done'
                      : doc.ocr_status === 'FAILED'
                      ? 'Needs Attention'
                      : doc.status || 'Uploaded';

                  return (
                    <tr key={doc.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-[#0F2A5C] flex items-center gap-2.5">
                        <File size={16} className="text-[#0B3C9D] shrink-0" />
                        <span className="truncate max-w-[200px]">{doc.original_filename}</span>
                      </td>
                      <td className="py-3.5 px-4 font-mono font-semibold text-[#0B3C9D]">
                        {doc.document_type_code || '—'}
                      </td>
                      <td className="py-3.5 px-4 text-slate-500 font-mono text-[11px]">
                        {doc.mime_type}
                      </td>
                      <td className="py-3.5 px-4 whitespace-nowrap">{formatBytes(doc.file_size)}</td>
                      <td className="py-3.5 px-4 whitespace-nowrap text-slate-500">
                        {new Date(doc.created_at).toLocaleDateString('en-GB')}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-[11px] text-slate-400">
                        {doc.sha256_hash.substring(0, 10)}...{doc.sha256_hash.substring(58)}
                      </td>
                      <td className="py-3.5 px-4">
                        <StatusPill status={ocrPillStatus} />
                      </td>
                      <td className="py-3.5 px-4">
                        <StatusPill status={formatVerificationStatus(doc.verification_status)} />
                      </td>
                      <td className="py-3.5 px-4">
                        <div className="flex items-center justify-center gap-1.5">
                          {/* View Extracted Data Drawer */}
                          <button
                            onClick={() => handleOpenDrawer(doc)}
                            title="View Extracted Data"
                            className="p-1.5 bg-[#FFF0D6] text-[#F58220] hover:bg-[#FFE0B2] rounded-[6px] transition-colors"
                          >
                            <Eye size={13} />
                          </button>

                          {/* Download Button */}
                          <a
                            href={`/api/institute/documents/${doc.id}/download`}
                            download
                            title="Download Document"
                            className="p-1.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded-[6px] transition-colors"
                          >
                            <Download size={13} />
                          </a>

                          {/* Delete Button */}
                          <button
                            onClick={() => handleDelete(doc.id, doc.original_filename)}
                            title="Delete Document"
                            className="p-1.5 bg-red-100 text-[#C62828] hover:bg-red-200 rounded-[6px] transition-colors"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Extracted Data Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={drawerDoc ? `Extracted Data — ${drawerDoc.original_filename}` : 'Extracted Document Data'}
        subtitle="Intelligent OCR Extraction, Verification & Regulatory Metadata"
        width="max-w-2xl"
      >
        {isLoadingExtraction ? (
          <div className="py-16 text-center text-slate-400">
            <Loader2 size={28} className="animate-spin mx-auto mb-2 text-[#F58220]" />
            Loading extracted fields & neural classification...
          </div>
        ) : !extractionData ? (
          <div className="py-12 text-center text-slate-400 text-xs">
            No extracted data available for this document yet.
          </div>
        ) : (
          <div className="space-y-5 text-xs text-slate-700">
            {/* Feedback Alert */}
            {fieldSaveSuccess && (
              <div className="p-3 bg-green-50 border border-green-200 text-[#1E7036] font-semibold rounded-lg flex items-center gap-2">
                <CheckCircle2 size={16} />
                <span>{fieldSaveSuccess}</span>
              </div>
            )}
            {verifyNotice && (
              <div className="p-3 bg-blue-50 border border-blue-200 text-[#0B3C9D] font-semibold rounded-lg flex items-center gap-2">
                <CheckCircle2 size={16} />
                <span>{verifyNotice}</span>
              </div>
            )}

            {/* Statutory Verification Section */}
            <div className="p-4 bg-white border border-slate-200 rounded-[10px] shadow-xs space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2 flex-wrap">
                  <ShieldCheck size={16} className="text-[#0B3C9D]" />
                  <span className="font-bold text-[#0F2A5C] text-xs">Statutory Verification</span>
                  <StatusPill
                    status={formatVerificationStatus(extractionData.verification?.status || drawerDoc?.verification_status)}
                  />
                  {extractionData.verification?.is_simulated && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-300">
                      Simulated source
                    </span>
                  )}
                </div>

                <button
                  onClick={handleVerifyNow}
                  disabled={isVerifying}
                  className="px-3 py-1.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded-[6px] text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors disabled:opacity-50 select-none self-start sm:self-auto cursor-pointer"
                >
                  {isVerifying ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                  Verify now
                </button>
              </div>

              {/* Source & Checked-At Meta */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] bg-slate-50/70 p-2.5 rounded-lg border border-slate-100">
                <div>
                  <span className="text-slate-400 block">Issuing Authority Source:</span>
                  <span className="font-semibold text-slate-800">
                    {extractionData.verification?.source_name || drawerDoc?.verification_source || 'Authority Registry / Digital Signature'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block">Checked At:</span>
                  <span className="font-semibold text-slate-800">
                    {extractionData.verification?.checked_at
                      ? new Date(extractionData.verification.checked_at).toLocaleString()
                      : 'Not verified yet'}
                  </span>
                </div>
              </div>

              {extractionData.verification?.message && (
                <div className="text-[11px] text-slate-600 bg-slate-50 p-2 rounded border border-slate-100">
                  <span className="font-semibold text-slate-700">Notice: </span>
                  {extractionData.verification.message}
                </div>
              )}

              {/* Per-field Submitted vs Official Comparisons Table */}
              <div className="mt-2">
                <span className="text-[11px] font-bold text-[#0F2A5C] uppercase tracking-wider block mb-1.5">
                  Field Comparison (Submitted vs Official)
                </span>
                {extractionData.verification?.all_comparisons && extractionData.verification.all_comparisons.length > 0 ? (
                  <div className="overflow-x-auto border border-slate-200 rounded-lg">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="bg-[#E3F0FF] text-[#0B3C9D] text-[10px] font-bold uppercase tracking-wider">
                          <th className="py-2 px-3">Field</th>
                          <th className="py-2 px-3">Submitted Value</th>
                          <th className="py-2 px-3">Official Value</th>
                          <th className="py-2 px-3 text-center">Result</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {extractionData.verification.all_comparisons.map((comp, cIdx) => (
                          <tr key={cIdx} className="hover:bg-slate-50/60">
                            <td className="py-2 px-3 font-mono text-[11px] font-semibold text-slate-700">
                              {comp.field.replace(/_/g, ' ')}
                            </td>
                            <td className="py-2 px-3 text-slate-800 font-medium break-all">
                              {String(comp.submitted ?? '—')}
                            </td>
                            <td className="py-2 px-3 text-slate-800 font-medium break-all">
                              {String(comp.official ?? '—')}
                            </td>
                            <td className="py-2 px-3 text-center">
                              {comp.matched ? (
                                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#1E7036] bg-[#E2F6E6] px-2 py-0.5 rounded-full">
                                  <CheckCircle2 size={12} /> Matched
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-[#C62828] bg-[#FDE7E9] px-2 py-0.5 rounded-full">
                                  <XCircle size={12} /> Mismatched
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-[11px] text-slate-400 italic p-3 bg-slate-50 rounded border border-slate-100 text-center">
                    No field comparisons recorded yet. Click &quot;Verify now&quot; to cross-reference against official registers.
                  </div>
                )}
              </div>
            </div>

            {/* Preliminary Anomaly Indicators Section */}
            <div className="p-4 bg-white border border-slate-200 rounded-[10px] shadow-xs space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100 flex-wrap gap-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <ShieldAlert size={16} className="text-amber-600" />
                  <span className="font-bold text-[#0F2A5C] text-xs">Preliminary Anomaly Indicators</span>
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-300">
                    Needs verification
                  </span>
                </div>
                <span className="text-[11px] font-mono text-slate-500">
                  {docAnomalies.length} {docAnomalies.length === 1 ? 'indicator' : 'indicators'} detected
                </span>
              </div>

              {docAnomalies.length === 0 ? (
                <div className="text-[11px] text-slate-500 bg-slate-50 p-3 rounded-lg border border-slate-100 flex items-center gap-2">
                  <CheckCircle2 size={14} className="text-emerald-600 shrink-0" />
                  <span>No potential anomaly indicators detected. Document passed preliminary automated screening.</span>
                </div>
              ) : (
                <div className="space-y-3">
                  {docAnomalies.map((flag) => {
                    const isTamper = flag.detector === 'ImageTamperDetector' || flag.has_overlay;
                    return (
                      <div
                        key={flag.id}
                        className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/70 space-y-2 hover:bg-slate-50 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2 flex-wrap">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="font-mono text-[11px] font-bold text-[#0B3C9D]">
                              {flag.code}
                            </span>
                            <span className="text-[10px] text-slate-400 font-medium">
                              ({flag.detector})
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <StatusPill status={flag.severity} />
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-purple-100 text-purple-800 border border-purple-200">
                              {flag.review_status.replace(/_/g, ' ')}
                            </span>
                          </div>
                        </div>

                        <p className="text-xs text-slate-700 leading-relaxed">
                          {flag.reason}
                        </p>

                        <div className="text-[11px] text-slate-500 flex items-start gap-1">
                          <strong className="text-slate-700 shrink-0">Action:</strong>
                          <span>{flag.recommended_action}</span>
                        </div>

                        {/* TAMPERING EVIDENCE MAP */}
                        {isTamper && drawerDoc && (
                          <div className="mt-3 p-3 bg-white rounded-lg border border-slate-200 space-y-2.5">
                            <div className="flex items-center justify-between">
                              <span className="font-bold text-[#0F2A5C] text-[11px] flex items-center gap-1.5">
                                <Eye size={13} className="text-[#0B3C9D]" />
                                Tampering Evidence Map (Visual Irregularities)
                              </span>
                              <span className="text-[10px] font-mono text-slate-500">
                                Preliminary Scrutiny Heatmap
                              </span>
                            </div>

                            {/* Overlay Image */}
                            <div className="relative overflow-hidden rounded-lg border border-slate-300 bg-slate-900/95 flex items-center justify-center p-2">
                              <img
                                src={`/api/institute/documents/${drawerDoc.id}/anomalies/${flag.id}/overlay`}
                                alt="Visual Tamper Overlay"
                                className="max-h-64 object-contain rounded"
                                onError={(e) => {
                                  (e.target as HTMLElement).style.display = 'none';
                                }}
                              />
                            </div>

                            {/* Highlighted Bounding Box Regions List */}
                            {flag.evidence_json && flag.evidence_json.length > 0 && (
                              <div className="space-y-1.5 pt-1">
                                <span className="text-[10px] font-bold text-slate-700 uppercase tracking-wider block">
                                  Highlighted Irregularity Regions ({flag.evidence_json.length})
                                </span>
                                {flag.evidence_json.map((reg, regIdx) => (
                                  <div
                                    key={regIdx}
                                    className="p-2.5 bg-red-50/70 border border-red-200 rounded-md text-xs space-y-1"
                                  >
                                    <div className="flex items-center justify-between text-[11px]">
                                      <span className="font-bold text-red-900 font-mono">
                                        Region #{regIdx + 1} {reg.page ? `• Page ${reg.page}` : ''}
                                      </span>
                                      {reg.type && (
                                        <span className="text-[10px] font-semibold text-red-800 bg-white border border-red-200 px-1.5 py-0.5 rounded">
                                          {reg.type}
                                        </span>
                                      )}
                                    </div>
                                    {reg.bbox && (
                                      <div className="text-[10px] font-mono text-slate-500">
                                        Region Bounding Box: [{reg.bbox.join(', ')}]
                                      </div>
                                    )}
                                    <p className="text-[11px] text-red-800 leading-normal">
                                      {reg.reason || 'Visual compression, repetition cluster, or layout irregularity detected; preliminary indicator requiring verification.'}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Classification Card */}
            {extractionData.classification && (
              <div className="p-4 bg-slate-50 border border-slate-200 rounded-[10px] space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#0F2A5C] flex items-center gap-1.5">
                    <Sparkles size={14} className="text-[#F58220]" />
                    Document Classification Prediction
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#E2F6E6] text-[#1E7036]">
                    Score: {Math.round(extractionData.classification.score * 100)}%
                  </span>
                </div>
                <div className="flex items-center gap-2 font-mono text-sm text-[#0B3C9D] font-bold">
                  {extractionData.classification.predicted_type}
                </div>
                {extractionData.classification.mismatch_flag && (
                  <div className="p-2.5 bg-amber-50 border border-amber-200 text-amber-800 rounded-md text-[11px] flex items-start gap-1.5">
                    <AlertCircle size={14} className="shrink-0 mt-0.5 text-amber-600" />
                    <span>{extractionData.classification.warning_message}</span>
                  </div>
                )}
              </div>
            )}

            {/* Validity Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 p-3.5 bg-slate-50 rounded-[8px] border border-slate-100 text-[11px]">
              <div>
                <span className="text-slate-400 block">Expiry Date:</span>
                <span className="font-bold text-[#0F2A5C]">{extractionData.expiry_date || 'N/A'}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Days Left:</span>
                <span className="font-bold text-[#0F2A5C]">
                  {extractionData.days_remaining !== undefined ? `${extractionData.days_remaining}d` : 'N/A'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block">Status:</span>
                <span className="font-bold text-[#0F2A5C]">
                  {extractionData.is_expired ? 'Expired' : 'Valid'}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block">OCR Engine:</span>
                <span className="font-bold text-[#0B3C9D]">{extractionData.ocr_status}</span>
              </div>
            </div>

            {/* Fields List */}
            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider text-[11px] mb-3">
                Extracted Fields ({extractionData.fields.length})
              </h4>

              {extractionData.fields.length === 0 ? (
                <div className="p-6 text-center text-slate-400 border border-dashed rounded-lg">
                  No structured fields detected in this document.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {extractionData.fields.map((field) => {
                    const isEditing = editingFieldKey === field.key;
                    const displayValue = field.corrected_value || field.normalized_value || field.value || '—';

                    return (
                      <div
                        key={field.key}
                        className="p-3.5 rounded-[8px] border border-slate-200 bg-white hover:border-slate-300 transition-colors"
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div>
                            <span className="font-mono text-[11px] text-[#0B3C9D] font-bold block">
                              {field.key}
                            </span>
                            <span className="text-[10px] text-slate-400">
                              Page {field.page_no} • {field.source} • Conf: {Math.round(field.confidence * 100)}%
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5">
                            {field.verified_by_user && (
                              <span className="text-[10px] font-semibold text-[#1E7036] bg-[#E2F6E6] px-2 py-0.5 rounded-full">
                                Verified
                              </span>
                            )}
                            {!isEditing && (
                              <button
                                onClick={() => handleStartEditField(field.key, displayValue === '—' ? '' : displayValue)}
                                className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-[#F58220] transition-colors"
                                title="Edit Field Value"
                              >
                                <Edit2 size={13} />
                              </button>
                            )}
                          </div>
                        </div>

                        {/* Value Display or Edit Input */}
                        <div className="mt-2">
                          {isEditing ? (
                            <div className="flex items-center gap-2 mt-1">
                              <input
                                type="text"
                                value={fieldEditValue}
                                onChange={(e) => setFieldEditValue(e.target.value)}
                                className="flex-1 px-2.5 py-1 text-xs border border-[#F58220] rounded-[6px] focus:outline-none bg-orange-50/20"
                                autoFocus
                              />
                              <button
                                onClick={() => handleSaveField(field.key)}
                                disabled={isSavingField}
                                className="px-3 py-1 bg-[#F58220] hover:bg-[#E06F0F] text-white rounded-[6px] text-xs font-semibold flex items-center gap-1 shadow-sm"
                              >
                                {isSavingField ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                                Save
                              </button>
                              <button
                                onClick={() => setEditingFieldKey(null)}
                                className="p-1 text-slate-400 hover:text-slate-600 rounded"
                              >
                                <X size={14} />
                              </button>
                            </div>
                          ) : (
                            <div className="font-semibold text-slate-800 break-all text-xs bg-slate-50/80 px-2.5 py-1.5 rounded border border-slate-100">
                              {displayValue}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
