import React, { useState, useEffect, useRef } from 'react';
import {
  Download,
  Loader2,
  MapPin,
  Calendar,
  FileSpreadsheet,
  Search,
  ChevronDown,
  Lock,
  X,
  Check,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { alertsApi } from '../../api/alerts';

const CONSOLIDATED_REPORTS = [
  {
    id: 'application_pendency',
    name: 'Application Pendency & Stage Ageing',
    category: 'Workflow & SLA',
    description: 'Overview of all pending applications, assigned officers, SLA duration, and current stages.',
  },
  {
    id: 'evc_status',
    name: 'EVC Physical Inspection Status',
    category: 'Expert Committee',
    description: 'Physical inspection schedule, committee constitution, visit confirmation, and committee report submission tracking.',
  },
  {
    id: 'undertaking_compliance',
    name: 'Undertakings Compliance & Fulfilment Register',
    category: 'Compliance Register',
    description: 'Active undertakings, category breakdown, evidence verification status, and fulfillment audit trail.',
  },
  {
    id: 'document_validity',
    name: 'Monitored Document Validity & Lease Register',
    category: 'Document Register',
    description: 'Register of mandatory certificates, lessor/lessee property metadata, validity dates, and renewal submissions.',
  },
  {
    id: 'overdue_cases',
    name: 'Overdue Cases & Escalations',
    category: 'Supervisory Escalations',
    description: 'Consolidated breach log across stages, undertakings, and validity with Level 1-3 escalation history.',
  },
  {
    id: 'region_processing_performance',
    name: 'Region-Wise Processing Performance & Throughput',
    category: 'Supervisory',
    description: 'Throughput comparison across Southern, Northern, and Western regional offices with compliance rates.',
  },
];

interface ReportApp {
  id: number;
  application_id: string;
  institute_id: number;
  institute_name: string;
  stage: string;
  region: string;
  category: string;
  status: string;
  label: string;
}

function canonicalizeUserRegion(raw?: string | null): string {
  if (!raw) return 'Southern';
  const s = raw.toLowerCase().trim();
  if (s.includes('south-west') || s.includes('south west') || s === 'swro') return 'South-Western';
  if (s.includes('south') || s === 'sr' || s === 'sro') return 'Southern';
  if (s.includes('north') || s === 'nr' || s === 'nro') return 'Northern';
  if (s.includes('west') || s === 'wr' || s === 'wro') return 'Western';
  if (s.includes('east') || s === 'er' || s === 'ero') return 'Eastern';
  if (s.includes('central') || s === 'cro') return 'Central';
  return 'Southern';
}

export const AdminReportsPage: React.FC = () => {
  const { user } = useAuth();
  const isRegionalOfficer = user?.role === 'REGIONAL_OFFICER';
  const officerCanonicalRegion = isRegionalOfficer ? canonicalizeUserRegion(user?.region) : null;

  const [selectedRegion, setSelectedRegion] = useState<string>(
    officerCanonicalRegion || 'ALL'
  );
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [downloadingReport, setDownloadingReport] = useState<string | null>(null);

  // Applications dropdown state
  const [applications, setApplications] = useState<ReportApp[]>([]);
  const [isLoadingApps, setIsLoadingApps] = useState<boolean>(true);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isDropdownOpen, setIsDropdownOpen] = useState<boolean>(false);
  const [appSelectError, setAppSelectError] = useState<string | null>(null);

  // Summary generation state
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState<string | null>(null);
  const [inlineError, setInlineError] = useState<string | null>(null);

  const dropdownRef = useRef<HTMLDivElement>(null);

  // Set default locked region if regional officer
  useEffect(() => {
    if (officerCanonicalRegion) {
      setSelectedRegion(officerCanonicalRegion);
    }
  }, [officerCanonicalRegion]);

  // Fetch applications when region changes
  const fetchApplications = async (regionFilter: string) => {
    setIsLoadingApps(true);
    try {
      const targetRegion = (isRegionalOfficer && officerCanonicalRegion)
        ? officerCanonicalRegion
        : (regionFilter !== 'ALL' ? regionFilter : undefined);
      const apps = await alertsApi.getReportApplications(targetRegion);
      setApplications(apps || []);

      // If previously selected application is not in new list, reset it
      if (selectedAppId && apps && !apps.some((a) => a.application_id === selectedAppId)) {
        setSelectedAppId('');
        setSearchQuery('');
      }
    } catch (err: any) {
      console.error('Failed to load applications for report dropdown:', err);
      setApplications([]);
    } finally {
      setIsLoadingApps(false);
    }
  };

  useEffect(() => {
    fetchApplications(selectedRegion);
  }, [selectedRegion]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const handleDownloadConsolidated = async (reportId: string, format: 'PDF' | 'CSV') => {
    const key = `${reportId}_${format}`;
    setDownloadingReport(key);
    setInlineError(null);
    try {
      const effectiveReg = isRegionalOfficer ? officerCanonicalRegion || undefined : selectedRegion;
      await alertsApi.downloadConsolidatedReport(
        reportId,
        format,
        effectiveReg,
        startDate || undefined,
        endDate || undefined
      );
    } catch (err: any) {
      setInlineError(err.response?.data?.detail || 'Failed to download report.');
    } finally {
      setDownloadingReport(null);
    }
  };

  const handleGenerateSummary = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAppId) {
      setAppSelectError('Select an application');
      return;
    }
    setAppSelectError(null);
    setInlineError(null);
    setGenerateMsg(null);
    setIsGenerating(true);

    try {
      const filename = await alertsApi.downloadApplicationSummaryPdf(selectedAppId, language);
      setGenerateMsg(
        `Generated and downloaded official ${language.toUpperCase()} validation summary PDF: ${filename}`
      );
    } catch (err: any) {
      setInlineError(err.response?.data?.detail || 'Failed to generate application report.');
    } finally {
      setIsGenerating(false);
    }
  };

  // Filter applications by search query
  const filteredApps = applications.filter((a) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      a.application_id.toLowerCase().includes(q) ||
      a.institute_name.toLowerCase().includes(q) ||
      a.stage.toLowerCase().includes(q) ||
      a.label.toLowerCase().includes(q)
    );
  });

  const selectedAppObj = applications.find((a) => a.application_id === selectedAppId);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Reports
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Download council registers and application reports.
            </p>
          </div>
        </div>

        {/* SECTION 1: CONSOLIDATED REPORTS */}
        <div className="pt-6 space-y-4">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2">
            <div>
              <h3 className="text-sm font-semibold text-slate-800">
                Consolidated reports
              </h3>
              <p className="text-xs text-slate-600 mt-0.5">
                Download council-wide registers and supervisory audits with official stamp.
              </p>
            </div>

            {/* Filter Bar: Regional Scope & Date Range */}
            <div className="flex flex-wrap items-center gap-3 text-xs">
              {/* Region Selector */}
              <div className="flex items-center gap-1.5">
                <MapPin size={14} className="text-slate-500 shrink-0" />
                <span className="font-semibold text-slate-700">Region:</span>
                <div className="relative inline-flex items-center">
                  <select
                    value={selectedRegion}
                    disabled={isRegionalOfficer}
                    onChange={(e) => setSelectedRegion(e.target.value)}
                    className={`px-3 py-1.5 rounded-lg border border-slate-300 text-xs font-semibold text-slate-800 outline-none focus:border-[#0B3C9D] ${
                      isRegionalOfficer ? 'bg-slate-100 text-slate-500 cursor-not-allowed pr-7' : 'bg-white'
                    }`}
                  >
                    {!isRegionalOfficer && <option value="ALL">All regions (National)</option>}
                    <option value="Northern">Northern</option>
                    <option value="Southern">Southern</option>
                    <option value="Western">Western</option>
                    <option value="Eastern">Eastern</option>
                    <option value="Central">Central</option>
                    <option value="South-Western">South-Western</option>
                  </select>
                  {isRegionalOfficer && (
                    <Lock size={12} className="absolute right-2 text-slate-400 pointer-events-none" />
                  )}
                </div>
              </div>

              {/* Date Range Selectors */}
              <div className="flex items-center gap-1.5">
                <Calendar size={14} className="text-slate-500 shrink-0" />
                <span className="font-semibold text-slate-700">Dates:</span>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="px-2 py-1 rounded-lg border border-slate-300 text-xs text-slate-700 bg-white outline-none focus:border-[#0B3C9D]"
                  title="Start date"
                />
                <span className="text-slate-400">to</span>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="px-2 py-1 rounded-lg border border-slate-300 text-xs text-slate-700 bg-white outline-none focus:border-[#0B3C9D]"
                  title="End date"
                />
                {(startDate || endDate) && (
                  <button
                    type="button"
                    onClick={() => {
                      setStartDate('');
                      setEndDate('');
                    }}
                    className="p-1 hover:bg-slate-100 rounded text-slate-500 hover:text-slate-700"
                    title="Clear date range"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-2">
            {CONSOLIDATED_REPORTS.map((r) => {
              const isPdfBusy = downloadingReport === `${r.id}_PDF`;
              const isCsvBusy = downloadingReport === `${r.id}_CSV`;
              return (
                <div
                  key={r.id}
                  className="p-5 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:border-[#0B3C9D] transition-all flex flex-col justify-between shadow-2xs space-y-3"
                >
                  <div className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-[#0B3C9D]">
                        {r.category}
                      </span>
                    </div>
                    <h4 className="text-sm font-bold text-[#0F2A5C]">{r.name}</h4>
                    <p className="text-xs text-slate-600 leading-relaxed line-clamp-3">
                      {r.description}
                    </p>
                  </div>

                  <div className="pt-2 border-t border-slate-200/80 flex items-center gap-2">
                    <button
                      onClick={() => handleDownloadConsolidated(r.id, 'PDF')}
                      disabled={isPdfBusy || isCsvBusy}
                      className="flex-1 py-1.5 px-3 bg-[#0B3C9D] hover:bg-[#082b70] text-white text-xs font-bold rounded-lg shadow-2xs flex items-center justify-center gap-1.5 transition-colors disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed cursor-pointer"
                    >
                      {isPdfBusy ? <Loader2 size={13} className="animate-spin" /> : <Download size={13} />}
                      <span>Official PDF</span>
                    </button>

                    <button
                      onClick={() => handleDownloadConsolidated(r.id, 'CSV')}
                      disabled={isPdfBusy || isCsvBusy}
                      className="py-1.5 px-3 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 text-xs font-semibold rounded-lg shadow-2xs flex items-center justify-center gap-1.5 transition-colors disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed cursor-pointer"
                    >
                      {isCsvBusy ? <Loader2 size={13} className="animate-spin" /> : <FileSpreadsheet size={13} />}
                      <span>CSV</span>
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* SECTION 2: INDIVIDUAL APPLICATION SUMMARY REPORT */}
        <div className="pt-8 mt-8 border-t border-slate-200">
          <h3 className="text-sm font-semibold text-slate-800 mb-4">
            Application summary report
          </h3>

          <form onSubmit={handleGenerateSummary} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-4">
            {/* Searchable Application Select */}
            <div className="sm:col-span-2 lg:col-span-7 relative" ref={dropdownRef}>
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Application
              </label>

              <div
                onClick={() => setIsDropdownOpen(true)}
                className={`w-full min-h-[38px] px-3 py-1.5 rounded-lg border bg-white flex items-center justify-between cursor-pointer transition-colors ${
                  appSelectError ? 'border-red-500 ring-1 ring-red-500' : 'border-slate-300 focus-within:border-[#0B3C9D]'
                }`}
              >
                <div className="flex-1 flex items-center gap-2 overflow-hidden">
                  <Search size={14} className="text-slate-400 shrink-0" />
                  <input
                    type="text"
                    value={isDropdownOpen ? searchQuery : (selectedAppObj ? selectedAppObj.label : searchQuery)}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setIsDropdownOpen(true);
                      setAppSelectError(null);
                    }}
                    onFocus={() => {
                      setIsDropdownOpen(true);
                      if (selectedAppObj) setSearchQuery('');
                    }}
                    placeholder={isLoadingApps ? 'Loading applications...' : 'Type to search applications...'}
                    className="w-full text-xs font-mono text-slate-800 bg-transparent outline-none placeholder:font-sans placeholder:text-slate-400"
                  />
                </div>
                <div className="flex items-center gap-1 shrink-0 ml-2">
                  {selectedAppId && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedAppId('');
                        setSearchQuery('');
                      }}
                      className="p-1 text-slate-400 hover:text-slate-600 rounded"
                    >
                      <X size={12} />
                    </button>
                  )}
                  <ChevronDown size={14} className="text-slate-500" />
                </div>
              </div>

              {/* Validation message under field */}
              {appSelectError && (
                <p className="text-[11px] text-red-600 font-medium mt-1">
                  {appSelectError}
                </p>
              )}

              {/* Dropdown Menu */}
              {isDropdownOpen && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-white rounded-lg shadow-lg border border-slate-200 z-50 max-h-64 overflow-y-auto">
                  {isLoadingApps ? (
                    <div className="p-4 text-center text-xs text-slate-500 flex items-center justify-center gap-2">
                      <Loader2 size={14} className="animate-spin text-[#0B3C9D]" />
                      <span>Loading applications...</span>
                    </div>
                  ) : filteredApps.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-500">
                      No applications match
                    </div>
                  ) : (
                    <div className="divide-y divide-slate-100">
                      {filteredApps.map((a) => {
                        const isSelected = a.application_id === selectedAppId;
                        return (
                          <button
                            key={a.id}
                            type="button"
                            onClick={() => {
                              setSelectedAppId(a.application_id);
                              setSearchQuery('');
                              setIsDropdownOpen(false);
                              setAppSelectError(null);
                            }}
                            className={`w-full text-left p-2.5 text-xs font-mono transition-colors flex items-center justify-between ${
                              isSelected ? 'bg-blue-50 text-[#0B3C9D] font-bold' : 'hover:bg-slate-50 text-slate-800'
                            }`}
                          >
                            <span className="truncate pr-2">{a.label}</span>
                            {isSelected && <Check size={14} className="text-[#0B3C9D] shrink-0" />}
                          </button>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Language Selection */}
            <div className="lg:col-span-2">
              <label className="block text-xs font-bold text-slate-700 mb-1">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as 'en' | 'hi')}
                className="w-full h-[38px] px-3 rounded-lg border border-slate-300 text-xs bg-white text-slate-800 focus:outline-none focus:border-[#0B3C9D]"
              >
                <option value="en">English</option>
                <option value="hi">Hindi</option>
              </select>
            </div>

            {/* Download Button */}
            <div className="sm:col-span-2 lg:col-span-3 flex items-end">
              <button
                type="submit"
                disabled={isGenerating}
                className="w-full h-[38px] px-4 rounded-lg bg-[#F58220] hover:bg-[#d97016] text-white font-bold text-xs shadow-sm flex items-center justify-center gap-2 transition-colors disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed cursor-pointer"
              >
                {isGenerating ? <Loader2 size={16} className="animate-spin" /> : <Download size={16} />}
                <span>{isGenerating ? 'Compiling PDF...' : 'Download Application PDF'}</span>
              </button>
            </div>
          </form>

          {/* Inline Feedback Messages */}
          {inlineError && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs font-semibold flex items-center justify-between">
              <span>{inlineError}</span>
              <button onClick={() => setInlineError(null)} className="text-red-700 hover:text-red-900 font-bold ml-2">×</button>
            </div>
          )}

          {generateMsg && (
            <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center justify-between">
              <span>{generateMsg}</span>
              <button onClick={() => setGenerateMsg(null)} className="text-emerald-700 hover:text-emerald-900 font-bold ml-2">×</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
