import React, { useState, useEffect } from 'react';
import { Bot, Play, Sparkles, AlertCircle, HelpCircle } from 'lucide-react';
import { instituteApi, ApplicationItem, ValidationCheck } from '../../api/institute';
import { StatusPill } from '../../components/StatusPill';

export const ValidationPage: React.FC = () => {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('APP-2026-8401');
  const [checks, setChecks] = useState<ValidationCheck[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const appsRes = await instituteApi.getApplications();
        setApplications(appsRes.items || []);
        if (appsRes.items && appsRes.items.length > 0) {
          const firstId = appsRes.items[0].application_id;
          setSelectedAppId(firstId);
          const valRes = await instituteApi.getValidationReport(firstId);
          setChecks(valRes.checks);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchData();
  }, []);

  const handleAppChange = async (appId: string) => {
    setSelectedAppId(appId);
    try {
      const valRes = await instituteApi.getValidationReport(appId);
      setChecks(valRes.checks);
    } catch {
      // quiet fallback
    }
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* 1. Controller Card with Robot Icon, App Selector, and Disabled "Run Validation" Button */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-[#E3F0FF] text-[#0B3C9D] flex items-center justify-center shrink-0">
            <Bot size={26} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-[#0B3C9D] tracking-tight">
                AI Validation & Scrutiny Engine
              </h2>
              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                <Sparkles size={11} />
                <span>SmartVerify AI Core</span>
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Automated multi-point regulatory compliance verification, cross-document OCR reconciliation & deficiency detection.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex flex-col">
            <label className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
              Select Application
            </label>
            <select
              value={selectedAppId}
              onChange={(e) => handleAppChange(e.target.value)}
              className="h-10 px-3 text-xs rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none font-mono"
            >
              {applications.length > 0 ? (
                applications.slice(0, 10).map((a) => (
                  <option key={a.id} value={a.application_id}>
                    {a.application_id} - {a.category.substring(0, 26)}
                  </option>
                ))
              ) : (
                <option value="APP-2026-8401">APP-2026-8401 (Sample)</option>
              )}
            </select>
          </div>

          {/* "Run Validation" Button (disabled with tooltip "Available in the next step") */}
          <div className="pt-4 sm:pt-0 relative group">
            <button
              disabled
              className="h-10 px-5 bg-slate-300 text-slate-500 text-xs font-semibold rounded-[6px] cursor-not-allowed flex items-center gap-2 shadow-none select-none"
              title="Available in the next step"
            >
              <Play size={14} />
              <span>Run Validation</span>
            </button>
            {/* Tooltip */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block w-44 p-2 bg-slate-800 text-white text-[11px] text-center rounded-md shadow-lg pointer-events-none z-30">
              Available in the next step
            </div>
          </div>
        </div>
      </div>

      {/* 2. Validation Report Card with Sample Data Badge */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <h3 className="text-base font-bold text-[#0F2A5C] tracking-tight">
              Deficiency Scrutiny Checklist
            </h3>
            <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-2 py-0.5 rounded">
              Ref: {selectedAppId}
            </span>
          </div>

          {/* Clearly labelled "Sample data" badge */}
          <span className="text-xs font-bold uppercase tracking-wider text-amber-800 bg-[#FFF0D6] border border-amber-200 px-3 py-1 rounded-full select-none flex items-center gap-1.5 shadow-xs">
            <AlertCircle size={14} />
            <span>Sample data</span>
          </span>
        </div>

        {/* Validation Table: Check, Result, Evidence, Suggested Action */}
        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#E3F0FF] text-[#0B3C9D] uppercase text-[11px] font-bold tracking-wider">
                <th className="py-3 px-4 rounded-l-md w-1/4">Statutory Check</th>
                <th className="py-3 px-4 w-28">Result</th>
                <th className="py-3 px-4 w-5/12">Evidence & Verification Detail</th>
                <th className="py-3 px-4 rounded-r-md">Suggested Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {checks.map((item, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-4 px-4 font-bold text-[#0F2A5C] align-top">
                    {item.check}
                  </td>
                  <td className="py-4 px-4 align-top">
                    <StatusPill status={item.result} />
                  </td>
                  <td className="py-4 px-4 text-slate-600 leading-relaxed align-top">
                    {item.evidence}
                  </td>
                  <td className="py-4 px-4 text-slate-800 font-medium align-top">
                    {item.suggested_action}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pipeline roadmap teaser note */}
        <div className="mt-6 p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-start gap-3">
          <HelpCircle size={18} className="text-[#0B3C9D] shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            The full AI validation pipeline integrates with <strong>Step 3 (Document OCR extraction)</strong> and{' '}
            <strong>Step 4 (Deep Learning Anomaly Detection)</strong> to automatically verify seal authenticity, signature matches,
            and discrepancy flags against the AICTE Approval Handbook repository.
          </p>
        </div>
      </div>
    </div>
  );
};
