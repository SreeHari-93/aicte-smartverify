import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Clock,
  RotateCcw,
  AlertTriangle,
  Calendar,
  Search,
  FileText,
  RefreshCw,
  AlertOctagon,
  Eye,
} from 'lucide-react';
import {
  workflowApi,
  ApplicationWorkflow,
  WorkflowDashboardData,
  WorkflowOfficer,
} from '../../api/workflow';
import { StatusPill } from '../../components/StatusPill';
import { WorkflowDetailDrawer } from '../../components/WorkflowDetailDrawer';
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

export const AdminWorkflowPage: React.FC = () => {
  const [dashboardData, setDashboardData] = useState<WorkflowDashboardData | null>(null);
  const [workflows, setWorkflows] = useState<ApplicationWorkflow[]>([]);
  const [officers, setOfficers] = useState<WorkflowOfficer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedWorkflow, setSelectedWorkflow] = useState<ApplicationWorkflow | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [regionFilter, setRegionFilter] = useState('ALL');
  const [stageFilter, setStageFilter] = useState('ALL');
  const [officerFilter, setOfficerFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchParams, setSearchParams] = useSearchParams();
  const [highlightedId, setHighlightedId] = useState<number | null>(null);
  const [unavailableNotice, setUnavailableNotice] = useState<string | null>(null);
  const handledParamRef = useRef<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [dash, apps, offs] = await Promise.all([
        workflowApi.getDashboard(regionFilter !== 'ALL' ? regionFilter : undefined),
        workflowApi.getApplications({
          region: regionFilter !== 'ALL' ? regionFilter : undefined,
          stage: stageFilter !== 'ALL' ? stageFilter : undefined,
          officer_id: officerFilter !== 'ALL' ? Number(officerFilter) : undefined,
          status_filter: statusFilter !== 'ALL' ? statusFilter : undefined,
          search: searchQuery || undefined,
        }),
        workflowApi.getOfficers(),
      ]);
      setDashboardData(dash);
      setWorkflows(apps);
      setOfficers(offs);
    } catch (err) {
      console.error('Error fetching workflow dashboard:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [regionFilter, stageFilter, officerFilter, statusFilter]);

  // Handle open query param once on load
  useEffect(() => {
    const targetCode = searchParams.get('application') || searchParams.get('open');
    if (!targetCode || isLoading) return;
    if (handledParamRef.current === targetCode) return;
    handledParamRef.current = targetCode;

    // Reset filters if hidden
    if (regionFilter !== 'ALL') setRegionFilter('ALL');
    if (stageFilter !== 'ALL') setStageFilter('ALL');
    if (officerFilter !== 'ALL') setOfficerFilter('ALL');
    if (statusFilter !== 'ALL') setStatusFilter('ALL');
    if (searchQuery) setSearchQuery('');

    const targetLower = targetCode.toLowerCase();
    const match = workflows.find(
      (w) =>
        String(w.id) === targetCode ||
        String(w.application_id) === targetCode ||
        (w.application_code && w.application_code.toLowerCase() === targetLower)
    );

    if (match) {
      setSelectedWorkflow(match);
      setIsDrawerOpen(true);
      setHighlightedId(match.id);
      setTimeout(() => {
        const el = document.getElementById(`workflow-row-${match.id}`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 150);
      setTimeout(() => setHighlightedId(null), 3000);
    } else {
      setUnavailableNotice('This case is no longer available.');
      setTimeout(() => setUnavailableNotice(null), 5000);
    }

    // Clear query param with replace: true
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('application');
    nextParams.delete('open');
    setSearchParams(nextParams, { replace: true });
  }, [searchParams, workflows, isLoading]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  const handleOpenWorkflow = (wf: ApplicationWorkflow) => {
    setSelectedWorkflow(wf);
    setIsDrawerOpen(true);
  };

  const handleWorkflowUpdated = (updated: ApplicationWorkflow) => {
    setSelectedWorkflow(updated);
    setWorkflows((prev) =>
      prev.map((w) => (w.id === updated.id ? updated : w))
    );
    workflowApi.getDashboard(regionFilter !== 'ALL' ? regionFilter : undefined).then(setDashboardData);
  };

  const stageOptions = useMemo(() => {
    const set = new Set<string>();
    workflows.forEach((w) => set.add(w.current_stage_name));
    return Array.from(set);
  }, [workflows]);

  return (
    <div className="space-y-6 pb-12">
      {/* Title Header Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">
              Workflow
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Stage tracking, SLA monitoring, and case decisions.
            </p>
          </div>

          <button
            onClick={fetchData}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-white border border-slate-300 hover:border-slate-400 text-slate-700 text-xs font-medium rounded-md shadow-sm transition-colors"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin text-[#0B3C9D]' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* 1. Stat Cards / Counters */}
      {dashboardData && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
              <span>Total applications</span>
              <FileText size={18} className="text-[#0B3C9D]" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">
              {dashboardData.counters.total}
            </p>
            <p className="text-xs text-slate-600 mt-1">Across all templates</p>
          </div>

          <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
              <span>In progress</span>
              <Clock size={18} className="text-blue-600" />
            </div>
            <p className="text-2xl font-bold text-blue-700 mt-2">
              {dashboardData.counters.in_progress}
            </p>
            <p className="text-xs text-slate-600 mt-1">Active stage evaluation</p>
          </div>

          <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
              <span>Returned</span>
              <RotateCcw size={18} className="text-amber-600" />
            </div>
            <p className="text-2xl font-bold text-amber-600 mt-2">
              {dashboardData.counters.returned}
            </p>
            <p className="text-xs text-slate-600 mt-1">Under clarification</p>
          </div>

          <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
              <span>Due in 7 days</span>
              <Calendar size={18} className="text-purple-600" />
            </div>
            <p className="text-2xl font-bold text-purple-700 mt-2">
              {dashboardData.counters.due_in_7_days}
            </p>
            <p className="text-xs text-purple-600 mt-1">Approaching SLA</p>
          </div>

          <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-600 text-xs font-medium">
              <span>Overdue</span>
              <AlertTriangle size={18} className="text-red-600" />
            </div>
            <p className="text-2xl font-bold text-red-600 mt-2">
              {dashboardData.counters.overdue}
            </p>
            <p className="text-xs text-red-500 mt-1">Exceeded SLA</p>
          </div>
        </div>
      )}

      {/* 2. Ageing Buckets */}
      {dashboardData && (
        <div className="bg-white rounded-lg p-6 border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-slate-900">
              Ageing by stage
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Distribution of pending cases by time in current stage.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {dashboardData.ageing_buckets.map((b) => (
              <div
                key={b.bucket}
                className="p-4 rounded-lg border border-slate-200 bg-slate-50 flex flex-col justify-between"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-800">{b.bucket}</span>
                  <span className="text-base font-bold text-slate-900">{b.count} cases</span>
                </div>

                <div className="mt-3 space-y-1 text-xs">
                  <div className="flex justify-between items-center text-emerald-800">
                    <span>On track</span>
                    <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-xs font-medium">
                      {b.on_track}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-amber-800">
                    <span>Due soon (≤ 2d)</span>
                    <span className="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 text-xs font-medium">
                      {b.due_soon}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-red-800">
                    <span>Overdue</span>
                    <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-800 text-xs font-medium">
                      {b.overdue}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. Middle Section: Stage Funnel & Region Distribution */}
      {dashboardData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Stage Funnel */}
          <div className="bg-white rounded-lg p-6 border border-slate-200 shadow-sm flex flex-col justify-between">
            <div>
              <h2 className="text-base font-semibold text-slate-900 mb-1">
                Stage funnel
              </h2>
              <p className="text-xs text-slate-600 mb-4">
                Active volume across workflow stages.
              </p>

              <div className="space-y-3">
                {dashboardData.stage_funnel.map((item) => {
                  const percent = dashboardData.counters.total
                    ? Math.round((item.count / dashboardData.counters.total) * 100)
                    : 0;
                  return (
                    <div key={item.stage} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-slate-700">{item.stage}</span>
                        <span className="font-semibold text-[#0B3C9D]">
                          {item.count} ({percent}%)
                        </span>
                      </div>
                      <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#0B3C9D] rounded-full"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Region Table */}
          <div className="bg-white rounded-lg p-6 border border-slate-200 shadow-sm">
            <h2 className="text-base font-semibold text-slate-900 mb-1">
              Regional caseloads
            </h2>
            <p className="text-xs text-slate-600 mb-4">
              Regional distribution of pending, returned, and overdue applications.
            </p>

            <div className="table-container">
              <table className="aicte-table">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-600 font-semibold">
                    <th className="py-2.5 px-3">Region</th>
                    <th className="py-2.5 px-3">Total</th>
                    <th className="py-2.5 px-3">In progress</th>
                    <th className="py-2.5 px-3">Returned</th>
                    <th className="py-2.5 px-3">Overdue</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dashboardData.region_table.map((r) => (
                    <tr key={r.region} className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 px-3 font-medium text-slate-900">{r.region}</td>
                      <td className="py-2.5 px-3 text-slate-700">{r.total}</td>
                      <td className="py-2.5 px-3 text-blue-700">{r.in_progress}</td>
                      <td className="py-2.5 px-3 text-amber-700">{r.returned}</td>
                      <td className="py-2.5 px-3">
                        {r.overdue > 0 ? (
                          <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">
                            {r.overdue}
                          </span>
                        ) : (
                          <span className="text-slate-600">0</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 4. Stage Bottlenecks & SLA Variance */}
      {dashboardData && dashboardData.stage_analytics && (
        <div className="bg-white rounded-lg p-6 border border-slate-200 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-semibold text-slate-900">
                Stage duration and benchmarks
              </h2>
              <p className="text-xs text-slate-600 mt-0.5">
                Target SLA compared against actual average days spent per stage.
              </p>
            </div>

            {dashboardData.worst_overdue_stage && dashboardData.worst_overdue_stage.overdue_count > 0 && (
              <div className="px-3 py-1.5 bg-red-50 border border-red-200 text-red-800 rounded-md text-xs font-medium flex items-center gap-2 shrink-0">
                <AlertOctagon size={15} className="text-red-600" />
                <span>
                  Most overdue stage: <strong>{dashboardData.worst_overdue_stage.stage_name}</strong> ({dashboardData.worst_overdue_stage.overdue_count} overdue)
                </span>
              </div>
            )}
          </div>

          <div className="table-container">
            <table className="aicte-table">
              <thead>
                <tr className="border-b border-slate-200 text-slate-600 font-semibold">
                  <th className="py-2.5 px-3">Stage</th>
                  <th className="py-2.5 px-3">SLA</th>
                  <th className="py-2.5 px-3">Actual avg days</th>
                  <th className="py-2.5 px-3">Variance</th>
                  <th className="py-2.5 px-3">Completed</th>
                  <th className="py-2.5 px-3 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {dashboardData.stage_analytics.map((s) => (
                  <tr key={s.stage_id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-medium text-slate-900">{s.stage_name}</td>
                    <td className="py-2.5 px-3 text-slate-700">{s.sla_days} days</td>
                    <td className="py-2.5 px-3 text-[#0B3C9D] font-medium">{s.avg_days_spent} days</td>
                    <td className="py-2.5 px-3">
                      {s.variance_days > 0 ? (
                        <span className="text-red-700 font-medium">+{s.variance_days}d (Delay)</span>
                      ) : (
                        <span className="text-emerald-700 font-medium">{s.variance_days}d (Ahead)</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">{s.completed_cases} cases</td>
                    <td className="py-2.5 px-3 text-right">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          s.status === 'BOTTLENECK'
                            ? 'bg-red-100 text-red-800'
                            : s.status === 'SLIGHT_DELAY'
                            ? 'bg-amber-100 text-amber-800'
                            : 'bg-emerald-100 text-emerald-800'
                        }`}
                      >
                        {s.status.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase())}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 5. Officer & Committee Workload Tables */}
      {dashboardData && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          {/* Officer Workload */}
          <div className="lg:col-span-7 bg-white rounded-lg p-6 border border-slate-200 shadow-sm flex flex-col">
            <h2 className="text-base font-semibold text-slate-900 mb-4">
              Officer workload
            </h2>

            <div className="overflow-x-auto max-h-[420px] overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
              <table className="w-full text-sm border-collapse" style={{ tableLayout: 'fixed' }}>
                <colgroup>
                  <col style={{ width: '30%' }} />
                  <col style={{ width: '18%' }} />
                  <col style={{ width: '16%' }} />
                  <col style={{ width: '12%' }} />
                  <col style={{ width: '12%' }} />
                  <col style={{ width: '12%' }} />
                </colgroup>
                <thead className="sticky top-0 bg-white z-10 shadow-[0_1px_0_0_#e2e8f0]">
                  <tr className="border-b border-slate-200 text-slate-600 font-semibold h-10">
                    <th className="py-2.5 px-3 text-left">Officer</th>
                    <th className="py-2.5 px-3 text-left">Role</th>
                    <th className="py-2.5 px-3 text-left">Region</th>
                    <th className="py-2.5 px-3 text-right">Active</th>
                    <th className="py-2.5 px-3 text-right">Overdue</th>
                    <th className="py-2.5 px-3 text-right pr-4">Completed</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dashboardData.officer_workload.map((o) => (
                    <tr key={o.officer_id} className="hover:bg-slate-50 transition-colors h-[52px]">
                      <td className="py-2 px-3 align-middle">
                        <div className="font-medium text-slate-900 truncate" title={o.name || o.email}>
                          {o.name || o.email.split('@')[0]}
                        </div>
                        <div className="text-xs text-slate-600 truncate" title={o.email}>
                          {o.email}
                        </div>
                      </td>
                      <td className="py-2 px-3 align-middle text-left">
                        <span className="inline-block px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 whitespace-nowrap">
                          {formatRole(o.role)}
                        </span>
                      </td>
                      <td className="py-2 px-3 align-middle text-left text-slate-800 text-sm">
                        {o.region}
                      </td>
                      <td className="py-2 px-3 align-middle text-right text-[#0B3C9D] font-medium text-sm">
                        {o.assigned_count}
                      </td>
                      <td className="py-2 px-3 align-middle text-right">
                        {o.overdue_count > 0 ? (
                          <span className="inline-block px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700">
                            {o.overdue_count}
                          </span>
                        ) : (
                          <span className="text-slate-500 font-normal text-sm">0</span>
                        )}
                      </td>
                      <td className="py-2 px-3 align-middle text-right pr-4 text-emerald-700 font-medium text-sm">
                        {o.completed_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Committee Member Workload */}
          <div className="lg:col-span-5 bg-white rounded-lg p-6 border border-slate-200 shadow-sm flex flex-col">
            <h2 className="text-base font-semibold text-slate-900 mb-4">
              Committee workload
            </h2>

            <div className="overflow-x-auto max-h-[420px] overflow-y-auto" style={{ scrollbarWidth: 'thin' }}>
              <table className="w-full text-sm border-collapse" style={{ tableLayout: 'fixed' }}>
                <colgroup>
                  <col style={{ width: '38%' }} />
                  <col style={{ width: '18%' }} />
                  <col style={{ width: '18%' }} />
                  <col style={{ width: '26%' }} />
                </colgroup>
                <thead className="sticky top-0 bg-white z-10 shadow-[0_1px_0_0_#e2e8f0]">
                  <tr className="border-b border-slate-200 text-slate-600 font-semibold h-10">
                    <th className="py-2.5 px-3 text-left">Member</th>
                    <th className="py-2.5 px-3 text-left">Region</th>
                    <th className="py-2.5 px-3 text-right">Active cases</th>
                    <th className="py-2.5 px-3 text-right pr-4">Visits</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dashboardData.committee_workload && dashboardData.committee_workload.length > 0 ? (
                    dashboardData.committee_workload.map((c) => (
                      <tr key={c.member_id} className="hover:bg-slate-50 transition-colors h-[52px]">
                        <td className="py-2 px-3 align-middle">
                          <div className="font-medium text-slate-900 truncate" title={c.name || c.email}>
                            {c.name || c.email.split('@')[0]}
                          </div>
                          <div className="text-xs text-slate-600 truncate" title={c.email}>
                            {c.email}
                          </div>
                        </td>
                        <td className="py-2 px-3 align-middle text-left text-slate-800 text-sm">
                          {c.region}
                        </td>
                        <td className="py-2 px-3 align-middle text-right text-sm">
                          {c.active_cases > 0 ? (
                            <span className="text-[#0B3C9D] font-medium">{c.active_cases}</span>
                          ) : (
                            <span className="text-slate-500 font-normal">0</span>
                          )}
                        </td>
                        <td className="py-2 px-3 align-middle text-right pr-4 text-sm">
                          {c.visits_display && c.visits_display !== '0' ? (
                            <span className="text-slate-800 font-medium">{c.visits_display}</span>
                          ) : (
                            <span className="text-slate-500 font-normal">0</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={4} className="py-6 text-center text-slate-500 text-xs">
                        No active committee visits assigned.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 5. Oldest Pending Cases */}
      {dashboardData && dashboardData.oldest_pending.length > 0 && (
        <div className="bg-white rounded-lg p-6 border border-slate-200 shadow-sm">
          <div className="mb-4">
            <h2 className="text-base font-semibold text-slate-900">
              Oldest pending cases
            </h2>
            <p className="text-xs text-slate-600 mt-0.5">
              Cases pending the longest in the current stage.
            </p>
          </div>

          <div className="table-container">
            <table className="aicte-table">
              <thead>
                <tr className="border-b border-slate-200 text-slate-600 font-semibold">
                  <th className="py-2.5 px-3 w-[15%]">App ID</th>
                  <th className="py-2.5 px-3 w-[25%]">Institution</th>
                  <th className="py-2.5 px-3 w-[15%]">Current stage</th>
                  <th className="py-2.5 px-3 w-[15%]">Region & officer</th>
                  <th className="py-2.5 px-3 w-[15%]">Days in stage</th>
                  <th className="py-2.5 px-3 w-[15%] text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {dashboardData.oldest_pending.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-mono font-medium text-[#0B3C9D]">
                      {item.application_id}
                    </td>
                    <td className="py-2.5 px-3 font-medium text-slate-900 truncate" title={item.institute_name}>
                      {item.institute_name}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">{item.stage_name}</td>
                    <td className="py-2.5 px-3 text-slate-600 text-xs">
                      <div>{item.region}</div>
                      <div className="text-[11px] text-slate-600 truncate" title={item.assigned_officer || ''}>{item.assigned_officer || 'Unassigned'}</div>
                    </td>
                    <td className="py-2.5 px-3 text-slate-700">
                      <div>{item.age_days} days</div>
                      <div className="mt-0.5">
                        <StatusPill status={item.sla_badge} />
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => {
                          const match = workflows.find((w) => w.id === item.id);
                          if (match) handleOpenWorkflow(match);
                        }}
                        className="px-2.5 py-1 bg-[#0B3C9D] hover:bg-[#082B70] text-white rounded text-xs font-medium"
                      >
                        Open case
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {unavailableNotice && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold rounded-lg flex items-center justify-between">
          <span>{unavailableNotice}</span>
          <button onClick={() => setUnavailableNotice(null)} className="text-amber-700 hover:text-amber-900 font-bold ml-2">×</button>
        </div>
      )}
      {/* 6. Applications Register */}
      <div className="bg-white rounded-lg p-6 border border-slate-200 shadow-sm space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-4">
          <div>
            <h2 className="text-base font-semibold text-slate-900">
              Applications ({workflows.length})
            </h2>
            <p className="text-xs text-slate-600">
              Current status of all applications.
            </p>
          </div>

          {/* Search Box */}
          <form onSubmit={handleSearchSubmit} className="flex items-center gap-2">
            <div className="relative">
              <Search size={15} className="absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search ID, officer, stage..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-3 py-1.5 text-xs rounded-md border border-slate-300 focus:border-[#0B3C9D] outline-none w-56 placeholder:text-slate-500"
              />
            </div>
            <button
              type="submit"
              className="px-3 py-1.5 bg-[#0B3C9D] text-white text-xs font-medium rounded-md hover:bg-[#082B70]"
            >
              Filter
            </button>
          </form>
        </div>

        {/* Filter Selectors */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="block text-slate-600 font-medium mb-1 text-xs">
              Region
            </label>
            <select
              value={regionFilter}
              onChange={(e) => setRegionFilter(e.target.value)}
              className="w-full p-2 rounded-md border border-slate-300 bg-white text-xs text-slate-700"
            >
              <option value="ALL">All regions</option>
              <option value="Southern">Southern</option>
              <option value="Northern">Northern</option>
              <option value="Western">Western</option>
              <option value="Eastern">Eastern</option>
              <option value="Central">Central</option>
            </select>
          </div>

          <div>
            <label className="block text-slate-600 font-medium mb-1 text-xs">
              Stage
            </label>
            <select
              value={stageFilter}
              onChange={(e) => setStageFilter(e.target.value)}
              className="w-full p-2 rounded-md border border-slate-300 bg-white text-xs text-slate-700"
            >
              <option value="ALL">All stages</option>
              {stageOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-slate-600 font-medium mb-1 text-xs">
              Assigned officer
            </label>
            <select
              value={officerFilter}
              onChange={(e) => setOfficerFilter(e.target.value)}
              className="w-full p-2 rounded-md border border-slate-300 bg-white text-xs text-slate-700"
            >
              <option value="ALL">All officers</option>
              {officers.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.email} ({formatRole(o.role)})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-slate-600 font-medium mb-1 text-xs">
              Status
            </label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full p-2 rounded-md border border-slate-300 bg-white text-xs text-slate-700"
            >
              <option value="ALL">All statuses</option>
              <option value="IN_PROGRESS">In progress</option>
              <option value="RETURNED">Returned</option>
              <option value="ON_HOLD">On hold</option>
              <option value="COMPLETED">Completed</option>
            </select>
          </div>
        </div>

        {/* Master Table */}
        <div className="p-2">
          {(() => {
            const columns: ColumnDef<ApplicationWorkflow>[] = [
              {
                key: 'application_code',
                header: 'Application ID',
                width: '14%',
                align: 'left',
                render: (wf) => (
                  <span className="font-mono font-medium text-[#0B3C9D] text-xs">
                    {wf.application_code}
                  </span>
                ),
              },
              {
                key: 'institute',
                header: 'Institution & region',
                width: '26%',
                align: 'left',
                render: (wf) => (
                  <div>
                    <div className="font-medium text-slate-900 truncate block text-xs" title={wf.institute_name}>
                      {wf.institute_name}
                    </div>
                    <div className="text-[11px] text-slate-600">
                      {wf.region || 'AICTE Region'}
                    </div>
                  </div>
                ),
              },
              {
                key: 'category_template',
                header: 'Category & template',
                width: '18%',
                align: 'left',
                render: (wf) => (
                  <div>
                    <div className="text-slate-700 line-clamp-1 text-xs" title={wf.category}>{wf.category}</div>
                    <div className="text-[10px] font-mono text-slate-600">{wf.template_code}</div>
                  </div>
                ),
              },
              {
                key: 'stage_officer',
                header: 'Stage & officer',
                width: '18%',
                align: 'left',
                render: (wf) => (
                  <div>
                    <div className="font-medium text-slate-800 text-xs">{wf.current_stage_name}</div>
                    <div className="text-[11px] text-slate-600 truncate" title={wf.assigned_officer_name || 'Unassigned'}>
                      {wf.assigned_officer_name || 'Unassigned'}
                    </div>
                  </div>
                ),
              },
              {
                key: 'status_due',
                header: 'Status & due date',
                width: '12%',
                align: 'left',
                render: (wf) => (
                  <div>
                    <StatusPill status={wf.status} />
                    <div className="mt-1 text-[11px]">
                      <span
                        className={`font-medium ${
                          wf.is_overdue
                            ? 'text-red-600'
                            : wf.days_remaining <= 2
                            ? 'text-amber-600'
                            : 'text-slate-600'
                        }`}
                      >
                        Due: {formatDate(wf.due_date)}
                      </span>
                    </div>
                  </div>
                ),
              },
              {
                key: 'action',
                header: 'Action',
                width: '12%',
                align: 'right',
                render: (wf) => (
                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleOpenWorkflow(wf);
                      }}
                      className="px-2.5 py-1 bg-[#0B3C9D] hover:bg-[#082B70] text-white rounded text-xs font-semibold transition-colors inline-flex items-center gap-1 shadow-2xs"
                    >
                      <Eye size={12} />
                      <span>Review</span>
                    </button>
                  </div>
                ),
              },
            ];

            return (
              <DataTable
                columns={columns}
                data={workflows}
                keyExtractor={(wf) => wf.id}
                isLoading={isLoading}
                emptyMessage="No applications found matching the selected filter criteria."
                isLong={workflows.length > 12}
                rowClassName={(wf) => (wf.id === highlightedId ? 'bg-amber-100/70 transition-colors duration-700' : '')}
              />
            );
          })()}
        </div>
      </div>

      {/* Case File Action Drawer */}
      <WorkflowDetailDrawer
        workflow={selectedWorkflow}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onUpdated={handleWorkflowUpdated}
        officers={officers}
      />
    </div>
  );
};
