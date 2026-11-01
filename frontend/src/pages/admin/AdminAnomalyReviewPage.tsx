import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  CheckCircle2,
  HelpCircle,
  TrendingUp,
  FileText,
  Eye,
  Loader2,
  RefreshCw,
  Layers,
  Image,
  ThumbsUp,
  ThumbsDown,
} from 'lucide-react';
import { adminApi, AdminAnomalyFlagOut } from '../../api/admin';
import { StatusPill } from '../../components/StatusPill';
import { Drawer } from '../../components/Drawer';
import { Modal } from '../../components/Modal';

export const AdminAnomalyReviewPage: React.FC = () => {
  const [flags, setFlags] = useState<AdminAnomalyFlagOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [severityFilter, setSeverityFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [detectorFilter, setDetectorFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Drawer / Inspector
  const [selectedFlag, setSelectedFlag] = useState<AdminAnomalyFlagOut | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Decision Modal
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [chosenDecision, setChosenDecision] = useState<'Verified – no concern' | 'Needs institute clarification' | 'Escalate'>('Verified – no concern');
  const [decisionNote, setDecisionNote] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const data = await adminApi.listAnomalies({
        severity: severityFilter || undefined,
        status: statusFilter || undefined,
        detector: detectorFilter || undefined,
        search: searchQuery || undefined,
      });
      setFlags(data);
    } catch (err) {
      console.error('Failed to load anomalies:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [severityFilter, statusFilter, detectorFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  // Feedback State
  const [, setFeedbackGiven] = useState<boolean | null>(null);
  const [feedbackNote, setFeedbackNote] = useState('');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const handleOpenDetail = (flag: AdminAnomalyFlagOut) => {
    setSelectedFlag(flag);
    setFeedbackGiven(null);
    setFeedbackNote('');
    setFeedbackMessage(null);
    setIsDrawerOpen(true);
  };

  const handleFeedback = async (isCorrect: boolean) => {
    if (!selectedFlag) return;
    setIsSubmittingFeedback(true);
    try {
      await adminApi.submitAiFeedback({
        target_type: 'ANOMALY',
        target_id: selectedFlag.id,
        document_id: selectedFlag.document_id,
        is_correct: isCorrect,
        correction_notes: feedbackNote.trim() || undefined,
      });
      setFeedbackGiven(isCorrect);
      setFeedbackMessage(isCorrect ? 'Detector result marked as valid alert' : 'Detector result marked as false alarm');
    } catch (err) {
      console.error('Failed to submit AI feedback:', err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const openDecisionModal = (decision: 'Verified – no concern' | 'Needs institute clarification' | 'Escalate', flag?: AdminAnomalyFlagOut) => {
    if (flag) setSelectedFlag(flag);
    setChosenDecision(decision);
    setDecisionNote('');
    setActionSuccess(null);
    setIsModalOpen(true);
  };

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFlag) return;
    if (!decisionNote.trim() || decisionNote.trim().length < 3) {
      alert('A review note (minimum 3 characters) is required for audit trail compliance.');
      return;
    }

    setIsSubmitting(true);
    try {
      const updated = await adminApi.recordAnomalyDecision(selectedFlag.id, {
        decision: chosenDecision,
        note: decisionNote.trim(),
      });
      setActionSuccess(`Determination saved: "${chosenDecision}" for Flag #${selectedFlag.id}`);
      setSelectedFlag(updated);
      setIsModalOpen(false);
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit anomaly decision.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 pb-12 animate-fade-in">
      {/* Header Banner with Principle */}
      {/* Header */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Anomaly review
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Rules decide, AI explains, Officials approve. Items flagged as needs verification or potential anomaly.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-white border border-slate-300 hover:border-slate-400 text-slate-700 rounded-lg text-xs font-semibold transition-colors shrink-0 shadow-sm"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin text-[#0B3C9D]' : ''} />
          <span>Refresh</span>
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
      <div className="bg-white rounded-xl p-4 shadow-sm border border-slate-200 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search by code, detector, reason, or document..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-9 pr-3 rounded-lg border border-slate-300 text-xs focus:border-[#0B3C9D] outline-none placeholder:text-slate-500 text-slate-800"
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
          <div className="flex items-center gap-1 text-xs text-slate-600 font-semibold">
            <Filter size={14} />
            <span>Filters:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-300 text-xs bg-white text-slate-700 focus:border-[#0B3C9D] outline-none"
          >
            <option value="">Status: All</option>
            <option value="OPEN">Open (Needs Scrutiny)</option>
            <option value="CONFIRMED_OK">Verified – No Concern</option>
            <option value="NEEDS_ACTION">Clarification Requested</option>
            <option value="ESCALATED">Escalated</option>
            <option value="DISMISSED">Dismissed</option>
          </select>

          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-300 text-xs bg-white text-slate-700 focus:border-[#0B3C9D] outline-none"
          >
            <option value="">Severity: All</option>
            <option value="HIGH">High Severity</option>
            <option value="MEDIUM">Medium Severity</option>
            <option value="LOW">Low Severity</option>
            <option value="INFO">Informational</option>
          </select>

          <select
            value={detectorFilter}
            onChange={(e) => setDetectorFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-300 text-xs bg-white text-slate-700 focus:border-[#0B3C9D] outline-none"
          >
            <option value="">Detector: All</option>
            <option value="DuplicateDetector">Duplicate Detector</option>
            <option value="MetadataDetector">Metadata Detector</option>
            <option value="DateAnomalyDetector">Date Anomaly Detector</option>
            <option value="IdentifierDetector">Identifier Detector</option>
            <option value="ImageTamperDetector">Image Tamper Detector</option>
            <option value="VerificationConflictDetector">Verification Conflict Detector</option>
          </select>
        </div>
      </div>

      {/* Main Anomaly Flags Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="table-container">
          <table className="aicte-table">
            <thead>
              <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-xs">
                <th className="py-2.5 px-3 w-[15%]">Severity & flag</th>
                <th className="py-2.5 px-3 w-[22%]">Institute & document</th>
                <th className="py-2.5 px-3 w-[25%]">Potential anomaly reason</th>
                <th className="py-2.5 px-3 w-[10%] text-center">Confidence</th>
                <th className="py-2.5 px-3 w-[8%] text-center">Overlay</th>
                <th className="py-2.5 px-3 w-[10%]">Status</th>
                <th className="py-2.5 px-3 w-[100px] text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-600">
                    <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#0B3C9D]" />
                    <span>Loading preliminary anomaly flags...</span>
                  </td>
                </tr>
              ) : flags.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-600">
                    <CheckCircle2 size={28} className="mx-auto mb-2 text-emerald-600" />
                    <p className="font-semibold text-slate-700">No anomaly flags matching criteria.</p>
                    <p className="text-[11px] text-slate-600 mt-0.5">
                      All uploaded application documents conform to statutory verification guidelines.
                    </p>
                  </td>
                </tr>
              ) : (
                flags.map((flag) => (
                  <tr key={flag.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                          flag.severity === 'HIGH'
                            ? 'bg-red-100 text-red-800 border border-red-200'
                            : flag.severity === 'MEDIUM'
                            ? 'bg-amber-100 text-amber-800 border border-amber-200'
                            : 'bg-blue-100 text-blue-800 border border-blue-200'
                        }`}>
                          {flag.severity}
                        </span>
                        <span className="font-mono text-slate-600 text-[10px]">#{flag.id}</span>
                      </div>
                      <div className="font-bold text-[#0F2A5C]">{flag.detector}</div>
                      <span className="text-[10px] text-slate-600 font-mono">{flag.code}</span>
                    </td>

                    <td className="py-3 px-3">
                      <div className="font-semibold text-[#0F2A5C] truncate max-w-[180px]" title={flag.institute_name}>
                        {flag.institute_name || `Institute #${flag.institute_id}`}
                      </div>
                      <div className="flex items-center gap-1 text-[11px] text-slate-600 mt-0.5">
                        <FileText size={12} className="text-slate-500 shrink-0" />
                        <span className="truncate max-w-[170px]" title={flag.document_filename}>
                          {flag.document_filename || `Doc #${flag.document_id}`}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 px-3 max-w-[260px]">
                      <p className="text-slate-700 line-clamp-2 leading-relaxed" title={flag.reason}>
                        {flag.reason}
                      </p>
                      <span className="text-[10px] text-slate-600 mt-0.5 block italic">
                        Action: {flag.recommended_action}
                      </span>
                    </td>

                    <td className="py-3 px-3 text-center">
                      <div className="inline-flex flex-col items-center">
                        <span className="font-bold text-slate-800 text-[12px]">
                          {Math.round(flag.confidence * 100)}%
                        </span>
                        <div className="w-12 h-1.5 bg-slate-100 rounded-full overflow-hidden mt-1">
                          <div
                            className={`h-full ${flag.confidence > 0.8 ? 'bg-red-500' : 'bg-amber-500'}`}
                            style={{ width: `${Math.round(flag.confidence * 100)}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-3">
                      {flag.has_overlay ? (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 text-[10px] font-bold">
                          <Image size={11} />
                          <span>Heatmap</span>
                        </span>
                      ) : (
                        <span className="text-slate-600 text-[10px]">None</span>
                      )}
                    </td>

                    <td className="py-3 px-3 whitespace-nowrap">
                      <StatusPill status={flag.review_status} />
                      {flag.reviewed_by_name && (
                        <div className="text-[10px] text-slate-600 mt-1 truncate max-w-[110px]" title={flag.reviewed_by_name}>
                          By: {flag.reviewed_by_name}
                        </div>
                      )}
                    </td>

                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => handleOpenDetail(flag)}
                          className="px-2.5 py-1.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded text-[11px] font-semibold inline-flex items-center gap-1 transition-colors"
                        >
                          <Eye size={12} />
                          <span>Inspect</span>
                        </button>
                        <button
                          onClick={() => openDecisionModal('Verified – no concern', flag)}
                          className="p-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 rounded transition-colors"
                          title="Verified – no concern"
                        >
                          <CheckCircle2 size={15} />
                        </button>
                        <button
                          onClick={() => openDecisionModal('Needs institute clarification', flag)}
                          className="p-1.5 bg-amber-50 hover:bg-amber-100 text-amber-700 rounded transition-colors"
                          title="Needs institute clarification"
                        >
                          <HelpCircle size={15} />
                        </button>
                        <button
                          onClick={() => openDecisionModal('Escalate', flag)}
                          className="p-1.5 bg-red-50 hover:bg-red-100 text-red-700 rounded transition-colors"
                          title="Escalate"
                        >
                          <TrendingUp size={15} />
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

      {/* Flag Inspection Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={`Anomaly Flag #${selectedFlag?.id || ''}`}
        subtitle={`${selectedFlag?.detector} (${selectedFlag?.code})`}
      >
        {selectedFlag && (
          <div className="space-y-6 text-xs">
            {/* Core Status Card */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Review Status:</span>
                <StatusPill status={selectedFlag.review_status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Algorithmic Confidence:</span>
                <span className="font-bold text-slate-800">{Math.round(selectedFlag.confidence * 100)}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Institute:</span>
                <span className="font-bold text-[#0F2A5C]">{selectedFlag.institute_name || `ID #${selectedFlag.institute_id}`}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Target Document:</span>
                <span className="font-mono text-slate-700">{selectedFlag.document_filename}</span>
              </div>
            </div>

            {/* Potential Anomaly Narrative */}
            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-2">
                Potential Anomaly Assessment
              </h4>
              <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-lg text-slate-800 space-y-1.5">
                <p className="font-semibold text-amber-900 leading-relaxed">
                  {selectedFlag.reason}
                </p>
                <div className="pt-2 border-t border-amber-200/60 text-[11px] text-amber-800">
                  <strong>Recommended Scrutiny Action:</strong> {selectedFlag.recommended_action}
                </div>
              </div>
            </div>

            {/* Overlay Heatmap / Visual Evidence */}
            {selectedFlag.has_overlay && (
              <div>
                <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                  <Image size={14} className="text-[#0B3C9D]" />
                  <span>Visual Evidence Heatmap</span>
                </h4>
                <div className="p-2 bg-slate-900 rounded-xl border border-slate-800 text-center overflow-hidden">
                  <img
                    src={`/api/v1/admin/anomalies/${selectedFlag.id}/overlay`}
                    alt="Anomaly Overlay Heatmap"
                    className="max-h-72 mx-auto rounded object-contain border border-slate-700"
                  />
                  <p className="text-[10px] text-slate-600 mt-2">
                    Visual bounding boxes and gradient heatmaps highlighting areas needing verification.
                  </p>
                </div>
              </div>
            )}

            {/* Structured Evidence Payload */}
            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Layers size={14} className="text-[#0B3C9D]" />
                <span>Extracted Evidence Points</span>
              </h4>
              {selectedFlag.evidence_json && selectedFlag.evidence_json.length > 0 ? (
                <div className="space-y-2">
                  {selectedFlag.evidence_json.map((ev, idx) => (
                    <div key={idx} className="p-3 bg-white border border-slate-200 rounded-lg font-mono text-[11px] space-y-1">
                      {Object.entries(ev).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-slate-500 font-sans">{k}:</span>
                          <span className="text-slate-800 font-semibold">{String(v)}</span>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-slate-600 italic text-[11px]">No granular evidence coordinates recorded.</p>
              )}
            </div>

            {/* Prior Review Determination if exists */}
            {selectedFlag.review_note && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-xl">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-[#0B3C9D]">Prior Officer Determination:</span>
                  <span className="text-[10px] text-slate-600">
                    {selectedFlag.reviewed_at ? new Date(selectedFlag.reviewed_at).toLocaleString('en-GB') : ''}
                  </span>
                </div>
                <p className="text-slate-700 italic text-[11px]">"{selectedFlag.review_note}"</p>
                <span className="text-[10px] text-slate-500 block mt-1">
                  Reviewer: {selectedFlag.reviewed_by_name || 'AICTE Officer'}
                </span>
              </div>
            )}

            {/* Human Feedback Loop for AI Governance */}
            <div className="pt-4 border-t border-slate-200">
              <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Detector Accuracy Feedback
              </span>
              <p className="text-[11px] text-slate-500 mb-2.5">
                Was this potential anomaly flag valid, or was it a benign false alarm?
              </p>
              {feedbackMessage ? (
                <div className="p-2.5 bg-emerald-50 text-emerald-800 rounded-lg text-xs font-semibold flex items-center gap-1.5">
                  <CheckCircle2 size={14} className="text-emerald-600" />
                  <span>{feedbackMessage}</span>
                </div>
              ) : (
                <div className="space-y-2">
                  <input
                    type="text"
                    placeholder="Optional feedback note (e.g. scanned watermark caused visual noise)..."
                    value={feedbackNote}
                    onChange={(e) => setFeedbackNote(e.target.value)}
                    className="w-full text-xs p-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-1 focus:ring-[#0B3C9D]"
                  />
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={isSubmittingFeedback}
                      onClick={() => handleFeedback(true)}
                      className="flex-1 py-1.5 px-3 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 border border-emerald-200 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      <ThumbsUp size={13} />
                      <span>Valid Flag</span>
                    </button>
                    <button
                      type="button"
                      disabled={isSubmittingFeedback}
                      onClick={() => handleFeedback(false)}
                      className="flex-1 py-1.5 px-3 bg-red-50 hover:bg-red-100 text-red-800 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 border border-red-200 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      <ThumbsDown size={13} />
                      <span>False Alarm</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Scrutiny Action Buttons in Drawer */}
            <div className="pt-4 border-t border-slate-200 space-y-2">
              <span className="text-slate-500 font-semibold block">Record Scrutiny Action:</span>
              <div className="grid grid-cols-3 gap-2">
                <button
                  onClick={() => openDecisionModal('Verified – no concern')}
                  className="py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 transition-colors"
                >
                  <CheckCircle2 size={13} />
                  <span>No Concern</span>
                </button>
                <button
                  onClick={() => openDecisionModal('Needs institute clarification')}
                  className="py-2.5 bg-[#F58220] hover:bg-[#E06F0F] text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 transition-colors"
                >
                  <HelpCircle size={13} />
                  <span>Clarify</span>
                </button>
                <button
                  onClick={() => openDecisionModal('Escalate')}
                  className="py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1 transition-colors"
                >
                  <TrendingUp size={13} />
                  <span>Escalate</span>
                </button>
              </div>
            </div>
          </div>
        )}
      </Drawer>

      {/* Decision Modal */}
      {selectedFlag && (
        <Modal
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          title={`Record Review Decision: "${chosenDecision}"`}
          subtitle={`Target Flag #${selectedFlag.id} (${selectedFlag.detector})`}
          maxWidth="max-w-[640px]"
          footer={
            <>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="h-11 px-5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmitting || !decisionNote.trim()}
                onClick={(e) => handleDecisionSubmit(e as any)}
                className="h-11 px-6 bg-[#0B3C9D] hover:bg-[#092E7A] text-white font-bold rounded-xl shadow-sm transition-colors flex items-center gap-2 text-sm disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isSubmitting && <Loader2 size={16} className="animate-spin" />}
                <span>Save Determination</span>
              </button>
            </>
          }
        >
          <div className="space-y-6">
            <p className="text-xs text-slate-500 leading-relaxed">
              Your determination is mandatory and will be permanently recorded in the append-only audit trail.
            </p>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Mandatory Review Note <span className="text-red-500">*</span>
              </label>
              <textarea
                required
                rows={4}
                placeholder="State the regulatory grounds, clarification specifics, or verification basis..."
                value={decisionNote}
                onChange={(e) => setDecisionNote(e.target.value)}
                className="w-full p-3.5 rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D] text-slate-800 text-sm resize-none"
              />
              <span className="text-xs text-slate-500 mt-2 block font-medium">
                Wording standard: AICTE protocol requires using &apos;needs verification&apos; or &apos;potential anomaly&apos;.
              </span>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

