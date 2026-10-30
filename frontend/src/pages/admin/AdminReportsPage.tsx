import React, { useState, useEffect } from 'react';
import {
  FileBarChart,
  Download,
  Mail,
  CheckCircle,
  Loader2,
  FileText,
} from 'lucide-react';
import { adminApi, AdminReportItem } from '../../api/admin';
import { instituteApi, ApplicationItem } from '../../api/institute';

export const AdminReportsPage: React.FC = () => {
  const [reports, setReports] = useState<AdminReportItem[]>([]);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [language, setLanguage] = useState<'en' | 'hi'>('en');

  const [format, setFormat] = useState<'PDF' | 'CSV'>('PDF');
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateMsg, setGenerateMsg] = useState<string | null>(null);

  const fetchReports = async () => {
    try {
      const [reportsRes, appsRes] = await Promise.all([
        adminApi.listReports(),
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
    if (!selectedAppId) {
      alert('Please select an application.');
      return;
    }
    setIsGenerating(true);
    setGenerateMsg(null);

    try {
      await adminApi.downloadApplicationReportPdf(selectedAppId, language);
      setGenerateMsg(
        `Generated and downloaded official ${language.toUpperCase()} validation summary PDF for application ${selectedAppId}.`
      );
      // Refresh reports list
      const updated = await adminApi.listReports();
      setReports(updated);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to generate report.');
    } finally {
      setIsGenerating(false);
    }
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
              Official council verification transcripts compiled via ReportLab. Governed under "Rules decide, AI explains, Officials approve."
            </p>
          </div>

          <div className="inline-flex items-center gap-2 bg-blue-50 border border-blue-200 text-[#0B3C9D] px-3.5 py-2 rounded-xl text-xs font-semibold shrink-0">
            <Mail size={16} />
            <span>Target: 25ec016@skcet.ac.in</span>
          </div>
        </div>

        {/* Generate Card */}
        <div className="pt-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-4">
            Compile Official Validation Report
          </h3>

          <form onSubmit={handleGenerate} className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Application</label>
              <select
                value={selectedAppId}
                onChange={(e) => setSelectedAppId(e.target.value)}
                className="w-full py-2 px-3 rounded-lg border border-slate-300 text-xs font-mono bg-white focus:outline-none focus:border-[#0B3C9D]"
              >
                {applications.map((a) => (
                  <option key={a.id} value={a.application_id}>
                    {a.application_id} - {a.programme || a.category}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Language</label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value as 'en' | 'hi')}
                className="w-full py-2 px-3 rounded-lg border border-slate-300 text-xs font-semibold bg-white focus:outline-none focus:border-[#0B3C9D]"
              >
                <option value="en">English (Official Standard)</option>
                <option value="hi">हिन्दी (Devanagari Transcript)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-600 mb-1">Format</label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setFormat('PDF')}
                  className={`flex-1 py-2 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-1.5 ${
                    format === 'PDF' ? 'bg-[#0B3C9D] text-white' : 'bg-white border border-slate-300 text-slate-700'
                  }`}
                >
                  <FileText size={13} />
                  <span>PDF Document</span>
                </button>
              </div>
            </div>

            <div className="flex items-end">
              <button
                type="submit"
                disabled={isGenerating}
                className="w-full py-2.5 rounded-xl bg-[#F58220] hover:bg-[#E06E0C] text-white text-xs font-bold shadow-sm flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 transition-colors select-none"
              >
                {isGenerating ? <Loader2 size={16} className="animate-spin" /> : <Download size={15} />}
                <span>{isGenerating ? 'Compiling PDF...' : 'Download PDF Report'}</span>
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
        <div className="p-4 sm:p-6 border-b border-slate-100 flex items-center justify-between">
          <h3 className="text-base font-bold text-[#0F2A5C] tracking-tight">
            Generated Reports Repository ({reports.length})
          </h3>
          <span className="text-xs text-slate-500 font-medium">
            Permanent scrutiny records archive
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-700">
            <thead className="bg-[#E3F0FF] text-[#0B3C9D] font-bold border-b border-slate-200 uppercase tracking-wider">
              <tr>
                <th className="py-3 px-3.5">Report ID</th>
                <th className="py-3 px-3.5">Institute</th>
                <th className="py-3 px-3.5">Application</th>
                <th className="py-3 px-3.5">Report Type</th>
                <th className="py-3 px-3.5">Language</th>
                <th className="py-3 px-3.5">Generated By</th>
                <th className="py-3 px-3.5">Date</th>
                <th className="py-3 px-3.5 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium">
              {reports.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No reports generated yet.
                  </td>
                </tr>
              ) : (
                reports.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3 px-3.5 font-mono font-bold text-[#0B3C9D]">
                      #{r.id}
                    </td>
                    <td className="py-3 px-3.5 text-slate-800 font-semibold max-w-[150px] truncate">
                      {r.institute_name || `Institute #${r.institute_id}`}
                    </td>
                    <td className="py-3 px-3.5 font-mono text-slate-700 whitespace-nowrap">
                      {r.application_id || <span className="text-slate-400 italic">General</span>}
                    </td>
                    <td className="py-3 px-3.5 font-semibold text-slate-800 max-w-[150px] truncate">
                      <div className="flex items-center gap-1.5">
                        <span>{r.report_type}</span>
                        <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold ${
                          r.format === 'PDF' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800'
                        }`}>
                          {r.format}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-3.5 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 uppercase">
                        {r.language || 'EN'}
                      </span>
                    </td>
                    <td className="py-3 px-3.5 text-slate-600 max-w-[120px] truncate text-[11px]">
                      {r.generated_by || 'ADMIN'}
                    </td>
                    <td className="py-3 px-3.5 whitespace-nowrap text-slate-500">
                      {new Date(r.created_at).toLocaleDateString('en-GB')}
                    </td>
                    <td className="py-3 px-3.5 text-center whitespace-nowrap">
                      <button
                        onClick={() => adminApi.downloadReportFile(r.id, r.filename)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-[#0B3C9D] hover:bg-[#092E7A] text-white text-xs font-semibold cursor-pointer select-none transition-colors"
                        title="Download archived report PDF"
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
  );
};
