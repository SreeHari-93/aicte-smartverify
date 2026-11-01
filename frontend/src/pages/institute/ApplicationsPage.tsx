import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Plus,
  Loader2,
  CheckCircle,
  Clock,
  AlertTriangle,
  Send,
} from 'lucide-react';
import {
  instituteApi,
  ApplicationItem,
  ApplicationListResponse,
  DocumentItem,
} from '../../api/institute';
import { workflowApi, ApplicationWorkflow } from '../../api/workflow';
import { StatusPill } from '../../components/StatusPill';
import { Modal } from '../../components/Modal';
import { Drawer } from '../../components/Drawer';
import { ActionMenu } from '../../components/ActionMenu';
import { DataTable, ColumnDef } from '../../components/DataTable';

export const ApplicationsPage: React.FC = () => {
  const [data, setData] = useState<ApplicationListResponse | null>(null);
  const [workflows, setWorkflows] = useState<ApplicationWorkflow[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('ALL');

  // Modal State for New Application
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [category, setCategory] = useState('Extension of Approval (EoA)');
  const [academicYear, setAcademicYear] = useState('2026-2027');
  const [programme, setProgramme] = useState('Engineering & Technology');
  const [intake, setIntake] = useState<number>(60);
  const [details, setDetails] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createMsg, setCreateMsg] = useState<string | null>(null);

  // Resubmit Modal State
  const [isResubmitModalOpen, setIsResubmitModalOpen] = useState(false);
  const [resubmitTargetApp, setResubmitTargetApp] = useState<ApplicationItem | null>(null);
  const [resubmitTargetWf, setResubmitTargetWf] = useState<ApplicationWorkflow | null>(null);
  const [resubmitReason, setResubmitReason] = useState('');
  const [resubmitText, setResubmitText] = useState('');
  const [resubmitDocIds, setResubmitDocIds] = useState<number[]>([]);
  const [isResubmitting, setIsResubmitting] = useState(false);
  const [resubmitSuccessMsg, setResubmitSuccessMsg] = useState<string | null>(null);

  // Drawer State for Viewing Application Details & Workflow Stepper
  const [selectedApp, setSelectedApp] = useState<ApplicationItem | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState<ApplicationWorkflow | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const [highlightedId, setHighlightedId] = useState<number | null>(null);
  const [unavailableNotice, setUnavailableNotice] = useState<string | null>(null);
  const handledParamRef = useRef<string | null>(null);

  const fetchApplications = async () => {
    try {
      setIsLoading(true);
      const [res, wfList, docs] = await Promise.all([
        instituteApi.getApplications(),
        workflowApi.getApplications().catch(() => [] as ApplicationWorkflow[]),
        instituteApi.getDocuments().catch(() => [] as DocumentItem[]),
      ]);
      setData(res);
      setWorkflows(wfList);
      setDocuments(docs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  // Handle open query param once on load
  useEffect(() => {
    const targetCode = searchParams.get('open') || searchParams.get('application');
    if (!targetCode || isLoading) return;
    if (handledParamRef.current === targetCode) return;
    handledParamRef.current = targetCode;

    if (activeFilter !== 'ALL') setActiveFilter('ALL');

    const items = data?.items || [];
    const targetLower = targetCode.toLowerCase();
    const match = items.find(
      (a) =>
        String(a.id) === targetCode ||
        (a.application_id && a.application_id.toLowerCase() === targetLower)
    );

    if (match) {
      setHighlightedId(match.id);
      handleOpenDrawer(match);
      setTimeout(() => {
        const el = document.getElementById(`inst-app-row-${match.id}`);
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
  }, [searchParams, data, isLoading]);

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setCreateMsg(null);
    try {
      await workflowApi.submitApplication({
        category,
        academic_year: academicYear,
        programme,
        intake: Number(intake) || 60,
        details,
        document_ids: selectedDocIds,
      });
      setCreateMsg('Application submitted successfully.');
      setTimeout(() => {
        setIsModalOpen(false);
        setCreateMsg(null);
        setSelectedDocIds([]);
        setDetails('');
        fetchApplications();
      }, 1500);
    } catch (err: any) {
      console.error(err);
      setCreateMsg(err.response?.data?.detail || 'Failed to submit application.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenResubmitModal = (app: ApplicationItem, wf?: ApplicationWorkflow | null) => {
    const matchedWf = wf || workflows.find((w) => w.application_code === app.application_id || w.application_id === app.id);
    const returnHist = matchedWf?.history?.slice().reverse().find((h) => h.action === 'RETURN');
    setResubmitTargetApp(app);
    setResubmitTargetWf(matchedWf || null);
    setResubmitReason(returnHist?.reason || 'Deficiency or clarification requested by reviewing officer.');
    setResubmitText('');
    setResubmitDocIds([]);
    setResubmitSuccessMsg(null);
    setIsResubmitModalOpen(true);
  };

  const handleResubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resubmitTargetWf && !resubmitTargetApp) return;
    setIsResubmitting(true);
    setResubmitSuccessMsg(null);
    try {
      const targetId = resubmitTargetWf ? resubmitTargetWf.application_id : resubmitTargetApp!.id;
      await workflowApi.resubmitApplication(targetId, {
        response_text: resubmitText,
        document_ids: resubmitDocIds,
      });
      setResubmitSuccessMsg('Application successfully resubmitted. Review restarted.');
      setTimeout(() => {
        setIsResubmitModalOpen(false);
        setResubmitSuccessMsg(null);
        setIsDrawerOpen(false);
        fetchApplications();
      }, 1500);
    } catch (err: any) {
      console.error(err);
      alert(err.response?.data?.detail || 'Failed to resubmit application.');
    } finally {
      setIsResubmitting(false);
    }
  };

  const handleOpenDrawer = (app: ApplicationItem) => {
    setSelectedApp(app);
    const wf = workflows.find((w) => w.application_code === app.application_id || w.application_id === app.id);
    setSelectedWorkflow(wf || null);
    setIsDrawerOpen(true);
  };

  const filteredItems = (data?.items || []).filter((item) => {
    if (activeFilter === 'ALL') return true;
    const wf = workflows.find((w) => w.application_code === item.application_id || w.application_id === item.id);
    if (activeFilter === 'RETURNED') {
      return item.status === 'RETURNED' || wf?.status === 'RETURNED';
    }
    return item.status.toUpperCase() === activeFilter;
  });

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {unavailableNotice && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold rounded-lg flex items-center justify-between">
          <span>{unavailableNotice}</span>
          <button onClick={() => setUnavailableNotice(null)} className="text-amber-700 hover:text-amber-900 font-bold ml-2">×</button>
        </div>
      )}
      {/* Page Header Card */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Applications
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Submit applications and track review stages.
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="px-4 py-2 bg-[#F58220] hover:bg-[#E06F0F] text-white text-xs font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-xs cursor-pointer"
        >
          <Plus size={16} />
          <span>New application</span>
        </button>
      </div>

      {/* Filter Tabs Row */}
      <div className="bg-white rounded-xl p-2 border border-slate-200 shadow-sm flex items-center gap-2 overflow-x-auto scrollbar-none">
        {[
          { key: 'ALL', label: `All applications (${data?.items?.length || 0})` },
          { key: 'SUBMITTED', label: 'Submitted' },
          { key: 'RETURNED', label: 'Returned' },
          { key: 'UNDER_REVIEW', label: 'Under review' },
          { key: 'APPROVED', label: 'Approved' },
          { key: 'REJECTED', label: 'Rejected' },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setActiveFilter(f.key)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors cursor-pointer ${
              activeFilter === f.key
                ? 'bg-[#0B3C9D] text-white'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 border border-slate-200'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Applications Table Card */}
      {(() => {
        const columns: ColumnDef<ApplicationItem>[] = [
          {
            key: 'application_id',
            header: 'Application ID',
            width: '15%',
            align: 'left',
            render: (app) => (
              <span className="font-mono font-medium text-[#0B3C9D] text-xs">
                {app.application_id}
              </span>
            ),
          },
          {
            key: 'category',
            header: 'Category',
            width: '22%',
            align: 'left',
            render: (app) => (
              <span className="text-slate-800 text-xs font-medium line-clamp-2 block" title={app.category}>
                {app.category}
              </span>
            ),
          },
          {
            key: 'stage',
            header: 'Stage & reviewer',
            width: '24%',
            align: 'left',
            render: (app) => {
              const wf = workflows.find((w) => w.application_code === app.application_id || w.application_id === app.id);
              return (
                <div>
                  <div className="font-medium text-slate-900 text-xs">
                    {wf ? wf.current_stage_name : (app.status === 'APPROVED' ? 'Final Approved' : 'Desktop Scrutiny')}
                  </div>
                  <div className="text-[11px] text-slate-600">
                    {wf?.assigned_officer_name || 'AICTE Desk'}
                  </div>
                </div>
              );
            },
          },
          {
            key: 'due_date',
            header: 'Due date & SLA',
            width: '17%',
            align: 'left',
            render: (app) => {
              const wf = workflows.find((w) => w.application_code === app.application_id || w.application_id === app.id);
              const sla = !wf ? 'ON_TRACK' : wf.is_overdue || (wf.days_remaining !== undefined && wf.days_remaining < 0) ? 'OVERDUE' : (wf.days_remaining !== undefined && wf.days_remaining <= 7) ? 'DUE_SOON' : 'ON_TRACK';
              return (
                <div className="text-xs">
                  <div className="text-slate-600">
                    Due: {wf?.due_date ? new Date(wf.due_date).toLocaleDateString('en-GB') : (app.filed_on ? new Date(app.filed_on).toLocaleDateString('en-GB') : '-')}
                  </div>
                  <div className="mt-0.5">
                    <span
                      className={`px-1.5 py-0.2 rounded text-[10px] font-medium ${
                        sla === 'OVERDUE'
                          ? 'bg-red-100 text-red-800 border border-red-200'
                          : sla === 'DUE_SOON'
                          ? 'bg-amber-100 text-amber-800 border border-amber-200'
                          : 'bg-emerald-100 text-emerald-800 border border-emerald-200'
                      }`}
                    >
                      {sla === 'OVERDUE' ? 'Overdue' : sla === 'DUE_SOON' ? 'Due soon' : 'On track'}
                    </span>
                  </div>
                </div>
              );
            },
          },
          {
            key: 'status',
            header: 'Status',
            width: '10%',
            align: 'left',
            render: (app) => {
              const wf = workflows.find((w) => w.application_code === app.application_id || w.application_id === app.id);
              const isReturned = app.status === 'RETURNED' || wf?.status === 'RETURNED';
              return isReturned ? (
                <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-900 border border-amber-300 inline-flex items-center gap-1">
                  <AlertTriangle size={10} className="text-amber-700" />
                  <span>Returned</span>
                </span>
              ) : (
                <StatusPill status={app.status} />
              );
            },
          },
          {
            key: 'actions',
            header: 'Action',
            width: '12%',
            align: 'right',
            render: (app) => {
              const wf = workflows.find((w) => w.application_code === app.application_id || w.application_id === app.id);
              const isReturned = app.status === 'RETURNED' || wf?.status === 'RETURNED';
              return (
                <div className="flex justify-end">
                  <ActionMenu
                    primaryAction={{
                      label: 'Timeline',
                      onClick: () => handleOpenDrawer(app),
                    }}
                    menuItems={
                      isReturned
                        ? [
                            {
                              label: 'Resubmit',
                              onClick: () => handleOpenResubmitModal(app, wf),
                            },
                          ]
                        : []
                    }
                  />
                </div>
              );
            },
          },
        ];

        return (
          <DataTable
            columns={columns}
            data={filteredItems}
            keyExtractor={(app) => app.id}
            isLoading={isLoading}
            emptyMessage="No applications found in this filter category."
            isLong={filteredItems.length > 12}
            rowClassName={(app) => (app.id === highlightedId ? 'bg-amber-100/70 transition-colors duration-700' : '')}
          />
        );
      })()}

      {/* New Application Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Submit application"
      >
        <form onSubmit={handleCreateApplication} className="space-y-4 text-xs">
          {createMsg && (
            <div className={`p-3 rounded-lg font-semibold flex items-center gap-2 ${
              createMsg.includes('success') ? 'bg-green-50 border border-green-200 text-[#1E7036]' : 'bg-red-50 border border-red-200 text-red-700'
            }`}>
              <CheckCircle size={16} />
              <span>{createMsg}</span>
            </div>
          )}

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">Application Category *</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full h-10 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              required
            >
              <option value="Extension of Approval (EoA)">Extension of Approval (EoA)</option>
              <option value="Increase in Intake / Additional Course">Increase in Intake / Additional Course</option>
              <option value="Setting Up New Technical Campus">Setting Up New Technical Campus</option>
              <option value="Change of Site / Location">Change of Site / Location</option>
              <option value="Conversion of Diploma to Degree">Conversion of Diploma to Degree</option>
              <option value="Closure of Course / Institute">Closure of Course / Institute</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Academic Year</label>
              <select
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="w-full h-10 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              >
                <option value="2026-2027">2026-2027</option>
                <option value="2027-2028">2027-2028</option>
              </select>
            </div>
            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Proposed Intake (Seats)</label>
              <input
                type="number"
                min={1}
                value={intake}
                onChange={(e) => setIntake(parseInt(e.target.value) || 0)}
                className="w-full h-10 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
                placeholder="e.g. 60, 120"
              />
            </div>
          </div>

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">Programme Stream</label>
            <select
              value={programme}
              onChange={(e) => setProgramme(e.target.value)}
              className="w-full h-10 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
            >
              <option value="Engineering & Technology">Engineering & Technology</option>
              <option value="Management (MBA)">Management (MBA)</option>
              <option value="Computer Applications (MCA)">Computer Applications (MCA)</option>
              <option value="Pharmacy">Pharmacy</option>
              <option value="Architecture & Planning">Architecture & Planning</option>
            </select>
          </div>

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">Remarks / Programme Details</label>
            <textarea
              rows={2}
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              className="w-full p-2.5 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              placeholder="Provide proposed course specializations, existing affiliations or brief remarks..."
            />
          </div>

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">Attach Checklist Documents (Optional)</label>
            <div className="max-h-32 overflow-y-auto border border-slate-200 rounded-lg p-2 bg-slate-50 space-y-1.5">
              {documents.length === 0 ? (
                <p className="text-slate-600 italic text-[11px]">No documents uploaded yet. You can also upload later from Documents menu.</p>
              ) : (
                documents.map((doc) => (
                  <label key={doc.id} className="flex items-center gap-2 text-slate-700 hover:text-[#0B3C9D] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={selectedDocIds.includes(doc.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedDocIds([...selectedDocIds, doc.id]);
                        } else {
                          setSelectedDocIds(selectedDocIds.filter((id) => id !== doc.id));
                        }
                      }}
                      className="rounded text-[#0B3C9D]"
                    />
                    <span className="truncate">{doc.original_filename || doc.document_type_code || `Document #${doc.id}`}</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg text-slate-600">
            <p className="font-semibold text-[#0B3C9D] mb-0.5">Scrutiny SLA:</p>
            <p className="text-[11px] leading-relaxed">
              Upon submission, the workflow is established at Stage 1 (Scrutiny) with assigned regional oversight and SLA timeline.
            </p>
          </div>

          <div className="pt-3 flex justify-end gap-2.5">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 border border-slate-200 rounded-[6px] text-slate-600 font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-[6px] transition-colors flex items-center gap-1.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting && <Loader2 size={14} className="animate-spin" />}
              <span>Submit Application</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Respond & Resubmit Modal */}
      <Modal
        isOpen={isResubmitModalOpen}
        onClose={() => setIsResubmitModalOpen(false)}
        title="Respond to Deficiency & Resubmit Application"
      >
        <form onSubmit={handleResubmit} className="space-y-4 text-xs">
          {resubmitSuccessMsg && (
            <div className="p-3 bg-green-50 border border-green-200 text-[#1E7036] rounded-lg font-semibold flex items-center gap-2">
              <CheckCircle size={16} />
              <span>{resubmitSuccessMsg}</span>
            </div>
          )}

          {/* Deficiency reason callout */}
          <div className="p-3.5 bg-amber-50 border border-amber-300 rounded-xl space-y-1 text-amber-950">
            <div className="flex items-center gap-1.5 font-bold text-amber-900 text-xs">
              <AlertTriangle size={15} className="text-amber-700" />
              <span>Reason for Return / Deficiency Notice:</span>
            </div>
            <p className="text-xs leading-relaxed font-medium pl-5">{resubmitReason}</p>
          </div>

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">
              Institutional Compliance Clarification / Response *
            </label>
            <textarea
              rows={4}
              required
              value={resubmitText}
              onChange={(e) => setResubmitText(e.target.value)}
              placeholder="State how the deficiency has been addressed or provide clarification..."
              className="w-full p-2.5 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
            />
          </div>

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">Attach Supporting Rectification Document(s)</label>
            <div className="max-h-28 overflow-y-auto border border-slate-200 rounded-lg p-2 bg-slate-50 space-y-1.5">
              {documents.length === 0 ? (
                <p className="text-slate-600 italic text-[11px]">No existing documents in repository.</p>
              ) : (
                documents.map((doc) => (
                  <label key={doc.id} className="flex items-center gap-2 text-slate-700 hover:text-[#0B3C9D] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={resubmitDocIds.includes(doc.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setResubmitDocIds([...resubmitDocIds, doc.id]);
                        } else {
                          setResubmitDocIds(resubmitDocIds.filter((id) => id !== doc.id));
                        }
                      }}
                      className="rounded text-[#0B3C9D]"
                    />
                    <span className="truncate">{doc.original_filename || doc.document_type_code || `Document #${doc.id}`}</span>
                  </label>
                ))
              )}
            </div>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg text-slate-600">
            <p className="font-semibold text-[#0B3C9D] mb-0.5">Notice:</p>
            <p className="text-[11px] leading-relaxed">
              Resubmission will return the application to <b>In progress</b> at the returned stage, reset the SLA review clock, and notify the scrutiny officer.
            </p>
          </div>

          <div className="pt-3 flex justify-end gap-2.5">
            <button
              type="button"
              onClick={() => setIsResubmitModalOpen(false)}
              className="px-4 py-2 border border-slate-200 rounded-[6px] text-slate-600 font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isResubmitting || !resubmitText.trim()}
              className="px-5 py-2 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-[6px] transition-colors flex items-center gap-1.5 disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isResubmitting && <Loader2 size={14} className="animate-spin" />}
              <span>Resubmit & Restart Clock</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* View Application & Timeline Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedApp?.application_id || 'Application Overview'}
        subtitle={selectedApp?.category}
      >
        {selectedApp && (
          <div className="space-y-6 text-xs">
            {/* Returned Callout Banner if status is RETURNED */}
            {(selectedApp.status === 'RETURNED' || selectedWorkflow?.status === 'RETURNED') && (
              <div className="p-4 bg-amber-50 border border-amber-300 rounded-xl space-y-2.5 text-amber-950">
                <div className="flex items-center gap-2 text-amber-900 font-bold text-xs">
                  <AlertTriangle size={16} className="text-amber-700" />
                  <span>Action Required: Application Returned for Deficiency</span>
                </div>
                <p className="text-xs leading-relaxed text-slate-700">
                  {selectedWorkflow?.history?.slice().reverse().find((h) => h.action === 'RETURN')?.reason ||
                    'Reviewing officer has returned this application for deficiency or required clarification.'}
                </p>
                <button
                  onClick={() => handleOpenResubmitModal(selectedApp, selectedWorkflow)}
                  className="w-full py-2 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-lg text-xs flex items-center justify-center gap-1.5 shadow-xs"
                >
                  <Send size={13} />
                  <span>Respond and Resubmit</span>
                </button>
              </div>
            )}

            {/* Overview Card */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Application Status:</span>
                <StatusPill status={selectedApp.status} />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Academic Year:</span>
                <span className="font-bold text-[#0F2A5C]">{selectedApp.academic_year}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Programme Stream:</span>
                <span className="font-semibold text-slate-700">{selectedApp.programme}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Reviewing Owner:</span>
                <span className="font-semibold text-[#0B3C9D]">{selectedWorkflow?.assigned_officer_name || 'AICTE Desk'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Current SLA Deadline:</span>
                <span className="font-semibold text-slate-800">
                  {selectedWorkflow?.due_date ? new Date(selectedWorkflow.due_date).toLocaleDateString('en-GB') : '-'}
                </span>
              </div>
            </div>

            {/* Stage Timeline Stepper */}
            <div>
              <h4 className="font-bold text-[#0B3C9D] uppercase tracking-wider text-[11px] mb-3 flex items-center gap-1.5">
                <Clock size={14} />
                <span>Workflow timeline</span>
              </h4>

              {selectedWorkflow?.stages && selectedWorkflow.stages.length > 0 ? (
                <div className="relative pl-6 space-y-4 before:content-[''] before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-200">
                  {selectedWorkflow.stages.map((stage: any) => {
                    const isPassed = stage.sequence < selectedWorkflow.current_stage_sequence;
                    const isCurrent = stage.sequence === selectedWorkflow.current_stage_sequence;
                    return (
                      <div key={stage.id} className="relative">
                        <div
                          className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                            isPassed
                              ? 'bg-emerald-600 text-white'
                              : isCurrent
                              ? 'bg-[#F58220] text-white ring-4 ring-amber-100'
                              : 'bg-slate-200 text-slate-500'
                          }`}
                        >
                          {isPassed ? '✓' : stage.sequence}
                        </div>
                        <div className={`p-2.5 rounded-lg border ${isCurrent ? 'bg-amber-50/70 border-amber-300' : 'bg-white border-slate-200'}`}>
                          <div className="flex items-center justify-between">
                            <span className={`font-semibold ${isCurrent ? 'text-amber-900 font-bold' : 'text-slate-700'}`}>
                              {stage.stage_name}
                            </span>
                            <span className="text-[10px] font-mono text-slate-600">SLA: {stage.sla_days}d</span>
                          </div>
                          <span className="text-[10px] text-slate-500 block mt-0.5">Role: {stage.responsible_role.replace('_', ' ')}</span>
                          {isCurrent && (
                            <span className="mt-1.5 inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-[#F58220] text-white">
                              Active Stage in Progress
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-3 bg-slate-50 rounded-lg text-slate-500 text-xs">
                  Progressing through standard handbook scrutiny.
                </div>
              )}
            </div>

            {/* Case Summary */}
            {selectedWorkflow?.case_summary && (
              <div className="p-3 bg-blue-50/70 border border-blue-200 rounded-xl text-blue-950 text-xs">
                <span className="font-bold text-[#0B3C9D] block mb-1">Case summary:</span>
                <p className="leading-relaxed text-slate-700">{selectedWorkflow.case_summary}</p>
              </div>
            )}
          </div>
        )}
      </Drawer>
    </div>
  );
};
