import React, { useState, useEffect } from 'react';
import {
  Clock,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  RotateCcw,
  Eye,
  FileText,
  UserCheck,
  Building,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import { adminApi, VerificationQueueItemDetailed, DocumentTypeOut } from '../../api/admin';
import { StatusPill } from '../../components/StatusPill';
import { Drawer } from '../../components/Drawer';
import { Modal } from '../../components/Modal';

export const AdminVerificationQueuePage: React.FC = () => {
  const [items, setItems] = useState<VerificationQueueItemDetailed[]>([]);
  const [docTypes, setDocTypes] = useState<DocumentTypeOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [docTypeFilter, setDocTypeFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected for Drawer Detail
  const [selectedItem, setSelectedItem] = useState<VerificationQueueItemDetailed | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Decision Modal State
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState(false);
  const [decisionType, setDecisionType] = useState<'APPROVED' | 'REJECTED' | 'REUPLOAD_REQUESTED'>('APPROVED');
  const [decisionReason, setDecisionReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [queueData, typesData] = await Promise.all([
        adminApi.listVerificationQueue({
          status: statusFilter || undefined,
          document_type: docTypeFilter || undefined,
          search: searchQuery || undefined,
        }),
        adminApi.listDocumentTypes(),
      ]);
      setItems(queueData);
      setDocTypes(typesData);
    } catch (err) {
      console.error('Failed to load verification queue:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter, docTypeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  const handleOpenDetail = (item: VerificationQueueItemDetailed) => {
    setSelectedItem(item);
    setIsDrawerOpen(true);
  };

  const openDecisionModal = (type: 'APPROVED' | 'REJECTED' | 'REUPLOAD_REQUESTED', item?: VerificationQueueItemDetailed) => {
    if (item) setSelectedItem(item);
    setDecisionType(type);
    setDecisionReason('');
    setActionSuccess(null);
    setIsDecisionModalOpen(true);
  };

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem) return;
    if (!decisionReason.trim() || decisionReason.trim().length < 3) {
      alert('Please provide a substantive rationale (at least 3 characters) for the audit trail.');
      return;
    }

    setIsSubmitting(true);
    try {
      const updated = await adminApi.reviewDocumentDecision(selectedItem.document_id, {
        decision: decisionType,
        reason: decisionReason.trim(),
      });
      setActionSuccess(`Decision recorded: ${decisionType} for ${selectedItem.document_filename}`);
      setIsDecisionModalOpen(false);
      setSelectedItem(updated);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit review decision.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12 animate-fade-in">
      {/* Header Banner */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Clock size={22} className="text-[#0B3C9D]" />
            <h1 className="text-xl font-bold text-[#0B3C9D] tracking-tight">
              Statutory Verification Scrutiny Queue
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Manual and automated external registry verification. Core rule:{' '}
            <strong className="text-[#0F2A5C]">"Rules decide, AI explains, Officials approve."</strong>
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold transition-colors shrink-0"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin text-[#F58220]' : ''} />
          <span>Refresh Queue</span>
        </button>
      </div>

      {actionSuccess && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-bold flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-600" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-600 hover:text-emerald-900 text-xs font-bold">
            Dismiss
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-[12px] p-4 shadow-[0_4px_12px_rgba(0,0,0,0.06)] border border-slate-200 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by filename, institute name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-9 pr-3 rounded-lg border border-slate-200 text-xs focus:border-[#0B3C9D] outline-none"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 h-10 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded-lg text-xs font-semibold shrink-0"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1 text-xs text-slate-500 font-semibold">
            <Filter size={14} />
            <span>Filters:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 text-xs bg-white text-slate-700 focus:border-[#0B3C9D] outline-none"
          >
            <option value="">Status: All Unresolved</option>
            <option value="MANUAL_REVIEW_REQUIRED">Manual Review Required</option>
            <option value="SOURCE_UNAVAILABLE">Source Unavailable</option>
            <option value="MISMATCH_DETECTED">Mismatch Detected</option>
            <option value="VERIFICATION_PENDING">Verification Pending</option>
            <option value="VERIFIED">Verified (Approved)</option>
            <option value="ALL">Show All Statuses</option>
          </select>

          <select
            value={docTypeFilter}
            onChange={(e) => setDocTypeFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 text-xs bg-white text-slate-700 focus:border-[#0B3C9D] outline-none max-w-[200px]"
          >
            <option value="">Doc Type: All</option>
            {docTypes.map((dt) => (
              <option key={dt.code} value={dt.code}>
                {dt.name} ({dt.code})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Verification Table */}
      <div className="bg-white rounded-[12px] shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#E3F0FF] text-[#0B3C9D] uppercase text-[11px] font-bold tracking-wider">
                <th className="py-3 px-4">Institute</th>
                <th className="py-3 px-3">Document Type</th>
                <th className="py-3 px-3">File Name</th>
                <th className="py-3 px-3">Current Status</th>
                <th className="py-3 px-3 text-center">Age</th>
                <th className="py-3 px-3">Assigned Officer</th>
                <th className="py-3 px-4 text-center">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                    <span>Loading statutory verification queue...</span>
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <CheckCircle2 size={28} className="mx-auto mb-2 text-emerald-500 opacity-60" />
                    <p className="font-semibold text-slate-600">Verification queue is clear!</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      No documents currently require manual review or external authority action.
                    </p>
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={`${item.document_id}-${item.id}`} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-[#0F2A5C] flex items-center gap-1.5">
                        <Building size={14} className="text-slate-400 shrink-0" />
                        <span className="truncate max-w-[200px]" title={item.institute_name}>
                          {item.institute_name}
                        </span>
                      </div>
                      <span className="text-[11px] text-slate-400 font-mono">ID: #{item.institute_id}</span>
                    </td>

                    <td className="py-3 px-3">
                      <span className="inline-block px-2 py-0.5 rounded bg-blue-50 text-[#0B3C9D] text-[11px] font-bold">
                        {item.document_type_code || 'DOCUMENT'}
                      </span>
                      <p className="text-[10px] text-slate-500 truncate max-w-[150px]">
                        {item.document_type_name}
                      </p>
                    </td>

                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5">
                        <FileText size={14} className="text-slate-400 shrink-0" />
                        <span className="font-semibold text-slate-800 truncate max-w-[180px]" title={item.document_filename}>
                          {item.document_filename}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {Math.round(item.file_size / 1024)} KB
                      </span>
                    </td>

                    <td className="py-3 px-3">
                      <StatusPill status={item.status} />
                      {item.manual_decision && (
                        <div className="text-[10px] text-slate-500 mt-1 font-semibold">
                          Overridden: <span className="text-emerald-700 font-bold">{item.manual_decision}</span>
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-3 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-bold ${
                        item.age_days > 7 ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {item.age_days}d
                      </span>
                    </td>

                    <td className="py-3 px-3">
                      <div className="flex items-center gap-1.5 text-slate-600">
                        <UserCheck size={14} className={item.assigned_officer_name ? 'text-[#0B3C9D]' : 'text-slate-300'} />
                        <span className="text-[11px] truncate max-w-[130px]">
                          {item.assigned_officer_name || 'Unassigned'}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => handleOpenDetail(item)}
                          className="px-2.5 py-1.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded text-[11px] font-semibold inline-flex items-center gap-1 transition-colors"
                          title="Inspect Extracted Fields & Timeline"
                        >
                          <Eye size={12} />
                          <span>Review</span>
                        </button>
                        <button
                          onClick={() => openDecisionModal('APPROVED', item)}
                          className="p-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded transition-colors"
                          title="Approve as Verified"
                        >
                          <CheckCircle2 size={15} />
                        </button>
                        <button
                          onClick={() => openDecisionModal('REJECTED', item)}
                          className="p-1.5 bg-red-50 hover:bg-red-100 text-red-700 rounded transition-colors"
                          title="Reject (Mismatch Detected)"
                        >
                          <XCircle size={15} />
                        </button>
                        <button
                          onClick={() => openDecisionModal('REUPLOAD_REQUESTED', item)}
                          className="p-1.5 bg-amber-50 hover:bg-amber-100 text-amber-700 rounded transition-colors"
                          title="Request Re-upload"
                        >
                          <RotateCcw size={15} />
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

      {/* Detail Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedItem?.document_filename || 'Document Verification Scrutiny'}
        subtitle={`${selectedItem?.institute_name} (${selectedItem?.document_type_code || 'Document'})`}
      >
        {selectedItem && (
          <div className="space-y-6 text-xs">
            {/* Automated vs Manual Decision Banner */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-200">
                <span className="text-slate-500 font-semibold">Verification Status:</span>
                <StatusPill status={selectedItem.status} />
              </div>
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <span className="text-slate-400 block">Original Automated Status:</span>
                  <span className="font-bold text-slate-700">{selectedItem.original_status || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-400 block">Statutory Source:</span>
                  <span className="font-bold text-[#0B3C9D]">{selectedItem.source_name || 'External Registry'}</span>
                </div>
              </div>

              {selectedItem.manual_decision && (
                <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-[#0B3C9D]">Officer Overridden Decision:</span>
                    <span className="font-bold text-emerald-800 uppercase">{selectedItem.manual_decision}</span>
                  </div>
                  <p className="text-slate-700 text-[11px] italic">"{selectedItem.manual_reason}"</p>
                  <span className="text-[10px] text-slate-400 mt-1 block">
                    Reviewed on {selectedItem.manual_reviewed_at ? new Date(selectedItem.manual_reviewed_at).toLocaleString('en-GB') : 'N/A'}
                  </span>
                </div>
              )}
            </div>

            {/* Side-by-Side Comparison: Extracted vs Official Registry Values */}
            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-2 flex items-center justify-between">
                <span>Side-by-Side Field Verification</span>
                <span className="text-[10px] text-slate-400 font-normal">Extracted OCR vs Authority Data</span>
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {/* Extracted Fields */}
                <div className="p-3 bg-white border border-slate-200 rounded-lg shadow-xs">
                  <div className="font-bold text-slate-700 border-b border-slate-100 pb-1.5 mb-2 flex items-center gap-1.5">
                    <FileText size={13} className="text-[#0B3C9D]" />
                    <span>Extracted Document Values</span>
                  </div>
                  {Object.keys(selectedItem.extracted_fields || {}).length === 0 ? (
                    <p className="text-slate-400 italic text-[11px]">No OCR fields extracted yet.</p>
                  ) : (
                    <div className="space-y-1.5 font-mono text-[11px]">
                      {Object.entries(selectedItem.extracted_fields).map(([k, v]) => (
                        <div key={k} className="flex justify-between border-b border-slate-50 py-1">
                          <span className="text-slate-500 font-sans">{k}:</span>
                          <span className="text-slate-900 font-bold max-w-[160px] truncate" title={String(v)}>
                            {String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Official Statutory Registry Record */}
                <div className="p-3 bg-white border border-slate-200 rounded-lg shadow-xs">
                  <div className="font-bold text-slate-700 border-b border-slate-100 pb-1.5 mb-2 flex items-center gap-1.5">
                    <CheckCircle2 size={13} className="text-emerald-600" />
                    <span>Official Authority Record</span>
                  </div>
                  {Object.keys(selectedItem.official_values || {}).length === 0 ? (
                    <p className="text-slate-400 italic text-[11px]">No external authority record matched.</p>
                  ) : (
                    <div className="space-y-1.5 font-mono text-[11px]">
                      {Object.entries(selectedItem.official_values).map(([k, v]) => (
                        <div key={k} className="flex justify-between border-b border-slate-50 py-1">
                          <span className="text-slate-500 font-sans">{k}:</span>
                          <span className="text-emerald-800 font-bold max-w-[160px] truncate" title={String(v)}>
                            {String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Mismatched Fields Alert if any */}
            {selectedItem.mismatched_fields && selectedItem.mismatched_fields.length > 0 && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-xl text-amber-900">
                <div className="flex items-center gap-1.5 font-bold mb-1">
                  <AlertTriangle size={14} className="text-amber-600" />
                  <span>Detected Discrepancies (Needs Verification):</span>
                </div>
                <div className="space-y-1 text-[11px]">
                  {selectedItem.mismatched_fields.map((mf, idx) => (
                    <div key={idx} className="flex justify-between bg-white/60 px-2 py-1 rounded">
                      <span className="font-semibold">{mf.field || 'Field'}:</span>
                      <span className="font-mono text-red-700">
                        Extracted: {String(mf.extracted)} vs Expected: {String(mf.expected)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Verification Timeline */}
            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-3">
                Scrutiny & Pipeline Timeline
              </h4>
              <div className="space-y-3 border-l-2 border-[#0B3C9D] pl-4 py-1">
                {(selectedItem.timeline || []).map((tl, i) => (
                  <div key={i} className="relative">
                    <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-[#0B3C9D]" />
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[#0F2A5C] text-xs">{tl.event}</span>
                      <span className="text-[10px] text-slate-400">
                        {tl.timestamp ? new Date(tl.timestamp).toLocaleString('en-GB') : ''}
                      </span>
                    </div>
                    <p className="text-slate-600 mt-0.5 text-xs">{tl.notes}</p>
                    <span className="text-[10px] text-[#0B3C9D] font-semibold block mt-0.5">
                      Actor: {tl.actor}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Action Bar inside Drawer */}
            <div className="pt-4 border-t border-slate-200 space-y-2">
              <span className="text-slate-500 font-semibold block">Record Scrutiny Determination:</span>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => openDecisionModal('APPROVED')}
                  className="py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <CheckCircle2 size={14} />
                  <span>Approve</span>
                </button>
                <button
                  onClick={() => openDecisionModal('REJECTED')}
                  className="py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <XCircle size={14} />
                  <span>Reject</span>
                </button>
                <button
                  onClick={() => openDecisionModal('REUPLOAD_REQUESTED')}
                  className="py-2.5 bg-[#F58220] hover:bg-[#E06F0F] text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors"
                >
                  <RotateCcw size={14} />
                  <span>Re-upload</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </Drawer>

      {/* Decision Modal */}
      {selectedItem && (
        <Modal
          isOpen={isDecisionModalOpen}
          onClose={() => setIsDecisionModalOpen(false)}
          title={
            decisionType === 'APPROVED'
              ? 'Confirm Approval as Verified'
              : decisionType === 'REJECTED'
              ? 'Confirm Rejection (Mismatch)'
              : 'Request Document Re-upload'
          }
          subtitle={`Target: ${selectedItem.document_filename} (${selectedItem.institute_name})`}
          maxWidth="max-w-[640px]"
          footer={
            <>
              <button
                type="button"
                onClick={() => setIsDecisionModalOpen(false)}
                className="h-11 px-5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmitting || !decisionReason.trim()}
                onClick={(e) => handleDecisionSubmit(e as any)}
                className={`h-11 px-6 text-white font-bold rounded-xl shadow-sm transition-colors flex items-center gap-2 text-sm disabled:opacity-50 ${
                  decisionType === 'APPROVED'
                    ? 'bg-emerald-600 hover:bg-emerald-700'
                    : decisionType === 'REJECTED'
                    ? 'bg-red-600 hover:bg-red-700'
                    : 'bg-[#F58220] hover:bg-[#E06F0F]'
                }`}
              >
                {isSubmitting && <Loader2 size={16} className="animate-spin" />}
                <span>Confirm Decision</span>
              </button>
            </>
          }
        >
          <div className="space-y-6">
            <p className="text-xs text-slate-500 leading-relaxed">
              Your determination will override the automated verification status while preserving the original record in the append-only audit trail.
            </p>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Mandatory Officer Rationale <span className="text-red-500">*</span>
              </label>
              <textarea
                required
                rows={4}
                placeholder="State clear reasons (e.g. physical register verified, seal authenticated, or deficiency observed)..."
                value={decisionReason}
                onChange={(e) => setDecisionReason(e.target.value)}
                className="w-full p-3.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D] text-slate-800 text-sm resize-none"
              />
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
