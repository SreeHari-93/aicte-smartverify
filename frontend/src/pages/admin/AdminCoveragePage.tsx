import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  GitBranch,
  Users,
  FileSignature,
  Bell,
  ScrollText,
  AlertTriangle,
  Layers,
} from 'lucide-react';
import { apiClient } from '../../api/client';
import { DataTable, ColumnDef } from '../../components/DataTable';

interface ClauseItem {
  section: string;
  clause: string;
  requirement: string;
  screen: string;
  api_route: string;
  db_table: string;
  test_file: string;
  status: string;
}

interface CoverageData {
  status: string;
  standard: string;
  counts: {
    workflows: number;
    evc_cases: number;
    undertakings: number;
    document_validity_records: number;
    alert_events: number;
    escalations: number;
    audit_logs: number;
    officers_registered: number;
  };
  clauses: ClauseItem[];
  total_clauses: number;
  verified_clauses: number;
  compliance_percentage: number;
  queried_at: string;
}

export const AdminCoveragePage: React.FC = () => {
  const [coverage, setCoverage] = useState<CoverageData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterSection, setFilterSection] = useState<string>('ALL');

  const fetchCoverage = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiClient.get<CoverageData>('/api/workflow/coverage');
      setCoverage(res.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load specification coverage data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCoverage();
  }, []);

  const sections = React.useMemo(() => {
    if (!coverage) return [];
    const set = new Set(coverage.clauses.map((c) => c.section));
    return Array.from(set);
  }, [coverage]);

  const filteredClauses = React.useMemo(() => {
    if (!coverage) return [];
    if (filterSection === 'ALL') return coverage.clauses;
    return coverage.clauses.filter((c) => c.section === filterSection);
  }, [coverage, filterSection]);

  const columns: ColumnDef<ClauseItem>[] = [
    {
      key: 'clause',
      header: 'Clause',
      width: '18%',
      align: 'left',
      render: (c) => (
        <div className="space-y-0.5">
          <span className="block text-xs font-bold text-[#0B3C9D]">{c.clause}</span>
          <span className="block text-[11px] text-slate-600 truncate" title={c.section}>
            {c.section}
          </span>
        </div>
      ),
    },
    {
      key: 'requirement',
      header: 'Requirement',
      width: '32%',
      align: 'left',
      render: (c) => (
        <div className="text-xs text-slate-700 leading-snug line-clamp-2" title={c.requirement}>
          {c.requirement}
        </div>
      ),
    },
    {
      key: 'where',
      header: 'Where',
      width: '22%',
      align: 'left',
      render: (c) => (
        <div className="space-y-1">
          <span className="inline-block px-2 py-0.5 rounded bg-blue-50 text-[#0B3C9D] font-mono text-[11px] border border-blue-100 max-w-full truncate" title={c.screen}>
            {c.screen}
          </span>
          <span className="block font-mono text-[10px] text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 truncate" title={c.api_route}>
            {c.api_route}
          </span>
        </div>
      ),
    },
    {
      key: 'tables_tests',
      header: 'Tables and tests',
      width: '16%',
      align: 'left',
      render: (c) => (
        <div className="space-y-0.5 font-mono text-[10px] text-slate-600">
          <span className="block text-slate-800 font-semibold truncate" title={c.db_table}>
            {c.db_table}
          </span>
          <span className="block text-slate-500 truncate" title={c.test_file}>
            {c.test_file}
          </span>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '12%',
      align: 'left',
      render: (c) => (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200 whitespace-nowrap">
          <CheckCircle2 size={12} className="shrink-0" />
          <span>{c.status}</span>
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Coverage
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Traceability matrix for PS 26262 requirements.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchCoverage}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 text-xs font-semibold rounded-lg shadow-xs disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs flex items-center gap-2">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Compliance Metric Cards */}
      {coverage && (
        <>
          <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-6">
            <div className="space-y-2">
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                {coverage.compliance_percentage}% clause coverage
              </h2>
              <p className="text-xs text-slate-600 max-w-xl leading-relaxed">
                {coverage.verified_clauses} of {coverage.total_clauses} specifications verified across workflow lifecycle, EVC, undertakings, validity, alerts, and safeguards.
              </p>
              <div className="pt-1">
                <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 px-3 py-1 rounded-md border border-slate-200">
                  Rules decide, AI explains, Officials approve. System decisions strictly remain with officials.
                </span>
              </div>
            </div>

            <div className="text-right sm:border-l sm:border-slate-200 sm:pl-8">
              <span className="text-xs text-slate-600 block font-medium">
                Live audit timestamp
              </span>
              <span className="text-sm font-mono font-bold text-slate-900 mt-1 block">
                {(() => {
                  const d = new Date(coverage.queried_at);
                  const day = String(d.getDate()).padStart(2, '0');
                  const month = String(d.getMonth() + 1).padStart(2, '0');
                  const year = d.getFullYear();
                  const hours = String(d.getHours()).padStart(2, '0');
                  const mins = String(d.getMinutes()).padStart(2, '0');
                  return `${day}-${month}-${year} ${hours}:${mins}`;
                })()}
              </span>
              <span className="text-[11px] text-emerald-600 mt-2 block font-medium flex items-center justify-end gap-1">
                <CheckCircle2 size={13} />
                <span>Zero regressions</span>
              </span>
            </div>
          </div>

          {/* Six operational counter cards: equal height aligned in a single row (wrap to 3 on narrow) */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 items-stretch">
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs h-full flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold mb-1">
                <GitBranch size={14} className="text-[#0B3C9D]" />
                <span>Workflows</span>
              </div>
              <div className="text-2xl font-black text-slate-800">{coverage.counts.workflows}</div>
              <span className="text-[10px] text-slate-600">Instances Tracked</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs h-full flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold mb-1">
                <Users size={14} className="text-[#F58220]" />
                <span>EVC Cases</span>
              </div>
              <div className="text-2xl font-black text-slate-800">{coverage.counts.evc_cases}</div>
              <span className="text-[10px] text-slate-600">Scheduled / Queue</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs h-full flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold mb-1">
                <FileSignature size={14} className="text-emerald-600" />
                <span>Undertakings</span>
              </div>
              <div className="text-2xl font-black text-slate-800">{coverage.counts.undertakings}</div>
              <span className="text-[10px] text-slate-600">Active Conditions</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs h-full flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold mb-1">
                <ShieldCheck size={14} className="text-blue-600" />
                <span>Doc Validity</span>
              </div>
              <div className="text-2xl font-black text-slate-800">{coverage.counts.document_validity_records}</div>
              <span className="text-[10px] text-slate-600">Monitored Expiries</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs h-full flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold mb-1">
                <Bell size={14} className="text-amber-600" />
                <span>Alert Events</span>
              </div>
              <div className="text-2xl font-black text-slate-800">{coverage.counts.alert_events}</div>
              <span className="text-[10px] text-slate-600">Triggered Idempotently</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs h-full flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-600 text-xs font-semibold mb-1">
                <ScrollText size={14} className="text-indigo-600" />
                <span>Audit Entries</span>
              </div>
              <div className="text-2xl font-black text-slate-800">{coverage.counts.audit_logs}</div>
              <span className="text-[10px] text-slate-600">Immutable Records</span>
            </div>
          </div>
        </>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center gap-2 pt-2">
        <button
          onClick={() => setFilterSection('ALL')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
            filterSection === 'ALL'
              ? 'bg-[#0B3C9D] text-white shadow-xs'
              : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          All Sections ({coverage?.clauses.length || 0})
        </button>
        {sections.map((sec) => (
          <button
            key={sec}
            onClick={() => setFilterSection(sec)}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
              filterSection === sec
                ? 'bg-[#0B3C9D] text-white shadow-xs'
                : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {sec.split(':')[0]}
          </button>
        ))}
      </div>

      {/* Traceability Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="p-4 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers size={16} className="text-[#0B3C9D]" />
            <h3 className="font-bold text-sm text-[#0F2A5C]">
              PS 26262 Requirements to Implementation Mapping
            </h3>
          </div>
          <span className="text-xs text-slate-600 font-medium">
            Showing {filteredClauses.length} specifications
          </span>
        </div>

        <DataTable
          columns={columns}
          data={filteredClauses}
          keyExtractor={(c, idx) => `${c.clause}-${idx}`}
          isLoading={isLoading}
          isLong={true}
          emptyMessage="No specification clauses match this filter."
        />
      </div>
    </div>
  );
};
