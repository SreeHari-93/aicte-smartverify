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
} from 'lucide-react';
import { instituteApi, DocumentItem, InstituteChecklistItem } from '../../api/institute';
import { StatusPill } from '../../components/StatusPill';

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

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [docsRes, checklistRes] = await Promise.all([
        instituteApi.getDocuments(),
        instituteApi.getChecklist(selectedCategory),
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
      const newDoc = await instituteApi.uploadDocument(file, undefined, docTypeCode);
      setUploadSuccess(`"${file.name}" uploaded successfully for type ${docTypeCode || 'General'}!`);
      setDocuments((prev) => [newDoc, ...prev]);
      // Refresh checklist
      const chk = await instituteApi.getChecklist(selectedCategory);
      if (chk && chk.items) {
        setChecklistItems(chk.items);
        setChecklistStats({
          total: chk.total_required,
          uploaded: chk.uploaded_count,
          missing: chk.missing_count,
        });
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
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to delete document.');
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
            Dynamic regulatory checklist requirements and secure tamper-evident storage with SHA-256 verification.
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
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-center rounded-r-md">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                    Loading archive records...
                  </td>
                </tr>
              ) : documents.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-slate-400">
                    No documents uploaded yet. Use the drop zone above to attach institutional proofs.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
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
                      <StatusPill status={doc.status} />
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center justify-center gap-2">
                        {/* Download / View Button */}
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
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
