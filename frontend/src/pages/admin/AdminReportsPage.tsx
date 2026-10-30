import React, { useState, useEffect } from 'react';
import {
  FileBarChart,
  Download,
  Mail,
  CheckCircle,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { instituteApi, ReportItem, ApplicationItem } from '../../api/institute';

export const AdminReportsPage: React.FC = () => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('');

  const [reportType, setReportType] = useState('Validation Summary');
  const [format, setFormat] = useState<'PDF' | 'CSV'>('PDF');
  const [dateRange] = useState('Current Academic Year 2026-27');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState<string | null>(null);

  const fetchReports = async () => {
    try {
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
      });
      setGenerateMsg(
        `Generated ${format} report successfully: ${newReport.filename}. Report archived and queued for email delivery to 25ec016@skcet.ac.in.`
      );
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center gap-2 bg-[#E3F0FF] text-[#0B3C9D] text-xs font-semibold px-2.5 py-1 rounded-md mb-2">
              <FileBarChart size={14} />
              <span>Administrative Regulatory Reports</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F2A5C] tracking-tight">
              Statutory Validation & Council Reports
            </h1>
            <p className="text-sm text-slate-500 mt-1 max-w-2xl">
              Reports are rendered with ReportLab as authenticated PDFs, downloadable and dispatched to council scrutiny officials.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 bg-blue-50 border border-blue-200 text-[#0B3C9D] px-3.5 py-2 rounded-xl text-xs font-semibold shrink-0">
            <Mail size={16} />
            <span>Target: 25ec016@skcet.ac.in</span>
          </div>
        </div>

        {/* Generate Card */}
        <div className="mt-6 bg-slate-50 rounded-xl border border-slate-200 p-6">
          <h2 className="text-sm font-bold uppercase tracking-wider text-[#0B3C9D] mb-4">
            Generate Scrutiny Export
          </h2>

          <form onSubmit={handleGenerate} className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Report Type
              </label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm bg-white"
              >
                <option value="Validation Summary">Validation Summary</option>
                <option value="Application Summary">Application Summary</option>
                <option value="Compliance Audit">Compliance Audit</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Target Application
              </label>
              <select
                value={selectedAppId}
                onChange={(e) => setSelectedAppId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm bg-white"
              >
                {applications.map((a) => (
                  <option key={a.id} value={a.application_id}>
                    {a.application_id} ({a.category})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Export Format
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setFormat('PDF')}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors ${
                    format === 'PDF' ? 'bg-[#0B3C9D] text-white' : 'bg-white border border-slate-300 text-slate-700'
                  }`}
                >
                  PDF Document
                </button>
                <button
                  type="button"
                  onClick={() => setFormat('CSV')}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors ${
                    format === 'CSV' ? 'bg-[#0B3C9D] text-white' : 'bg-white border border-slate-300 text-slate-700'
                  }`}
                >
                  CSV Data
                </button>
              </div>
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={isGenerating}
                className="w-full py-2.5 rounded-xl bg-[#0B3C9D] text-white text-xs font-bold hover:bg-[#0F2A5C] shadow-sm flex items-center justify-center gap-2"
              >
                {isGenerating ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
                <span>{isGenerating ? 'Compiling PDF...' : 'Compile Report'}</span>
              </button>
            </div>
          </form>

          {generateMsg && (
            <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center gap-2">
              <CheckCircle size={16} className="text-emerald-600" />
              <span>{generateMsg}</span>
            </div>
          )}
        </div>
      </div>

      {/* Reports Archive Table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase text-xs tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Filename</th>
                <th className="py-3.5 px-4">Report Type</th>
                <th className="py-3.5 px-4">Format</th>
                <th className="py-3.5 px-4">Size</th>
                <th className="py-3.5 px-4">Generated At</th>
                <th className="py-3.5 px-4 text-right">Download</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {reports.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    No reports generated yet.
                  </td>
                </tr>
              ) : (
                reports.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-[#0F2A5C]">
                      {r.filename}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-700">
                      {r.report_type}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-slate-100 text-slate-700">
                        {r.format}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-500 font-mono">
                      {formatBytes(r.file_size)}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-500">
                      {new Date(r.created_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <a
                        href={`/api/institute/reports/${r.id}/download`}
                        download
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-50 text-[#0B3C9D] hover:bg-blue-100 text-xs font-bold"
                      >
                        <Download size={13} />
                        <span>Download</span>
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
