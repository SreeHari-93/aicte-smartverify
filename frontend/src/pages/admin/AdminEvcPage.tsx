import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  Clock,
  CheckCircle2,
  Building2,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react';
import { evcApi, EvcRecordItem, CommitteeMember } from '../../api/stage3';
import { StatusPill } from '../../components/StatusPill';
import { Modal } from '../../components/Modal';
import { ActionMenu } from '../../components/ActionMenu';
import { DataTable, ColumnDef } from '../../components/DataTable';

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return String(dateStr);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}-${month}-${year}`;
}

export const AdminEvcPage: React.FC = () => {
  const [queue, setQueue] = useState<EvcRecordItem[]>([]);
  const [_upcoming, setUpcoming] = useState<EvcRecordItem[]>([]);
  const [committeePool, setCommitteePool] = useState<CommitteeMember[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

  // Schedule Modal State
  const [schedulingEvc, setSchedulingEvc] = useState<EvcRecordItem | null>(null);
  const [isScheduleModalOpen, setIsScheduleModalOpen] = useState(false);
  const [proposedDate, setProposedDate] = useState('');
  const [confirmedDate, setConfirmedDate] = useState('');
  const [selectedMembers, setSelectedMembers] = useState<CommitteeMember[]>([]);
  const [scheduleRemarks, setScheduleRemarks] = useState('');
  const [conflictWarning, setConflictWarning] = useState<string | null>(null);
  const [isSavingSchedule, setIsSavingSchedule] = useState(false);

  // Complete Visit Modal State
  const [completingEvc, setCompletingEvc] = useState<EvcRecordItem | null>(null);
  const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false);
  const [completionRemarks, setCompletionRemarks] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  const [highlightedId, setHighlightedId] = useState<number | null>(null);
  const [unavailableNotice, setUnavailableNotice] = useState<string | null>(null);
  const handledParamRef = useRef<string | null>(null);
  const [reportFile, setReportFile] = useState<File | null>(null);
  const [isSubmittingReport, setIsSubmittingReport] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [queueData, upcomingData, poolData] = await Promise.all([
        evcApi.getQueue({ status: statusFilter !== 'ALL' ? statusFilter : undefined }),
        evcApi.getUpcoming(),
        evcApi.getCommitteeMembers(),
      ]);
      setQueue(queueData);
      setUpcoming(upcomingData);
      setCommitteePool(poolData);
    } catch (err) {
      console.error('Failed to load EVC data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  // Handle open query param once on load
  useEffect(() => {
    const targetCode = searchParams.get('open') || searchParams.get('application');
    if (!targetCode || isLoading) return;
    if (handledParamRef.current === targetCode) return;
    handledParamRef.current = targetCode;

    if (statusFilter !== 'ALL') setStatusFilter('ALL');
    if (search) setSearch('');

    const targetLower = targetCode.toLowerCase();
    const match = queue.find(
      (item) =>
        String(item.id) === targetCode ||
        String(item.application_id) === targetCode ||
        (item.application_code && item.application_code.toLowerCase() === targetLower)
    );

    if (match) {
      setHighlightedId(match.id);
      if (match.status === 'SCHEDULED') {
        handleOpenComplete(match);
      } else {
        handleOpenSchedule(match);
      }
      setTimeout(() => {
        const el = document.getElementById(`evc-row-${match.id}`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 150);
      setTimeout(() => setHighlightedId(null), 3000);
    } else {
      setUnavailableNotice('This case is no longer available.');
      setTimeout(() => setUnavailableNotice(null), 5000);
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('open');
    nextParams.delete('application');
    setSearchParams(nextParams, { replace: true });
  }, [searchParams, queue, isLoading, statusFilter, search]);

  // Open Schedule Modal
  const handleOpenSchedule = (evc: EvcRecordItem) => {
    setSchedulingEvc(evc);
    setProposedDate(evc.proposed_date ? evc.proposed_date.slice(0, 16) : '');
    setConfirmedDate(evc.confirmed_date ? evc.confirmed_date.slice(0, 16) : '');
    setSelectedMembers(evc.committee_members || []);
    setScheduleRemarks(evc.remarks || '');
    setConflictWarning(null);
    setIsScheduleModalOpen(true);
  };

  // Toggle member selection in schedule modal
  const toggleMemberSelection = (member: CommitteeMember) => {
    const exists = selectedMembers.some((m) => m.email === member.email);
    if (exists) {
      setSelectedMembers(selectedMembers.filter((m) => m.email !== member.email));
    } else {
      setSelectedMembers([...selectedMembers, member]);
    }
  };

  const handleSaveSchedule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!schedulingEvc) return;
    if (!confirmedDate) {
      alert('Confirmed visit date is required.');
      return;
    }

    setIsSavingSchedule(true);
    try {
      await evcApi.scheduleVisit(schedulingEvc.id, {
        proposed_date: proposedDate ? new Date(proposedDate).toISOString() : new Date().toISOString(),
        confirmed_date: new Date(confirmedDate).toISOString(),
        committee_members: selectedMembers,
        remarks: scheduleRemarks,
      });

      setIsScheduleModalOpen(false);
      await loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to schedule EVC visit.');
    } finally {
      setIsSavingSchedule(false);
    }
  };

  // Open Complete Modal
  const handleOpenComplete = (evc: EvcRecordItem) => {
    setCompletingEvc(evc);
    setCompletionRemarks('');
    setReportFile(null);
    setIsCompleteModalOpen(true);
  };

  const handleSaveComplete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!completingEvc) return;

    setIsSubmittingReport(true);
    try {
      const fd = new FormData();
      fd.append('remarks', completionRemarks);
      if (reportFile) fd.append('report_file', reportFile);
      await evcApi.completeVisit(completingEvc.id, fd);

      setIsCompleteModalOpen(false);
      await loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to complete EVC visit.');
    } finally {
      setIsSubmittingReport(false);
    }
  };

  // Filtering
  const filteredQueue = queue.filter((item) => {
    const matchesSearch =
      !search ||
      item.institute_name.toLowerCase().includes(search.toLowerCase()) ||
      (item.application_code && item.application_code.toLowerCase().includes(search.toLowerCase()));
    return matchesSearch;
  });

  const columns: ColumnDef<EvcRecordItem>[] = [
    {
      key: 'application',
      header: 'Application',
      width: '15%',
      align: 'left',
      render: (item) => (
        <span className="font-mono font-bold text-[#0B3C9D] text-xs">
          {item.application_code || `#${item.application_id}`}
        </span>
      ),
    },
    {
      key: 'institute',
      header: 'Institution & region',
      width: '27%',
      align: 'left',
      render: (item) => (
        <div>
          <div className="font-semibold text-slate-900 truncate" title={item.institute_name}>
            {item.institute_name}
          </div>
          <div className="text-[11px] text-slate-600 flex items-center gap-1 mt-0.5">
            <Building2 size={11} className="text-slate-500" />
            <span>{item.institute_state || 'AICTE Region'}</span>
          </div>
        </div>
      ),
    },
    {
      key: 'category',
      header: 'Category & type',
      width: '20%',
      align: 'left',
      render: (item) => (
        <div>
          <div className="text-slate-800 line-clamp-1 text-xs">{item.category}</div>
          {item.is_new_institution ? (
            <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-200">
              New institution (Fast-track)
            </span>
          ) : (
            <span className="text-[11px] text-slate-600">Standard</span>
          )}
        </div>
      ),
    },
    {
      key: 'dates',
      header: 'Dates',
      width: '15%',
      align: 'left',
      render: (item) => (
        <div className="space-y-0.5">
          <div className="flex items-center gap-1 text-slate-700 text-xs">
            <Clock size={11} className="text-slate-500 shrink-0" />
            <span>Due: {formatDate(item.scheduling_deadline)}</span>
          </div>
          <div className="text-xs">
            {item.confirmed_date ? (
              <span className="text-emerald-700 font-medium flex items-center gap-1">
                <CheckCircle2 size={11} className="shrink-0" />
                Visit: {formatDate(item.confirmed_date)}
              </span>
            ) : (
              <span className="text-slate-600 italic">Visit: Not scheduled</span>
            )}
          </div>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '11%',
      align: 'left',
      render: (item) => <StatusPill status={item.status} />,
    },
    {
      key: 'actions',
      header: 'Actions',
      width: '12%',
      align: 'right',
      render: (item) => (
        <div className="flex justify-end">
          {item.status === 'PENDING_SCHEDULING' && (
            <ActionMenu
              primaryAction={{
                label: 'Schedule',
                onClick: () => handleOpenSchedule(item),
              }}
            />
          )}
          {item.status === 'SCHEDULED' && (
            <ActionMenu
              primaryAction={{
                label: 'Reschedule',
                onClick: () => handleOpenSchedule(item),
                variant: 'secondary',
              }}
              menuItems={[
                {
                  label: 'Complete visit',
                  onClick: () => handleOpenComplete(item),
                },
              ]}
            />
          )}
          {item.status === 'COMPLETED' && (
            <span className="text-xs text-slate-600 italic pr-2">Completed</span>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {unavailableNotice && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold rounded-lg flex items-center justify-between">
          <span>{unavailableNotice}</span>
          <button onClick={() => setUnavailableNotice(null)} className="text-amber-700 hover:text-amber-900 font-bold ml-2">×</button>
        </div>
      )}
      {/* Header Banner */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            EVC visits
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Expert Visit Committee inspection scheduling and conflict check.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 text-xs font-semibold rounded-lg shadow-xs disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Main Card with Queue Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
        {/* Toolbar */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setStatusFilter('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                statusFilter === 'ALL'
                  ? 'bg-[#0B3C9D] text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              All visits ({queue.length})
            </button>
            <button
              onClick={() => setStatusFilter('PENDING_SCHEDULING')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                statusFilter === 'PENDING_SCHEDULING'
                  ? 'bg-[#0B3C9D] text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              Pending ({queue.filter((x) => x.status === 'PENDING_SCHEDULING').length})
            </button>
            <button
              onClick={() => setStatusFilter('SCHEDULED')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                statusFilter === 'SCHEDULED'
                  ? 'bg-[#0B3C9D] text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              Scheduled ({queue.filter((x) => x.status === 'SCHEDULED').length})
            </button>
            <button
              onClick={() => setStatusFilter('COMPLETED')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                statusFilter === 'COMPLETED'
                  ? 'bg-[#0B3C9D] text-white shadow-xs'
                  : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
              }`}
            >
              Completed ({queue.filter((x) => x.status === 'COMPLETED').length})
            </button>
          </div>

          <div className="relative">
            <Search size={14} className="absolute left-3 top-2.5 text-slate-600" />
            <input
              type="text"
              placeholder="Search application or institute..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs w-64 focus:outline-none focus:border-[#0B3C9D] text-slate-800 placeholder:text-slate-600"
            />
          </div>
        </div>

        {/* DataTable */}
        <DataTable
          columns={columns}
          data={filteredQueue}
          keyExtractor={(item) => item.id}
          isLoading={isLoading}
          emptyMessage="No EVC visits match these filters."
          rowClassName={(item) => (item.id === highlightedId ? 'bg-amber-100/70 transition-colors duration-700' : '')}
          onClearFilters={search || statusFilter !== 'ALL' ? () => { setSearch(''); setStatusFilter('ALL'); } : undefined}
        />
      </div>

      {/* Schedule Visit Modal */}
      <Modal
        isOpen={isScheduleModalOpen}
        onClose={() => setIsScheduleModalOpen(false)}
        title={`Schedule visit - ${schedulingEvc?.application_code || ''}`}
      >
        <form onSubmit={handleSaveSchedule} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Confirmed Visit Date *
            </label>
            <input
              type="datetime-local"
              value={confirmedDate}
              onChange={(e) => setConfirmedDate(e.target.value)}
              required
              className="w-full p-2 border border-slate-300 rounded-lg text-xs bg-white text-slate-800 focus:outline-none focus:border-[#0B3C9D]"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Proposed Alternate Date (Optional)
            </label>
            <input
              type="datetime-local"
              value={proposedDate}
              onChange={(e) => setProposedDate(e.target.value)}
              className="w-full p-2 border border-slate-300 rounded-lg text-xs bg-white text-slate-800 focus:outline-none focus:border-[#0B3C9D]"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Select Committee Members ({selectedMembers.length} selected)
            </label>
            <div className="max-h-48 overflow-y-auto border border-slate-200 rounded-lg p-2 space-y-1.5 bg-slate-50">
              {committeePool.map((m) => {
                const isSelected = selectedMembers.some((sm) => sm.email === m.email);
                return (
                  <div
                    key={m.email}
                    onClick={() => toggleMemberSelection(m)}
                    className={`p-2 rounded-md border text-xs cursor-pointer flex items-center justify-between transition-colors ${
                      isSelected
                        ? 'bg-blue-50 border-[#0B3C9D] text-[#0B3C9D] font-bold'
                        : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    <div>
                      <div className="font-semibold">{m.name}</div>
                      <div className="text-[10px] text-slate-600">{m.institution || m.region || 'Committee Member'} • {m.role || 'Expert'}</div>
                    </div>
                    {isSelected && <CheckCircle2 size={14} className="text-[#0B3C9D]" />}
                  </div>
                );
              })}
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Scheduling Remarks
            </label>
            <textarea
              rows={2}
              value={scheduleRemarks}
              onChange={(e) => setScheduleRemarks(e.target.value)}
              placeholder="Inspection agenda, logistics notes, or special requirements..."
              className="w-full p-2 border border-slate-300 rounded-lg text-xs bg-white text-slate-800 focus:outline-none focus:border-[#0B3C9D]"
            />
          </div>

          {conflictWarning && (
            <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg text-xs flex items-center gap-2">
              <ShieldAlert size={14} />
              <span>{conflictWarning}</span>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsScheduleModalOpen(false)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSavingSchedule}
              className="px-4 py-1.5 bg-[#0B3C9D] text-white rounded-lg text-xs font-semibold hover:bg-[#082b70] disabled:bg-slate-300"
            >
              {isSavingSchedule ? 'Saving...' : 'Confirm Schedule'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Complete Visit Modal */}
      <Modal
        isOpen={isCompleteModalOpen}
        onClose={() => setIsCompleteModalOpen(false)}
        title={`Complete visit - ${completingEvc?.application_code || ''}`}
      >
        <form onSubmit={handleSaveComplete} className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Visit Observations & Remarks *
            </label>
            <textarea
              rows={4}
              value={completionRemarks}
              onChange={(e) => setCompletionRemarks(e.target.value)}
              required
              placeholder="Summary of findings, infrastructure verification, deficiency status..."
              className="w-full p-2 border border-slate-300 rounded-lg text-xs bg-white text-slate-800 focus:outline-none focus:border-[#0B3C9D]"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">
              Upload Signed EVC Report (PDF)
            </label>
            <input
              type="file"
              accept=".pdf"
              onChange={(e) => setReportFile(e.target.files?.[0] || null)}
              className="w-full text-xs text-slate-600 file:mr-2 file:py-1 file:px-2.5 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-[#0B3C9D] hover:file:bg-blue-100"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsCompleteModalOpen(false)}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingReport}
              className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg text-xs font-semibold hover:bg-emerald-700 disabled:bg-slate-300"
            >
              {isSubmittingReport ? 'Submitting...' : 'Mark Visit Complete'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
