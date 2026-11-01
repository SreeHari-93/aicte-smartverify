import React, { useState, useEffect } from 'react';

import {

  Search,

  ChevronRight,

  RefreshCw,

} from 'lucide-react';

import {

  workflowApi,

  ApplicationWorkflow,

  WorkflowOfficer,

} from '../../api/workflow';

import { StatusPill } from '../../components/StatusPill';

import { DataTable, ColumnDef } from '../../components/DataTable';

import { WorkflowDetailDrawer } from '../../components/WorkflowDetailDrawer';



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



export const AdminApplicationsPage: React.FC = () => {

  const [workflows, setWorkflows] = useState<ApplicationWorkflow[]>([]);

  const [officers, setOfficers] = useState<WorkflowOfficer[]>([]);

  const [isLoading, setIsLoading] = useState(true);

  const [selectedWorkflow, setSelectedWorkflow] = useState<ApplicationWorkflow | null>(null);

  const [isDrawerOpen, setIsDrawerOpen] = useState(false);



  // Filters

  const [searchQuery, setSearchQuery] = useState('');

  const [regionFilter, setRegionFilter] = useState('ALL');

  const [stageFilter, setStageFilter] = useState('ALL');

  const [officerFilter, setOfficerFilter] = useState('ALL');

  const [statusFilter, setStatusFilter] = useState('ALL');



  const fetchApps = async () => {

    setIsLoading(true);

    try {

      const [apps, offs] = await Promise.all([

        workflowApi.getApplications({

          region: regionFilter !== 'ALL' ? regionFilter : undefined,

          stage: stageFilter !== 'ALL' ? stageFilter : undefined,

          officer_id: officerFilter !== 'ALL' ? Number(officerFilter) : undefined,

          status_filter: statusFilter !== 'ALL' ? statusFilter : undefined,

          search: searchQuery || undefined,

        }),

        workflowApi.getOfficers(),

      ]);

      setWorkflows(apps);

      setOfficers(offs);

    } catch (err) {

      console.error(err);

    } finally {

      setIsLoading(false);

    }

  };



  useEffect(() => {

    fetchApps();

  }, [regionFilter, stageFilter, officerFilter, statusFilter]);



  const handleOpenWorkflow = (wf: ApplicationWorkflow) => {

    setSelectedWorkflow(wf);

    setIsDrawerOpen(true);

  };



  const handleWorkflowUpdated = (updated: ApplicationWorkflow) => {

    setSelectedWorkflow(updated);

    setWorkflows((prev) => prev.map((w) => (w.id === updated.id ? updated : w)));

  };



  const columns: ColumnDef<ApplicationWorkflow>[] = [

    {

      key: 'code',

      header: 'Application ID',

      width: '15%',

      align: 'left',

      render: (wf) => (

        <span className="font-mono font-bold text-[#0B3C9D] text-xs">

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

          <div className="font-semibold text-slate-900 truncate" title={wf.institute_name}>

            {wf.institute_name}

          </div>

          <div className="text-[11px] text-slate-600 mt-0.5">

            {wf.region || 'AICTE Region'}

          </div>

        </div>

      ),

    },

    {

      key: 'category',

      header: 'Category',

      width: '18%',

      align: 'left',

      render: (wf) => (

        <span className="text-slate-800 line-clamp-1 text-xs" title={wf.category}>

          {wf.category}

        </span>

      ),

    },

    {

      key: 'stage',

      header: 'Stage & officer',

      width: '18%',

      align: 'left',

      render: (wf) => (

        <div>

          <div className="font-semibold text-slate-800 text-xs">

            {wf.current_stage_name}

          </div>

          <div className="text-[11px] text-slate-600 truncate mt-0.5" title={wf.assigned_officer_name || 'Unassigned'}>

            {wf.assigned_officer_name || 'Unassigned'}

          </div>

        </div>

      ),

    },

    {

      key: 'status',

      header: 'Status & due date',

      width: '13%',

      align: 'left',

      render: (wf) => (

        <div className="space-y-1">

          <StatusPill status={wf.status} />

          <div className="text-[11px]">

            <span

              className={

                wf.is_overdue

                  ? 'text-red-600 font-semibold'

                  : wf.days_remaining <= 2

                  ? 'text-amber-600 font-semibold'

                  : 'text-slate-600'

              }

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

      width: '10%',

      align: 'right',

      render: (wf) => (

        <div className="flex justify-end">

          <button

            type="button"

            onClick={(e) => {

              e.stopPropagation();

              handleOpenWorkflow(wf);

            }}

            className="px-3 py-1.5 bg-[#0B3C9D] hover:bg-[#082B70] text-white rounded-md text-xs font-semibold inline-flex items-center gap-1 transition-colors shadow-2xs"

          >

            Open

            <ChevronRight size={12} />

          </button>

        </div>

      ),

    },

  ];



  return (

    <div className="space-y-6 pb-12">

      {/* Header Card */}

      <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">

        <div>

          <h1 className="text-2xl font-bold tracking-tight text-slate-900">

            Applications

          </h1>

          <p className="text-xs text-slate-600 mt-0.5">

            Review institution applications and stage status.

          </p>

        </div>



        <button

          onClick={fetchApps}

          disabled={isLoading}

          className="flex items-center gap-2 px-3.5 py-1.5 bg-white border border-slate-300 hover:border-slate-400 text-slate-800 text-xs font-medium rounded-md shadow-sm transition-colors cursor-pointer"

        >

          <RefreshCw size={14} className={isLoading ? 'animate-spin text-[#0B3C9D]' : ''} />

          Refresh

        </button>

      </div>



      {/* Filters and Search */}

      <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm space-y-4">

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 text-xs">

          <div className="lg:col-span-1">

            <label className="block text-slate-600 font-medium mb-1 text-xs">

              Search

            </label>

            <div className="relative">

              <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />

              <input

                type="text"

                placeholder="Search ID, officer..."

                value={searchQuery}

                onChange={(e) => setSearchQuery(e.target.value)}

                onKeyDown={(e) => e.key === 'Enter' && fetchApps()}

                className="pl-8 pr-3 py-1.5 text-xs rounded-md border border-slate-300 w-full outline-none focus:border-[#0B3C9D]"

              />

            </div>

          </div>



          <div>

            <label className="block text-slate-600 font-medium mb-1 text-xs">

              Region

            </label>

            <select

              value={regionFilter}

              onChange={(e) => setRegionFilter(e.target.value)}

              className="w-full p-2 rounded-md border border-slate-300 bg-white text-xs"

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

              className="w-full p-2 rounded-md border border-slate-300 bg-white text-xs"

            >

              <option value="ALL">All stages</option>

              <option value="Scrutiny">Scrutiny</option>

              <option value="EVC">EVC</option>

              <option value="SHC">SHC</option>

              <option value="SAC">SAC</option>

              <option value="Final Decision">Final Decision</option>

            </select>

          </div>



          <div>

            <label className="block text-slate-600 font-medium mb-1 text-xs">

              Officer

            </label>

            <select

              value={officerFilter}

              onChange={(e) => setOfficerFilter(e.target.value)}

              className="w-full p-2 rounded-md border border-slate-300 bg-white text-xs"

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

              className="w-full p-2 rounded-md border border-slate-300 bg-white text-xs"

            >

              <option value="ALL">All statuses</option>

              <option value="IN_PROGRESS">In progress</option>

              <option value="RETURNED">Returned</option>

              <option value="ON_HOLD">On hold</option>

              <option value="COMPLETED">Completed</option>

            </select>

          </div>

        </div>



        {/* DataTable */}

        <DataTable

          columns={columns}

          data={workflows}

          keyExtractor={(wf) => wf.id}

          isLoading={isLoading}

          emptyMessage="No applications match the search."

          onClearFilters={searchQuery ? () => setSearchQuery('') : undefined}

          rowClassName={() => 'cursor-pointer'}

        />

      </div>



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

