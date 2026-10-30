import React, { useState, useEffect } from 'react';
import {
  BarChart3,
  FileSpreadsheet,
  FileText,
  Download,
  Loader2,
  Sparkles,
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

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const pdfCount = reports.filter((r) => r.format === 'PDF').length;
  const csvCount = reports.filter((r) => r.format === 'CSV').length;

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Page Header Card */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <BarChart3 size={22} className="text-[#0B3C9D]" />
            <h2 className="text-xl font-bold text-[#0B3C9D] tracking-tight">
              Statutory Reports & Regulatory Export
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Generate authenticated PDF transcripts and CSV archives for institutional auditing and council visits.
          </p>
        </div>
      </div>

      {/* Stat Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
        <StatCard
          label="Total Reports Generated"
          value={reports.length}
          icon={<BarChart3 size={28} />}
          tint="blue"
        />
        <StatCard
          label="PDF Transcripts"
          value={pdfCount}
          icon={<FileText size={28} />}
          tint="amber"
        />
        <StatCard
          label="CSV Data Sheets"
          value={csvCount}
          icon={<FileSpreadsheet size={28} />}
          tint="green"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Form: Choose report type, date range, format & Generate */}
        <div className="lg:col-span-5 bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
          <div className="flex items-center gap-2 pb-4 border-b border-slate-100">
            <Sparkles size={20} className="text-[#F58220]" />
            <h3 className="text-base font-bold text-[#0F2A5C] tracking-tight">
              Generate Regulatory Report
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
              className="w-full h-11 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-[6px] transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 select-none mt-2"
            >
              {isGenerating ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Compiling Real Document via ReportLab...</span>
                </>
              ) : (
                <span>Generate Official Export</span>
              )}
            </button>
          </form>
        </div>

        {/* Right Table: List of Generated Reports with Download Buttons */}
        <div className="lg:col-span-7 bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
          <h3 className="text-base font-bold text-[#0B3C9D] pb-4 border-b border-slate-100 tracking-tight">
            Generated Reports Archive ({reports.length})
          </h3>

          <div className="overflow-x-auto mt-4">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#E3F0FF] text-[#0B3C9D] uppercase text-[11px] font-bold tracking-wider">
                  <th className="py-3 px-3.5 rounded-l-md">Report ID</th>
                  <th className="py-3 px-3.5">Application</th>
                  <th className="py-3 px-3.5">Report Title</th>
                  <th className="py-3 px-3.5">Language</th>
                  <th className="py-3 px-3.5">Generated By</th>
                  <th className="py-3 px-3.5">Date</th>
                  <th className="py-3 px-3.5 text-center rounded-r-md">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                {isLoading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400">
                      <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                      Loading reports...
                    </td>
                  </tr>
                ) : reports.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-slate-400">
                      No reports generated yet. Use the generator on the left to export official transcripts.
                    </td>
                  </tr>
                ) : (
                  reports.map((rep) => (
                    <tr key={rep.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-3.5 font-mono font-bold text-[#0B3C9D] whitespace-nowrap">
                        #{rep.id}
                      </td>
                      <td className="py-3.5 px-3.5 font-mono text-slate-700 whitespace-nowrap">
                        {rep.application_id || <span className="text-slate-400 italic">General</span>}
                      </td>
                      <td className="py-3.5 px-3.5 font-bold text-[#0F2A5C] max-w-[160px] truncate">
                        <div className="flex items-center gap-1.5">
                          <span>{rep.report_type}</span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                              rep.format === 'PDF'
                                ? 'bg-amber-100 text-amber-800'
                                : 'bg-emerald-100 text-emerald-800'
                            }`}
                          >
                            {rep.format}
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 px-3.5 whitespace-nowrap">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 uppercase">
                          {rep.language || 'EN'}
                        </span>
                      </td>
                      <td className="py-3.5 px-3.5 text-slate-600 max-w-[120px] truncate text-[11px]">
                        {rep.generated_by || 'INSTITUTE'}
                      </td>
                      <td className="py-3.5 px-3.5 whitespace-nowrap text-slate-500">
                        {new Date(rep.created_at).toLocaleDateString('en-GB')}
                        <span className="block text-[10px] text-slate-400 font-mono">
                          {formatBytes(rep.file_size)}
                        </span>
                      </td>
                      <td className="py-3.5 px-3.5 text-center">
                        <button
                          onClick={() => instituteApi.downloadReportFile(rep.id, rep.filename)}
                          className="px-3 py-1.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded-[6px] text-xs font-semibold inline-flex items-center gap-1.5 transition-colors cursor-pointer select-none"
                          title="Download stored report transcript"
                        >
                          <Download size={12} />
                          <span>Download</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
