import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';

import {

  Search,

  Plus,

  Clock,

  CheckCircle2,

  AlertTriangle,

  FileText,

  RefreshCw,

  Loader2,

} from 'lucide-react';

import {

  undertakingsApi,

  UndertakingItem,

  UndertakingTemplate,

} from '../../api/stage3';

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



export const AdminUndertakingsPage: React.FC = () => {

  const [undertakings, setUndertakings] = useState<UndertakingItem[]>([]);

  const [templates, setTemplates] = useState<UndertakingTemplate[]>([]);

  const [isLoading, setIsLoading] = useState(true);

  const [search, setSearch] = useState('');

  const [statusFilter, setStatusFilter] = useState('ALL');

  const [categoryFilter, setCategoryFilter] = useState('ALL');



  // Create Modal State

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  const [appIdInput, setAppIdInput] = useState('1');

  const [selectedTemplate, setSelectedTemplate] = useState('');

  const [categoryInput, setCategoryInput] = useState('lease');

  const [conditionInput, setConditionInput] = useState('');

  const [dueDateInput, setDueDateInput] = useState('');

  const [isSubmittingCreate, setIsSubmittingCreate] = useState(false);



  // Verify Modal State

  const [selectedUndertaking, setSelectedUndertaking] = useState<UndertakingItem | null>(null);

  const [isVerifyModalOpen, setIsVerifyModalOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const [highlightedId, setHighlightedId] = useState<number | null>(null);
  const [unavailableNotice, setUnavailableNotice] = useState<string | null>(null);
  const handledParamRef = useRef<string | null>(null);

  const [verifyAction, setVerifyAction] = useState<'ACCEPT' | 'REQUEST_MORE' | 'REJECT'>('ACCEPT');

  const [verifyReason, setVerifyReason] = useState('');

  const [isSubmittingVerify, setIsSubmittingVerify] = useState(false);



  const loadData = async () => {

    setIsLoading(true);

    try {

      const [listData, tmpls] = await Promise.all([

        undertakingsApi.list({

          status: statusFilter !== 'ALL' ? statusFilter : undefined,

          category: categoryFilter !== 'ALL' ? categoryFilter : undefined,

        }),

        undertakingsApi.getTemplates(),

      ]);

      setUndertakings(listData);

      setTemplates(tmpls);

    } catch (err) {

      console.error('Failed to load undertakings:', err);

    } finally {

      setIsLoading(false);

    }

  };



  useEffect(() => {

    loadData();

  }, [statusFilter, categoryFilter]);

  // Handle open query param once on load
  useEffect(() => {
    const targetCode = searchParams.get('open') || searchParams.get('application');
    if (!targetCode || isLoading) return;
    if (handledParamRef.current === targetCode) return;
    handledParamRef.current = targetCode;

    if (statusFilter !== 'ALL') setStatusFilter('ALL');
    if (categoryFilter !== 'ALL') setCategoryFilter('ALL');
    if (search) setSearch('');

    const targetLower = targetCode.toLowerCase();
    const match = undertakings.find(
      (item) =>
        String(item.id) === targetCode ||
        String(item.application_id) === targetCode ||
        (item.application_code && item.application_code.toLowerCase() === targetLower)
    );

    if (match) {
      setHighlightedId(match.id);
      setSelectedUndertaking(match);
      setIsVerifyModalOpen(true);
      setTimeout(() => {
        const el = document.getElementById(`undertaking-row-${match.id}`);
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
  }, [searchParams, undertakings, isLoading, statusFilter, categoryFilter, search]);



  const handleTemplateSelect = (title: string) => {

    setSelectedTemplate(title);

    const tmpl = templates.find((t) => t.title === title);

    if (tmpl) {

      setCategoryInput(tmpl.category);

      setConditionInput(tmpl.condition);

      const due = new Date();

      due.setDate(due.getDate() + tmpl.default_sla_days);

      setDueDateInput(due.toISOString().slice(0, 10));

    }

  };



  const handleCreateSubmit = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!conditionInput.trim() || !dueDateInput) {

      alert('Condition and due date are required.');

      return;

    }



    setIsSubmittingCreate(true);

    try {

      await undertakingsApi.create({

        application_id: parseInt(appIdInput) || 1,

        condition: conditionInput.trim(),

        category: categoryInput,

        due_date: new Date(dueDateInput).toISOString(),

      });

      setIsCreateModalOpen(false);

      loadData();

    } catch (err: any) {

      alert(err.response?.data?.detail || 'Failed to create undertaking');

    } finally {

      setIsSubmittingCreate(false);

    }

  };



  const handleVerifySubmit = async (e: React.FormEvent) => {

    e.preventDefault();

    if (!selectedUndertaking) return;

    if (!verifyReason.trim()) {

      alert('Reason is required for verification.');

      return;

    }



    setIsSubmittingVerify(true);

    try {

      await undertakingsApi.verify(selectedUndertaking.id, {

        action: verifyAction,

        reason: verifyReason.trim(),

      });

      setIsVerifyModalOpen(false);

      loadData();

    } catch (err: any) {

      alert(err.response?.data?.detail || 'Failed to verify undertaking');

    } finally {

      setIsSubmittingVerify(false);

    }

  };



  const filtered = undertakings.filter((item) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      (item.application_code || '').toLowerCase().includes(s) ||
      (item.institute_name || '').toLowerCase().includes(s) ||
      (item.condition || '').toLowerCase().includes(s) ||
      (item.category || '').toLowerCase().includes(s)
    );
  });

  const columns: ColumnDef<UndertakingItem>[] = [

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

      header: 'Institution & category',

      width: '25%',

      align: 'left',

      render: (item) => (

        <div>

          <div className="font-semibold text-slate-900 truncate" title={item.institute_name}>

            {item.institute_name}

          </div>

          <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-[11px] text-slate-700 font-medium">

            {item.category}

          </span>

        </div>

      ),

    },

    {

      key: 'condition',

      header: 'Condition',

      width: '26%',

      align: 'left',

      render: (item) => (

        <p className="line-clamp-2 text-slate-800 text-xs leading-relaxed" title={item.condition}>

          {item.condition}

        </p>

      ),

    },

    {

      key: 'due_date',

      header: 'Due date & evidence',

      width: '18%',

      align: 'left',

      render: (item) => (

        <div className="space-y-0.5">

          <div className="flex items-center gap-1 text-slate-700 text-xs">

            <Clock size={11} className={item.status === 'OVERDUE' ? 'text-red-500 shrink-0' : 'text-slate-500 shrink-0'} />

            <span className={item.status === 'OVERDUE' ? 'text-red-600 font-semibold' : ''}>

              Due: {formatDate(item.due_date)}

            </span>

          </div>

          <div className="text-xs">

            {item.evidence_original_filename ? (

              <div className="flex items-center gap-1 text-emerald-700 font-medium truncate max-w-[170px]" title={item.evidence_original_filename}>

                <FileText size={11} className="shrink-0" />

                <span className="truncate">{item.evidence_original_filename}</span>

              </div>

            ) : (

              <span className="text-slate-600 italic text-[11px]">No evidence uploaded</span>

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

          <ActionMenu

            primaryAction={{

              label: 'Review',

              onClick: () => {

                setSelectedUndertaking(item);

                setVerifyReason('');

                setVerifyAction('ACCEPT');

                setIsVerifyModalOpen(true);

              },

            }}

          />

        </div>

      ),

    },

  ];



  return (

    <div className="space-y-6 pb-12">

      {unavailableNotice && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold rounded-lg flex items-center justify-between">
          <span>{unavailableNotice}</span>
          <button onClick={() => setUnavailableNotice(null)} className="text-amber-700 hover:text-amber-900 font-bold ml-2">×</button>
        </div>
      )}
      {/* Page Header Card */}

      <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">

        <div>

          <h1 className="text-2xl font-bold tracking-tight text-slate-900">

            Undertakings

          </h1>

          <p className="text-xs text-slate-600 mt-0.5">

            Conditions, affidavit tracking, and verification decisions.

          </p>

        </div>



        <div className="flex items-center gap-2.5">

          <button

            onClick={() => {

              setConditionInput('');

              setDueDateInput('');

              setSelectedTemplate('');

              setIsCreateModalOpen(true);

            }}

            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-[#F58220] hover:bg-[#D96B0E] text-white text-xs font-medium rounded-md shadow-sm transition-colors"

          >

            <Plus size={14} />

            <span>Add undertaking</span>

          </button>

          <button

            onClick={loadData}

            disabled={isLoading}

            className="flex items-center gap-2 px-3.5 py-1.5 bg-white border border-slate-300 hover:border-slate-400 text-slate-800 text-xs font-medium rounded-md shadow-sm transition-colors"

          >

            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />

            Refresh

          </button>

        </div>

      </div>



      {/* Main Table Card */}

      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">

        {/* Filters */}

        <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50">

          <div className="flex flex-wrap items-center gap-2">

            <span className="text-xs font-medium text-slate-500">Status:</span>

            {[

              { id: 'ALL', label: 'All' },

              { id: 'ACTIVE', label: 'Active' },

              { id: 'SUBMITTED', label: 'Submitted' },

              { id: 'FULFILLED', label: 'Fulfilled' },

              { id: 'OVERDUE', label: 'Overdue' },

              { id: 'ESCALATED', label: 'Escalated' },

            ].map((st) => (

              <button

                key={st.id}

                onClick={() => setStatusFilter(st.id)}

                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${

                  statusFilter === st.id

                    ? 'bg-[#0B3C9D] text-white'

                    : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'

                }`}

              >

                {st.label}

              </button>

            ))}

          </div>



          <div className="flex items-center gap-2">

            <select

              value={categoryFilter}

              onChange={(e) => setCategoryFilter(e.target.value)}

              className="px-2.5 py-1.5 border border-slate-300 rounded-md text-xs bg-white text-slate-700 focus:outline-none focus:border-[#0B3C9D]"

            >

              <option value="ALL">All categories</option>

              <option value="lease">Lease deeds</option>

              <option value="accreditation">Accreditation (NBA/NAAC)</option>

              <option value="infrastructure">Infrastructure norms</option>

              <option value="faculty">Faculty cadre ratio</option>

              <option value="other">Other</option>

            </select>



            <div className="relative w-56">

              <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />

              <input

                type="text"

                placeholder="Search undertaking..."

                value={search}

                onChange={(e) => setSearch(e.target.value)}

                className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"

              />

            </div>

          </div>

        </div>



        {/* DataTable */}

        <DataTable

          columns={columns}

          data={filtered}

          keyExtractor={(item) => item.id}

          isLoading={isLoading}

          emptyMessage="No undertakings match these filters"

          rowClassName={(item) => (item.id === highlightedId ? 'bg-amber-100/70 transition-colors duration-700' : '')}

          onClearFilters={statusFilter !== 'ALL' || categoryFilter !== 'ALL' || search ? () => {

            setStatusFilter('ALL');

            setCategoryFilter('ALL');

            setSearch('');

          } : undefined}

        />

      </div>



      {/* Create Undertaking Modal */}

      <Modal

        isOpen={isCreateModalOpen}

        onClose={() => setIsCreateModalOpen(false)}

        title="Add undertaking"

      >

        <form onSubmit={handleCreateSubmit} className="space-y-4">

          <div>

            <label className="block text-xs font-medium text-slate-700 mb-1">

              Select condition template (Optional)

            </label>

            <select

              value={selectedTemplate}

              onChange={(e) => handleTemplateSelect(e.target.value)}

              className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs bg-white focus:outline-none focus:border-[#0B3C9D]"

            >

              <option value="">-- Choose condition template --</option>

              {templates.map((t) => (

                <option key={t.title} value={t.title}>

                  [{t.category}] {t.title} ({t.default_sla_days} days SLA)

                </option>

              ))}

            </select>

          </div>



          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            <div>

              <label className="block text-xs font-medium text-slate-700 mb-1">

                Target application ID <span className="text-red-500">*</span>

              </label>

              <input

                type="number"

                required

                value={appIdInput}

                onChange={(e) => setAppIdInput(e.target.value)}

                className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"

              />

            </div>

            <div>

              <label className="block text-xs font-medium text-slate-700 mb-1">

                Category <span className="text-red-500">*</span>

              </label>

              <select

                value={categoryInput}

                onChange={(e) => setCategoryInput(e.target.value)}

                className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs bg-white focus:outline-none focus:border-[#0B3C9D]"

              >

                <option value="lease">Lease agreement</option>

                <option value="accreditation">Accreditation</option>

                <option value="infrastructure">Infrastructure</option>

                <option value="faculty">Faculty ratio</option>

                <option value="other">Other</option>

              </select>

            </div>

          </div>



          <div>

            <label className="block text-xs font-medium text-slate-700 mb-1">

              Condition details <span className="text-red-500">*</span>

            </label>

            <textarea

              required

              rows={4}

              value={conditionInput}

              onChange={(e) => setConditionInput(e.target.value)}

              placeholder="Enter exact terms of the required compliance milestone..."

              className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"

            />

          </div>



          <div>

            <label className="block text-xs font-medium text-slate-700 mb-1">

              Due date <span className="text-red-500">*</span>

            </label>

            <input

              type="date"

              required

              value={dueDateInput}

              onChange={(e) => setDueDateInput(e.target.value)}

              className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"

            />

          </div>



          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">

            <button

              type="button"

              onClick={() => setIsCreateModalOpen(false)}

              className="px-3.5 py-1.5 border border-slate-300 text-slate-700 rounded-md text-xs font-medium hover:bg-slate-50"

            >

              Cancel

            </button>

            <button

              type="submit"

              disabled={isSubmittingCreate}

              className="px-4 py-1.5 bg-[#F58220] hover:bg-[#D96B0E] text-white rounded-md text-xs font-medium flex items-center gap-2"

            >

              {isSubmittingCreate && <Loader2 size={14} className="animate-spin" />}

              <span>Issue undertaking</span>

            </button>

          </div>

        </form>

      </Modal>



      {/* Verify / Review Undertaking Modal */}

      <Modal

        isOpen={isVerifyModalOpen}

        onClose={() => setIsVerifyModalOpen(false)}

        title={`Review undertaking - ${selectedUndertaking?.application_code || ''}`}

      >

        <form onSubmit={handleVerifySubmit} className="space-y-4">

          <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs space-y-2">

            <div>

              <span className="font-medium text-slate-500">Institution:</span>{' '}

              <span className="font-medium text-slate-900">{selectedUndertaking?.institute_name}</span>

            </div>

            <div>

              <span className="font-medium text-slate-500">Condition:</span>

              <p className="mt-0.5 text-slate-800">{selectedUndertaking?.condition}</p>

            </div>

            <div className="flex items-center gap-4 pt-1 border-t border-slate-200/60">

              <div>

                <span className="font-medium text-slate-500">Due date:</span>{' '}

                <span>{formatDate(selectedUndertaking?.due_date)}</span>

              </div>

              <div>

                <span className="font-medium text-slate-500">Status:</span>{' '}

                <StatusPill status={selectedUndertaking?.status || 'ACTIVE'} />

              </div>

            </div>

          </div>



          {/* Evidence Details */}

          {selectedUndertaking?.evidence_original_filename ? (

            <div className="p-3 bg-emerald-50/60 border border-emerald-200 rounded-lg text-xs space-y-1">

              <span className="font-medium text-emerald-900 flex items-center gap-1.5">

                <CheckCircle2 size={14} />

                <span>Submitted proof of compliance</span>

              </span>

              <p className="font-mono text-emerald-800 font-medium">{selectedUndertaking.evidence_original_filename}</p>

              {selectedUndertaking.evidence_remarks && (

                <p className="text-slate-600 pt-1">Remarks: {selectedUndertaking.evidence_remarks}</p>

              )}

            </div>

          ) : (

            <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-800 text-xs">

              <p className="font-medium flex items-center gap-1.5">

                <AlertTriangle size={14} />

                <span>No evidence uploaded yet</span>

              </p>

              <p className="mt-0.5">The institution has not yet uploaded proof.</p>

            </div>

          )}



          <div>

            <label className="block text-xs font-medium text-slate-700 mb-1">

              Action <span className="text-red-500">*</span>

            </label>

            <div className="grid grid-cols-3 gap-2">

              <button

                type="button"

                onClick={() => setVerifyAction('ACCEPT')}

                className={`py-2 px-3 rounded-md text-xs font-medium border transition-colors ${

                  verifyAction === 'ACCEPT'

                    ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'

                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'

                }`}

              >

                Accept

              </button>

              <button

                type="button"

                onClick={() => setVerifyAction('REQUEST_MORE')}

                className={`py-2 px-3 rounded-md text-xs font-medium border transition-colors ${

                  verifyAction === 'REQUEST_MORE'

                    ? 'bg-amber-600 text-white border-amber-600 shadow-xs'

                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'

                }`}

              >

                Request more

              </button>

              <button

                type="button"

                onClick={() => setVerifyAction('REJECT')}

                className={`py-2 px-3 rounded-md text-xs font-medium border transition-colors ${

                  verifyAction === 'REJECT'

                    ? 'bg-red-600 text-white border-red-600 shadow-xs'

                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'

                }`}

              >

                Reject & escalate

              </button>

            </div>

          </div>



          <div>

            <label className="block text-xs font-medium text-slate-700 mb-1">

              Reason <span className="text-red-500">*</span>

            </label>

            <textarea

              required

              rows={3}

              value={verifyReason}

              onChange={(e) => setVerifyReason(e.target.value)}

              placeholder="State the basis for this decision..."

              className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"

            />

          </div>



          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">

            <button

              type="button"

              onClick={() => setIsVerifyModalOpen(false)}

              className="px-3.5 py-1.5 border border-slate-300 text-slate-700 rounded-md text-xs font-medium hover:bg-slate-50"

            >

              Cancel

            </button>

            <button

              type="submit"

              disabled={isSubmittingVerify}

              className="px-4 py-1.5 bg-[#0B3C9D] text-white rounded-md text-xs font-medium hover:bg-[#082B70] flex items-center gap-2"

            >

              {isSubmittingVerify && <Loader2 size={14} className="animate-spin" />}

              <span>Save decision</span>

            </button>

          </div>

        </form>

      </Modal>

    </div>

  );

};

