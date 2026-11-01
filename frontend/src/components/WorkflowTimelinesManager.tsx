import React, { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { workflowApi, WorkflowTemplate, WorkflowStage } from '../api/workflow';
import { DataTable, ColumnDef } from './DataTable';

interface WorkflowTimelinesManagerProps {
  readOnly?: boolean;
}

function formatRole(role: string): string {
  switch (role) {
    case 'REGIONAL_OFFICER': return 'Regional officer';
    case 'BUREAU_OFFICER': return 'Bureau officer';
    case 'COMMITTEE_MEMBER': return 'Committee member';
    case 'ADMIN': return 'Admin';
    case 'REVIEWER': return 'Reviewer';
    default: return role.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

export const WorkflowTimelinesManager: React.FC<WorkflowTimelinesManagerProps> = ({ readOnly = false }) => {
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUpdating, setIsUpdating] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [editingStage, setEditingStage] = useState<{
    templateId: number;
    stageId: number;
    sla_days: number;
    responsible_role: string;
  } | null>(null);

  const loadTemplates = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await workflowApi.getTemplates();
      setTemplates(data);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load workflow templates.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTemplates();
  }, []);

  const handleSaveStage = async (templateId: number, stageId: number) => {
    if (!editingStage) return;
    setIsUpdating(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      await workflowApi.updateStageSla(templateId, stageId, {
        sla_days: editingStage.sla_days,
        responsible_role: editingStage.responsible_role,
      });
      setSuccessMsg('Workflow stage SLA and responsible role updated successfully!');
      setEditingStage(null);
      await loadTemplates();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to update stage SLA.');
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-slate-900">
            Workflow stages and SLAs
          </h2>
          <p className="text-xs text-slate-600 mt-0.5">
            Configure the 4 standard regulatory templates, SLA duration days, and designated roles.
          </p>
        </div>
        <button
          onClick={loadTemplates}
          disabled={isLoading}
          className="px-3.5 py-1.5 border border-slate-300 rounded-md text-xs font-medium text-slate-800 bg-white hover:bg-slate-50 flex items-center gap-1.5 shadow-xs transition-colors"
        >
          <RefreshCw size={13} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {successMsg && (
        <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center gap-2 animate-fade-in">
          <CheckCircle2 size={16} className="text-emerald-600" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-800 text-xs font-semibold flex items-center gap-2 animate-fade-in">
          <AlertCircle size={16} className="text-red-600" />
          <span>{errorMsg}</span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        {templates.map((tpl) => {
          const columns: ColumnDef<WorkflowStage>[] = [
            {
              key: 'sequence',
              header: 'Seq',
              width: '8%',
              align: 'left',
              render: (stg) => (
                <span className="font-semibold text-slate-900">{stg.sequence}</span>
              ),
            },
            {
              key: 'stage_name',
              header: 'Stage name',
              width: '32%',
              align: 'left',
              render: (stg) => (
                <div>
                  <span
                    className="font-medium text-slate-900 block line-clamp-2"
                    title={`Stage code: ${stg.stage_code} - ${stg.stage_name}`}
                  >
                    {stg.stage_name}
                  </span>
                  <span className="text-[11px] font-mono text-slate-600 block mt-0.5">
                    {stg.stage_code}
                  </span>
                </div>
              ),
            },
            {
              key: 'responsible_role',
              header: 'Responsible role',
              width: '24%',
              align: 'left',
              render: (stg) => {
                const isEditingThis =
                  editingStage?.templateId === tpl.id && editingStage?.stageId === stg.id;
                return isEditingThis ? (
                  <select
                    value={editingStage.responsible_role}
                    onChange={(e) =>
                      setEditingStage({
                        ...editingStage,
                        responsible_role: e.target.value,
                      })
                    }
                    className="p-1.5 rounded border border-slate-300 text-xs bg-white text-slate-800 font-medium w-full"
                  >
                    <option value="REGIONAL_OFFICER">Regional officer</option>
                    <option value="COMMITTEE_MEMBER">Committee member</option>
                    <option value="BUREAU_OFFICER">Bureau officer</option>
                    <option value="ADMIN">Admin</option>
                    <option value="REVIEWER">Reviewer</option>
                  </select>
                ) : (
                  <span className="text-xs font-medium text-slate-800 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded inline-block">
                    {formatRole(stg.responsible_role)}
                  </span>
                );
              },
            },
            {
              key: 'sla_days',
              header: 'SLA days',
              width: '14%',
              align: 'right',
              render: (stg) => {
                const isEditingThis =
                  editingStage?.templateId === tpl.id && editingStage?.stageId === stg.id;
                return isEditingThis ? (
                  <input
                    type="number"
                    min={1}
                    max={90}
                    value={editingStage.sla_days}
                    onChange={(e) =>
                      setEditingStage({
                        ...editingStage,
                        sla_days: Number(e.target.value),
                      })
                    }
                    className="w-20 p-1.5 rounded border border-slate-300 text-xs font-semibold text-right text-[#0B3C9D] bg-white"
                  />
                ) : (
                  <span className="font-semibold text-slate-900">{stg.sla_days} days</span>
                );
              },
            },
            {
              key: 'stage_type',
              header: 'Stage type',
              width: '10%',
              align: 'left',
              render: (stg) =>
                stg.is_final_decision ? (
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                    Decision stage
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                    Standard stage
                  </span>
                ),
            },
            {
              key: 'action',
              header: 'Action',
              width: '12%',
              align: 'right',
              render: (stg) => {
                const isEditingThis =
                  editingStage?.templateId === tpl.id && editingStage?.stageId === stg.id;
                if (readOnly) {
                  return <span className="text-xs text-slate-600 font-medium">View-only</span>;
                }
                if (isEditingThis) {
                  return (
                    <div className="flex items-center justify-end gap-1.5">
                      <button
                        onClick={() => handleSaveStage(tpl.id, stg.id)}
                        disabled={isUpdating}
                        className="px-2.5 py-1 bg-[#0B3C9D] text-white rounded text-xs font-semibold hover:bg-[#082B70]"
                      >
                        Save
                      </button>
                      <button
                        onClick={() => setEditingStage(null)}
                        className="px-2 py-1 text-slate-600 hover:text-slate-800 text-xs font-medium"
                      >
                        Cancel
                      </button>
                    </div>
                  );
                }
                return (
                  <button
                    onClick={() =>
                      setEditingStage({
                        templateId: tpl.id,
                        stageId: stg.id,
                        sla_days: stg.sla_days,
                        responsible_role: stg.responsible_role,
                      })
                    }
                    className="px-2.5 py-1 border border-slate-300 bg-white text-slate-800 hover:bg-slate-50 hover:border-[#0B3C9D] rounded text-xs font-medium transition-colors"
                  >
                    Edit SLA
                  </button>
                );
              },
            },
          ];

          return (
            <div
              key={tpl.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden"
            >
              <div className="bg-slate-50 p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold text-[#0B3C9D] bg-blue-100/70 px-2 py-0.5 rounded">
                      {tpl.code}
                    </span>
                    <h3 className="font-semibold text-sm text-slate-900">{tpl.name}</h3>
                  </div>
                  <p className="text-xs text-slate-600 mt-1">{tpl.description}</p>
                </div>
                <span className="text-xs font-medium text-slate-700 bg-white border border-slate-200 px-3 py-1 rounded-full">
                  {tpl.stages.length} sequential stages
                </span>
              </div>

              <div className="p-2">
                <DataTable
                  columns={columns}
                  data={tpl.stages}
                  keyExtractor={(stg) => stg.id}
                  isLoading={isLoading}
                  emptyMessage="No stages configured for this workflow template."
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
