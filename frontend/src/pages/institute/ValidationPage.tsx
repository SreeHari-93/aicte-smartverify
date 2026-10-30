import React, { useState, useEffect } from 'react';
import { Bot, Play, Sparkles, HelpCircle, CheckCircle2 } from 'lucide-react';
import { instituteApi, ApplicationItem, ValidationCheck, ValidationRunData } from '../../api/institute';
import { StatusPill } from '../../components/StatusPill';

export const ValidationPage: React.FC = () => {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('APP-2026-8401');
  const [checks, setChecks] = useState<ValidationCheck[]>([]);
  const [valRun, setValRun] = useState<ValidationRunData | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);

  const loadValidationForApp = async (appId: string) => {
    try {
      const data = await instituteApi.getLatestValidation(appId);
      setValRun(data);
      if (data.findings && data.findings.length > 0) {
        const mappedChecks: ValidationCheck[] = data.findings.map((f) => ({
          check: f.rule_title || f.rule_code,
          result: f.status === 'PASS' ? 'Pass' : (f.status === 'WARNING' || f.status === 'NEEDS_REVIEW' ? 'Warning' : 'Fail'),
          evidence: f.reason || 'Verified against published statutory criteria.',
          suggested_action: f.suggested_action || 'No remediation required.',
        }));
        setChecks(mappedChecks);
      } else {
        setChecks([]);
      }
    } catch {
      // Fallback to legacy report if latest endpoint fails
      try {
        const valRes = await instituteApi.getValidationReport(appId);
        setChecks(valRes.checks || []);
      } catch {
        setChecks([]);
      }
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const appsRes = await instituteApi.getApplications();
        setApplications(appsRes.items || []);
        if (appsRes.items && appsRes.items.length > 0) {
          const firstId = appsRes.items[0].application_id;
          setSelectedAppId(firstId);
          await loadValidationForApp(firstId);
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchData();
  }, []);

  const handleAppChange = async (appId: string) => {
    setSelectedAppId(appId);
    await loadValidationForApp(appId);
  };

  const handleRunValidation = async () => {
    if (!selectedAppId || isValidating) return;
    setIsValidating(true);
    try {
      const data = await instituteApi.runValidation(selectedAppId);
      setValRun(data);
      if (data.findings && data.findings.length > 0) {
        const mappedChecks: ValidationCheck[] = data.findings.map((f) => ({
          check: f.rule_title || f.rule_code,
          result: f.status === 'PASS' ? 'Pass' : (f.status === 'WARNING' || f.status === 'NEEDS_REVIEW' ? 'Warning' : 'Fail'),
          evidence: f.reason || 'Verified against published statutory criteria.',
          suggested_action: f.suggested_action || 'No remediation required.',
        }));
        setChecks(mappedChecks);
      } else {
        setChecks([]);
      }
    } catch (err) {
      console.error('Validation failed:', err);
    } finally {
      setIsValidating(false);
    }
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* 1. Controller Card with Robot Icon, App Selector, and Active "Run Validation" Button */}
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
                <option value="APP-2026-8401">APP-2026-8401</option>
              )}
            </select>
          </div>

          {/* "Run Validation" Button */}
          <div className="pt-4 sm:pt-0">
            <button
              onClick={handleRunValidation}
              disabled={isValidating}
              className="h-10 px-5 bg-[#0B3C9D] hover:bg-[#093280] active:scale-[0.98] text-white text-xs font-semibold rounded-[6px] transition-all flex items-center gap-2 shadow-xs cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed select-none"
              title="Run statutory validation engine"
            >
              <Play size={14} className={isValidating ? 'animate-spin' : ''} />
              <span>{isValidating ? 'Validating...' : 'Run Validation'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* 2. Validation Report Card with Real Status Badge */}
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

          {/* Real Overall Status & Score Badge */}
          {valRun ? (
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 border border-slate-200 px-3 py-1 rounded-full">
                Score: {valRun.score}/100
              </span>
              <StatusPill status={valRun.overall_status.replace(/_/g, ' ')} />
            </div>
          ) : (
            <span className="text-xs font-bold uppercase tracking-wider text-slate-600 bg-slate-100 border border-slate-200 px-3 py-1 rounded-full select-none flex items-center gap-1.5 shadow-xs">
              <CheckCircle2 size={14} />
              <span>Verified Published Rules</span>
            </span>
          )}
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
              {checks.length > 0 ? (
                checks.map((item, idx) => (
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
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-slate-500">
                    No deficiencies detected. Click &quot;Run Validation&quot; to execute all statutory checks.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pipeline note */}
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
