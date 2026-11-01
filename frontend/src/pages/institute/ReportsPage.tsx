import { DataTable, ColumnDef } from '../../components/DataTable';
import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  FileSpreadsheet,
  FileText,
  Download,
  Loader2,
  CheckCircle,
} from 'lucide-react';
import { instituteApi, ReportItem, ApplicationItem } from '../../api/institute';
import { StatCard } from '../../components/StatCard';

export const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);

  // Form State
  const [reportType, setReportType] = useState('Validation Summary');
  const [dateRange, setDateRange] = useState('Current Academic Year 2026-27');
  const [language, setLanguage] = useState<'en' | 'hi'>('en');
  const [format, setFormat] = useState<'PDF' | 'CSV'>('PDF');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState<string | null>(null);

  const fetchReports = async () => {
    try {
      setIsLoading(true);
      const [reportsRes, appsRes] = await Promise.all([
        instituteApi.getReports(),
        instituteApi.getApplications().catch(() => ({ items: [] })),
      ]);
      setReports(reportsRes);
      if (appsRes && appsRes.items) {
        setApplications(appsRes.items);
        if (appsRes.items.length > 0) {
          setSelectedAppId(appsRes.items[0].application_id);
        }
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsGenerating(true);
    setGenerateMsg(null);

    try {
      const newReport = await instituteApi.generateReport({
        report_type: reportType,
        format,
        date_range: dateRange,
        application_id: selectedAppId || undefined,
        language,
      });
      setGenerateMsg(`Generated ${format} report successfully: ${newReport.filename}`);
      setReports((prev) => [newReport, ...prev]);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate report.');
    } finally {
      setIsGenerating(false);
    }
  };

  
  const pdfCount = reports.filter((r) => r.format === 'PDF').length;
  const csvCount = reports.filter((r) => r.format === 'CSV').length;

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Page Header Card */}
      <div className="bg-white rounded-xl p-6 shadow-sm border border-slate-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Reports
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Generate PDF transcripts and compliance export archives.
          </p>
        </div>
      </div>

      {/* Stat Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <StatCard
          label="Total reports generated"
          value={reports.length}
          icon={<BarChart3 size={28} />}
          tint="blue"
        />
        <StatCard
          label="PDF transcripts"
          value={pdfCount}
          icon={<FileText size={28} />}
          tint="amber"
        />
        <StatCard
          label="CSV data sheets"
          value={csvCount}
          icon={<FileSpreadsheet size={28} />}
          tint="green"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Form: Choose report type, date range, format & Generate */}
        <div className="lg:col-span-5 bg-white rounded-lg p-6 shadow-sm border border-slate-200">
          <div className="pb-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-900">
              Generate report
            </h3>
          </div>

          <form onSubmit={handleGenerate} className="space-y-4 mt-4 text-xs">
            {generateMsg && (
              <div className="p-3 bg-green-50 border border-green-200 text-[#1E7036] rounded-lg font-semibold flex items-center gap-2">
                <CheckCircle size={16} />
                <span className="truncate">{generateMsg}</span>
              </div>
            )}

            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Select Report Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              >
                <option value="Application Summary">Application Summary (EoA, Intake, Status)</option>
                <option value="Certificate Expiry">Certificate Expiry Tracker (NOCs, Stability, Fire)</option>
                <option value="Validation Summary">Validation Summary (AI Compliance Scrutiny)</option>
              </select>
            </div>

            {reportType === 'Validation Summary' && (
              <div>
                <label className="font-bold text-[#0F2A5C] block mb-1">Target Application</label>
                <select
                  value={selectedAppId}
                  onChange={(e) => setSelectedAppId(e.target.value)}
                  className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
                >
                  <option value="">Latest Active Application (Auto-detected)</option>
                  {applications.map((app) => (
                    <option key={app.id} value={app.application_id}>
                      {app.application_id} ({app.category} - {app.academic_year})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Time Horizon / Date Range</label>
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              >
                <option value="Current Academic Year 2026-27">Current Academic Year 2026-27</option>
                <option value="Past 30 Days">Past 30 Days</option>
                <option value="Past 90 Days">Past 90 Days</option>
                <option value="Full Institutional History">Full Institutional History</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as 'en' | 'hi')}
                className="w-full h-10 px-3 text-xs rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              >
                <option value="en">English (Official Regulatory Standard)</option>
                <option value="hi">हिन्दी (Devanagari Transcript)</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Export File Format</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setFormat('PDF')}
                  className={`h-11 rounded-lg border flex items-center justify-center gap-2 font-bold transition-all ${
                    format === 'PDF'
                      ? 'border-[#0B3C9D] bg-[#E3F0FF] text-[#0B3C9D] shadow-xs'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <FileText size={16} />
                  <span>PDF Document</span>
                </button>
                <button
                  type="button"
                  onClick={() => setFormat('CSV')}
                  className={`h-11 rounded-lg border flex items-center justify-center gap-2 font-bold transition-all ${
                    format === 'CSV'
                      ? 'border-[#1E7036] bg-[#E2F6E6] text-[#1E7036] shadow-xs'
                      : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  <FileSpreadsheet size={16} />
                  <span>CSV Data Table</span>
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isGenerating}
              className="w-full h-10 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-sm disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed select-none mt-2 text-xs"
            >
              {isGenerating ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Generating report...</span>
                </>
              ) : (
                <span>Generate report</span>
              )}
            </button>
          </form>
        </div>

        {/* Right Table: List of Generated Reports */}
        <div className="lg:col-span-7 bg-white rounded-xl p-6 shadow-sm border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-900 pb-4 border-b border-slate-100">
            Reports archive ({reports.length})
          </h3>

          <div className="mt-4">
            {(() => {
              const columns: ColumnDef<ReportItem>[] = [
                {
                  key: 'report_id',
                  header: 'Report',
                  width: '18%',
                  align: 'left',
                  render: (rep) => (
                    <div>
                      <div className="font-mono font-medium text-[#0B3C9D] text-xs">#{rep.id}</div>
                      <div className="text-[10px] text-slate-600 font-mono">
                        {rep.application_id || 'General'}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'title_format',
                  header: 'Title & format',
                  width: '36%',
                  align: 'left',
                  render: (rep) => (
                    <div>
                      <div className="font-medium text-slate-900 text-xs line-clamp-2" title={rep.report_type}>
                        {rep.report_type}
                      </div>
                      <div className="text-[10px] text-slate-600 uppercase font-bold tracking-wider mt-0.5">
                        {rep.format}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'language',
                  header: 'Language',
                  width: '12%',
                  align: 'left',
                  render: (rep) => (
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 uppercase">
                      {rep.language}
                    </span>
                  ),
                },
                {
                  key: 'date_size',
                  header: 'Date & size',
                  width: '18%',
                  align: 'left',
                  render: (rep) => (
                    <div>
                      <div className="text-xs text-slate-700">
                        {new Date(rep.created_at).toLocaleDateString('en-GB')}
                      </div>
                      <div className="text-[10px] text-slate-600">
                        {rep.file_size ? `${Math.round(rep.file_size / 1024)} KB` : 'Ready'}
                      </div>
                    </div>
                  ),
                },
                {
                  key: 'action',
                  header: 'Action',
                  width: '16%',
                  align: 'right',
                  render: (rep) => (
                    <button
                      onClick={() => instituteApi.downloadReportFile(rep.id, rep.filename)}
                      className="px-2.5 py-1 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 rounded text-xs font-semibold inline-flex items-center gap-1 shadow-2xs transition-colors"
                    >
                      <Download size={11} />
                      <span>Download</span>
                    </button>
                  ),
                },
              ];

              return (
                <DataTable
                  columns={columns}
                  data={reports}
                  keyExtractor={(rep) => rep.id}
                  isLoading={isLoading}
                  emptyMessage="No reports yet."
                  isLong={reports.length > 12}
                />
              );
            })()}
          </div>
        </div>
      </div>
    </div>
  );
};
