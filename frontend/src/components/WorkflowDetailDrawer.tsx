import React, { useState, useEffect } from 'react';
import {
  X,
  CheckCircle2,
  RotateCcw,
  UserCheck,
  PauseCircle,
  PlayCircle,
  Gavel,
  AlertTriangle,
  Send,
  Loader2,
  Shield,
  Mail,
  Download,
} from 'lucide-react';
import {
  ApplicationWorkflow,
  WorkflowOfficer,
  workflowApi,
} from '../api/workflow';
import { alertsApi, AuditTimelineEvent } from '../api/alerts';
import { useAuth } from '../context/AuthContext';
import { StatusPill } from './StatusPill';

interface WorkflowDetailDrawerProps {
  workflow: ApplicationWorkflow | null;
  isOpen: boolean;
  onClose: () => void;
  onUpdated: (updated: ApplicationWorkflow) => void;
  officers: WorkflowOfficer[];
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return String(dateStr);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}-${month}-${year}`;
}

function formatRole(role?: string): string {
  if (!role) return '';
  switch (role) {
    case 'ADMIN': return 'Admin';
    case 'REGIONAL_OFFICER': return 'Regional officer';
    case 'BUREAU_OFFICER': return 'Bureau officer';
    case 'COMMITTEE_MEMBER': return 'Committee member';
    case 'REVIEWER': return 'Reviewer';
    case 'INSTITUTE': return 'Institute';
    default: return role.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export const WorkflowDetailDrawer: React.FC<WorkflowDetailDrawerProps> = ({
  workflow,
  isOpen,
  onClose,
  onUpdated,
  officers,
}) => {
  const { user } = useAuth();

  // Action modal states
  const [activeAction, setActiveAction] = useState<
    'ADVANCE' | 'RETURN' | 'REASSIGN' | 'HOLD' | 'RESUME' | 'DECISION' | 'COMMUNICATION' | null
  >(null);
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [selectedOfficerId, setSelectedOfficerId] = useState<number>(0);
  const [decision, setDecision] = useState<'APPROVED' | 'REJECTED'>('APPROVED');
  const [selectedTemplateCode, setSelectedTemplateCode] = useState('DEFICIENCY_NOTICE');
  const [commResult, setCommResult] = useState<any>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [isRefreshingAi, setIsRefreshingAi] = useState(false);
  const [timelineEvents, setTimelineEvents] = useState<AuditTimelineEvent[]>([]);
  const [isLoadingTimeline, setIsLoadingTimeline] = useState(false);

  const buildFallbackSummary = (wf: ApplicationWorkflow): string => {
    const stage = wf.current_stage_name || 'Scrutiny';
    const officer = wf.assigned_officer_name || 'Unassigned';
    const slaText = wf.is_overdue
      ? `SLA is overdue by ${Math.abs(wf.days_remaining)} days`
      : `SLA due in ${wf.days_remaining} days`;
    const recentAction = wf.history && wf.history.length > 0
      ? ` Recent action: ${wf.history[0].action}${wf.history[0].reason ? ` - ${wf.history[0].reason}` : ''}.`
      : '';
    return `${wf.institute_name} application ${wf.application_code} (${wf.category}) is at ${stage} stage. Status: ${wf.status}. Assigned to ${officer}. ${slaText}.${recentAction}`;
  };

  useEffect(() => {
    if (workflow?.id && isOpen) {
      setIsLoadingTimeline(true);
      alertsApi
        .getAuditTimeline(workflow.id)
        .then((res) => setTimelineEvents(res.timeline || []))
        .catch((err) => console.error('Failed to load audit timeline:', err))
        .finally(() => setIsLoadingTimeline(false));

      if (!workflow.case_summary) {
        setIsRefreshingAi(true);
        const timeoutPromise = new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('TIMEOUT')), 10000)
        );
        Promise.race([workflowApi.refreshSummary(workflow.id), timeoutPromise])
          .then((res) => {
            if (res && res.case_summary) {
              onUpdated({ ...workflow, case_summary: res.case_summary });
            } else {
              onUpdated({ ...workflow, case_summary: buildFallbackSummary(workflow) });
            }
          })
          .catch(() => {
            onUpdated({ ...workflow, case_summary: buildFallbackSummary(workflow) });
          })
          .finally(() => {
            setIsRefreshingAi(false);
          });
      }
    }
  }, [workflow?.id, isOpen]);

  if (!isOpen || !workflow) return null;

  const isCompetentAuthority =
    user?.role === 'ADMIN' || user?.role === 'BUREAU_OFFICER';
  const isFinalStage =
    workflow.stages.length > 0 &&
    workflow.current_stage_sequence >= workflow.stages.length;

  const handleOpenAction = (
    action: 'ADVANCE' | 'RETURN' | 'REASSIGN' | 'HOLD' | 'RESUME' | 'DECISION' | 'COMMUNICATION'
  ) => {
    setActiveAction(action);
    setReason('');
    setNotes('');
    setCommResult(null);
    setActionError(null);
    if (action === 'REASSIGN' && officers.length > 0) {
      setSelectedOfficerId(officers[0].id);
    }
  };

  const handleDownloadPdf = () => {
    if (!commResult?.pdf_base64) return;
    const link = document.createElement('a');
    link.href = `data:application/pdf;base64,${commResult.pdf_base64}`;
    link.download = `AICTE_${selectedTemplateCode}_${workflow.application_code}.pdf`;
    link.click();
  };

  const handleExecuteAction = async () => {
    if (!reason.trim()) {
      setActionError('Reason is required.');
      return;
    }
    setIsSubmitting(true);
    setActionError(null);

    try {
      if (activeAction === 'COMMUNICATION') {
        const res = await workflowApi.generateCommunication({
          template_code: selectedTemplateCode,
          workflow_id: workflow.id,
          reason,
        });
        setCommResult(res);
        alertsApi.getAuditTimeline(workflow.id).then((t) => setTimelineEvents(t.timeline || []));
        return;
      }

      let updated: ApplicationWorkflow;
      if (activeAction === 'ADVANCE') {
        updated = await workflowApi.advanceStage(workflow.id, { reason, notes });
      } else if (activeAction === 'RETURN') {
        updated = await workflowApi.returnWorkflow(workflow.id, { reason, notes });
      } else if (activeAction === 'REASSIGN') {
        updated = await workflowApi.reassignOfficer(workflow.id, {
          new_officer_id: Number(selectedOfficerId),
          reason,
        });
      } else if (activeAction === 'HOLD') {
        updated = await workflowApi.holdWorkflow(workflow.id, { reason });
      } else if (activeAction === 'RESUME') {
        updated = await workflowApi.resumeWorkflow(workflow.id, { reason });
      } else if (activeAction === 'DECISION') {
        updated = await workflowApi.recordDecision(workflow.id, {
          decision,
          reason,
          notes,
        });
      } else {
        return;
      }

      onUpdated(updated);
      setActiveAction(null);
    } catch (err: any) {
      setActionError(
        err.response?.data?.detail || 'Failed to execute workflow action. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRefreshSummary = async () => {
    setIsRefreshingAi(true);
    const timeoutPromise = new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('TIMEOUT')), 10000)
    );
    try {
      const res = await Promise.race([workflowApi.refreshSummary(workflow.id), timeoutPromise]);
      if (res && res.case_summary) {
        onUpdated({ ...workflow, case_summary: res.case_summary });
      } else {
        onUpdated({ ...workflow, case_summary: buildFallbackSummary(workflow) });
      }
    } catch {
      onUpdated({ ...workflow, case_summary: buildFallbackSummary(workflow) });
    } finally {
      setIsRefreshingAi(false);
    }
  };

  return (
    <div className="fixed inset-x-0 bottom-0 top-24 z-50 overflow-hidden bg-black/35 backdrop-blur-none flex justify-end animate-fade-in">
      <div className="fixed inset-x-0 bottom-0 top-24" onClick={onClose} aria-hidden="true" />
      <div className="relative z-10 w-full max-w-3xl bg-white h-full shadow-2xl flex flex-col overflow-hidden border-l border-slate-200">
        {/* Fixed Header */}
        <div className="bg-[#0B3C9D] text-white p-5 flex items-start justify-between shrink-0 z-20 border-b border-blue-900">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#FCE0BE]">
                Case File
              </span>
              <span className="text-white/60">•</span>
              <span className="text-xs text-white/90 font-mono">
                {workflow.application_code}
              </span>
            </div>
            <h2 className="text-xl font-bold tracking-tight">
              {workflow.institute_name}
            </h2>
            <p className="text-xs text-white/80 mt-1">
              {workflow.category} • {workflow.region} Region • Template:{' '}
              {workflow.template_name}
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close drawer"
            className="p-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors cursor-pointer"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="p-5 sm:p-6 space-y-6 flex-1 overflow-y-auto">
          {/* Status & SLA Overview Banner */}
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <StatusPill status={workflow.status} />
              <div>
                <p className="text-xs text-slate-500 font-medium">Current Stage</p>
                <p className="text-sm font-bold text-slate-800">
                  {workflow.current_stage_name}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs text-slate-600">
              <div>
                <span className="block text-slate-600 font-medium">Assigned Officer</span>
                <span className="font-semibold text-slate-800">
                  {workflow.assigned_officer_name || 'Unassigned'}
                </span>
              </div>
              <div className="border-l pl-4 border-slate-200">
                <span className="block text-slate-600 font-medium">SLA Due Date</span>
                <span
                  className={`font-semibold ${
                    workflow.is_overdue
                      ? 'text-red-600'
                      : workflow.days_remaining <= 2
                      ? 'text-amber-600'
                      : 'text-emerald-700'
                  }`}
                >
                  {formatDate(workflow.due_date)} (
                  {workflow.is_overdue
                    ? 'Overdue'
                    : `${workflow.days_remaining}d remaining`}
                  )
                </span>
              </div>
            </div>
          </div>

          {/* Case Summary Card */}
          <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-sm relative">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-semibold text-slate-700">
                Case summary
              </h4>
              <button
                onClick={handleRefreshSummary}
                disabled={isRefreshingAi}
                className="text-[11px] font-medium text-[#0B3C9D] hover:underline flex items-center gap-1 cursor-pointer"
              >
                {isRefreshingAi && <Loader2 size={12} className="animate-spin" />}
                Refresh
              </button>
            </div>
            {isRefreshingAi ? (
              <div className="flex items-center gap-2 text-xs text-slate-600 font-medium py-1">
                <Loader2 size={14} className="animate-spin text-[#0B3C9D]" />
                <span>Refreshing summary...</span>
              </div>
            ) : (
              <p className="text-sm text-slate-700 leading-relaxed font-normal">
                {workflow.case_summary || buildFallbackSummary(workflow)}
              </p>
            )}
          </div>

          {/* Ordered Stages Progression Stepper */}
          <div>
            <h4 className="text-xs font-semibold text-slate-700 mb-3">
              Stages
            </h4>
            <div className="space-y-3">
              {workflow.stages.map((stg) => {
                const isPassed = stg.sequence < workflow.current_stage_sequence;
                const isCurrent = stg.sequence === workflow.current_stage_sequence;
                const isFuture = stg.sequence > workflow.current_stage_sequence;

                return (
                  <div
                    key={stg.id}
                    className={`p-3.5 rounded-lg border transition-all flex items-center justify-between ${
                      isCurrent
                        ? 'border-[#0B3C9D] bg-blue-50/60 shadow-xs'
                        : isPassed
                        ? 'border-emerald-200 bg-emerald-50/40 text-slate-700'
                        : 'border-slate-200 bg-slate-50/50 text-slate-600'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-7 h-7 rounded-full flex items-center justify-center font-bold text-xs ${
                          isCurrent
                            ? 'bg-[#0B3C9D] text-white'
                            : isPassed
                            ? 'bg-emerald-600 text-white'
                            : 'bg-slate-200 text-slate-600'
                        }`}
                      >
                        {isPassed ? <CheckCircle2 size={16} /> : stg.sequence}
                      </div>
                      <div>
                        <p
                          className={`text-sm font-semibold ${
                            isCurrent
                              ? 'text-[#0B3C9D]'
                              : isPassed
                              ? 'text-slate-800'
                              : 'text-slate-700'
                          }`}
                        >
                          {stg.stage_name}
                        </p>
                        <p className="text-xs text-slate-600">
                          Role: <span className="font-medium">{formatRole(stg.responsible_role)}</span> • SLA:{' '}
                          <span className="font-medium">{stg.sla_days} days</span>
                        </p>
                      </div>
                    </div>

                    <div>
                      {isCurrent && (
                        <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-[#0B3C9D] text-white">
                          In progress
                        </span>
                      )}
                      {isPassed && (
                        <span className="text-xs font-medium text-emerald-700">
                          Completed
                        </span>
                      )}
                      {isFuture && (
                        <span className="text-xs text-slate-600 font-medium">Upcoming</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Action Control Panel */}
          {workflow.status !== 'COMPLETED' && (
            <div className="p-4 rounded-lg border border-slate-200 bg-slate-50 space-y-3">
              <h4 className="text-xs font-semibold text-slate-700">
                Actions
              </h4>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {!isFinalStage && (
                  <button
                    onClick={() => handleOpenAction('ADVANCE')}
                    className="px-3 py-2 bg-[#0B3C9D] hover:bg-[#082B70] text-white rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <CheckCircle2 size={14} />
                    Complete stage
                  </button>
                )}

                <button
                  onClick={() => handleOpenAction('RETURN')}
                  className="px-3 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
                >
                  <RotateCcw size={14} />
                  Return
                </button>

                <button
                  onClick={() => handleOpenAction('REASSIGN')}
                  className="px-3 py-2 bg-slate-700 hover:bg-slate-800 text-white rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
                >
                  <UserCheck size={14} />
                  Reassign
                </button>

                {workflow.status === 'ON_HOLD' ? (
                  <button
                    onClick={() => handleOpenAction('RESUME')}
                    className="px-3 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                  >
                    <PlayCircle size={14} />
                    Resume Case
                  </button>
                ) : (
                  <button
                    onClick={() => handleOpenAction('HOLD')}
                    className="px-3 py-2.5 bg-slate-600 hover:bg-slate-700 text-white rounded-lg text-xs font-semibold flex items-center justify-center gap-1.5 shadow-xs transition-colors"
                  >
                    <PauseCircle size={14} />
                    Put On Hold
                  </button>
                )}

                {/* Final Decision Button: Enabled for Competent Authority on Final Stage */}
                {isCompetentAuthority && isFinalStage && (
                  <div className="col-span-2 space-y-1">
                    <button
                      onClick={() => handleOpenAction('DECISION')}
                      className="w-full px-3 py-2 bg-[#E8650A] hover:bg-[#D45906] text-white rounded-md text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
                    >
                      <Gavel size={15} />
                      Record decision
                    </button>
                    <p className="text-[11px] text-slate-500 text-center">
                      Decisions remain with the competent authority.
                    </p>
                  </div>
                )}

                {/* Dispatch Notice Button */}
                <button
                  onClick={() => handleOpenAction('COMMUNICATION')}
                  className="px-3 py-2 bg-indigo-700 hover:bg-indigo-800 text-white rounded-md text-xs font-medium flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Mail size={14} />
                  Dispatch notice
                </button>
              </div>

              {!isCompetentAuthority && isFinalStage && (
                <p className="text-[11px] text-slate-500 italic">
                  Note: Final decision is restricted to the competent authority (Bureau officer / Admin).
                </p>
              )}
            </div>
          )}

          {/* Action Execution Sub-Form */}
          {activeAction && (
            <div className="p-5 rounded-lg border border-slate-200 bg-white shadow-sm space-y-4">
              <div className="flex items-center justify-between border-b pb-3">
                <h5 className="font-semibold text-sm text-slate-900 flex items-center gap-2">
                  <Shield size={16} />
                  Action: {activeAction.replace('_', ' ').toLowerCase()}
                </h5>
                <button
                  onClick={() => setActiveAction(null)}
                  className="text-slate-600 hover:text-slate-900"
                >
                  <X size={16} />
                </button>
              </div>

              {actionError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-md flex items-center gap-2">
                  <AlertTriangle size={15} className="shrink-0" />
                  <span>{actionError}</span>
                </div>
              )}

              {activeAction === 'DECISION' && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Decision
                  </label>
                  <div className="flex gap-4">
                    <label className="flex items-center gap-2 text-xs font-medium text-emerald-800 cursor-pointer">
                      <input
                        type="radio"
                        name="decision"
                        value="APPROVED"
                        checked={decision === 'APPROVED'}
                        onChange={() => setDecision('APPROVED')}
                      />
                      Grant approval
                    </label>
                    <label className="flex items-center gap-2 text-xs font-medium text-red-800 cursor-pointer">
                      <input
                        type="radio"
                        name="decision"
                        value="REJECTED"
                        checked={decision === 'REJECTED'}
                        onChange={() => setDecision('REJECTED')}
                      />
                      Reject application
                    </label>
                  </div>
                </div>
              )}

              {activeAction === 'REASSIGN' && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Select officer
                  </label>
                  <select
                    value={selectedOfficerId}
                    onChange={(e) => setSelectedOfficerId(Number(e.target.value))}
                    className="w-full text-xs p-2.5 rounded-md border border-slate-300 bg-white"
                  >
                    {officers.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.email} ({formatRole(o.role)} • {o.region || 'National'})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {activeAction === 'COMMUNICATION' && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Select notice template
                  </label>
                  <select
                    value={selectedTemplateCode}
                    onChange={(e) => setSelectedTemplateCode(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-md border border-slate-300 bg-white font-medium text-slate-800"
                  >
                    <option value="DEFICIENCY_NOTICE">Deficiency notice (Scrutiny defect)</option>
                    <option value="CLARIFICATION_REQUEST">Clarification request (Query)</option>
                    <option value="EVC_SCHEDULING_INTIMATION">EVC scheduling intimation (Physical inspection)</option>
                    <option value="UNDERTAKING_REMINDER">Undertaking reminder (Conditional approval)</option>
                    <option value="DOCUMENT_RENEWAL_REQUEST">Document renewal request (Validity expiry)</option>
                    <option value="ESCALATION_NOTICE">Escalation notice (SLA breach)</option>
                  </select>
                </div>
              )}

              {commResult && (
                <div className="p-4 bg-emerald-50 border border-emerald-300 rounded-lg space-y-2 text-emerald-950">
                  <div className="flex items-center gap-2 font-semibold text-emerald-900 text-xs">
                    <CheckCircle2 size={16} className="text-emerald-700" />
                    <span>Notice dispatched and recorded</span>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed font-mono">
                    Subject: {commResult.subject}
                  </p>
                  <div className="text-[11px] text-slate-600 flex items-center gap-3">
                    <span>Email outbox: <strong>{commResult.email_status}</strong></span>
                    <span>In-app: <strong>Delivered</strong></span>
                  </div>
                  <p className="text-[10px] text-slate-500 italic">
                    {commResult.disclaimer}
                  </p>
                  <button
                    type="button"
                    onClick={handleDownloadPdf}
                    className="mt-2 px-3 py-1.5 bg-[#0B3C9D] hover:bg-[#082b70] text-white rounded text-xs font-medium inline-flex items-center gap-1.5"
                  >
                    <Download size={13} />
                    <span>Download letter (PDF)</span>
                  </button>
                </div>
              )}

              {!commResult && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Reason <span className="text-red-500">*</span>
                    </label>
                    <textarea
                      rows={3}
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder={
                        activeAction === 'COMMUNICATION'
                          ? 'Specify details of deficiency, required documentation, or directives...'
                          : 'State the justification for this action...'
                      }
                      className="w-full text-xs p-3 rounded-md border border-slate-300 focus:border-[#0B3C9D] focus:ring-1 focus:ring-[#0B3C9D] outline-none"
                    />
                  </div>

                  {activeAction !== 'COMMUNICATION' && (
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Additional notes (Optional)
                      </label>
                      <input
                        type="text"
                        value={notes}
                        onChange={(e) => setNotes(e.target.value)}
                        placeholder="Optional internal remarks..."
                        className="w-full text-xs p-2.5 rounded-md border border-slate-300 focus:border-[#0B3C9D] outline-none"
                      />
                    </div>
                  )}
                </>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setActiveAction(null)}
                  className="px-3.5 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-md"
                >
                  {commResult ? 'Close' : 'Cancel'}
                </button>
                {!commResult && (
                  <button
                    type="button"
                    onClick={handleExecuteAction}
                    disabled={isSubmitting || !reason.trim()}
                    className="px-4 py-1.5 bg-[#0B3C9D] hover:bg-[#082B70] text-white text-xs font-medium rounded-md flex items-center gap-1.5 disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <Send size={14} />
                    )}
                    {activeAction === 'COMMUNICATION' ? 'Dispatch notice' : 'Confirm'}
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Unified Audit Timeline Log */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-xs font-semibold text-slate-800">
                History ({timelineEvents.length || workflow.history.length})
              </h4>
              {isLoadingTimeline && (
                <span className="text-[10px] text-slate-600 flex items-center gap-1 font-mono">
                  <Loader2 size={11} className="animate-spin" />
                  Syncing logs...
                </span>
              )}
            </div>

            {timelineEvents.length === 0 && workflow.history.length === 0 ? (
              <p className="text-xs text-slate-600 italic">
                No actions or events recorded yet.
              </p>
            ) : (
              <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1">
                {(timelineEvents.length > 0 ? timelineEvents : workflow.history.map(h => ({
                  source: 'WORKFLOW' as const,
                  action: h.action,
                  title: `${h.from_stage} -> ${h.to_stage}`,
                  actor: `${h.performed_by_name} (${h.performed_by_role})`,
                  reason: h.reason,
                  details: h.details,
                  timestamp: h.created_at
                }))).map((item, idx) => {
                  let badgeBg = 'bg-blue-100 text-[#0B3C9D] border-blue-200';
                  if (item.source === 'EVC') badgeBg = 'bg-purple-100 text-purple-800 border-purple-200';
                  else if (item.source === 'UNDERTAKING') badgeBg = 'bg-amber-100 text-amber-800 border-amber-200';
                  else if (item.source === 'ALERT') badgeBg = 'bg-orange-100 text-orange-800 border-orange-200';
                  else if (item.source === 'ESCALATION') badgeBg = 'bg-red-100 text-red-800 border-red-200';
                  else if (item.source === 'AUDIT') badgeBg = 'bg-emerald-100 text-emerald-800 border-emerald-200';

                  return (
                    <div
                      key={idx}
                      className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1 hover:bg-white transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2 flex-wrap">
                        <div className="flex items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded text-[9px] font-black border ${badgeBg}`}>
                            {item.source}
                          </span>
                          <span className="font-mono font-bold text-slate-800 text-[11px]">
                            {item.action}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-600 font-mono">
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                      </div>

                      <p className="text-slate-800 font-semibold text-xs">{item.title}</p>

                      {item.reason && (
                        <p className="text-slate-700 text-[11px] leading-relaxed">
                          <span className="font-semibold text-slate-800">Justification:</span>{' '}
                          {item.reason}
                        </p>
                      )}

                      {item.details && typeof item.details === 'string' && (
                        <p className="text-slate-600 text-[10px] font-mono mt-0.5">
                          {item.details}
                        </p>
                      )}

                      <p className="text-[10px] text-slate-600 pt-0.5">
                        Recorded by: <span className="font-medium text-slate-800">{item.actor}</span>
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Fixed Footer */}
        <div className="p-4 bg-slate-50 border-t border-slate-200 shrink-0 z-20 flex items-center justify-between">
          <span className="text-xs text-slate-600">
            Case: <span className="font-mono font-semibold text-slate-800">{workflow.application_code}</span>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-200 hover:bg-slate-300 text-slate-800 font-semibold text-xs rounded-lg transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
