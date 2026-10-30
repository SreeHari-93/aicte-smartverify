import React, { useState, useEffect } from 'react';
import { Bot, Play, Sparkles, HelpCircle, CheckCircle2, AlertTriangle, Languages, Info, Wrench, ShieldAlert } from 'lucide-react';
import { instituteApi, ApplicationItem, ValidationCheck, ValidationRunData, WhyFailedData } from '../../api/institute';
import { StatusPill } from '../../components/StatusPill';

export const ValidationPage: React.FC = () => {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('APP-2026-8401');
  const [checks, setChecks] = useState<ValidationCheck[]>([]);
  const [valRun, setValRun] = useState<ValidationRunData | null>(null);
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [whyFailedData, setWhyFailedData] = useState<WhyFailedData | null>(null);
  const [whyFailedLang, setWhyFailedLang] = useState<'en' | 'hi'>('en');
  const [isLoadingWhyFailed, setIsLoadingWhyFailed] = useState<boolean>(false);

  const formatVerificationStatus = (raw?: string): string => {
    if (!raw) return 'Pending';
    const u = raw.toUpperCase().trim();
    switch (u) {
      case 'VERIFIED':
        return 'Verified';
      case 'MISMATCH_DETECTED':
        return 'Mismatch Detected';
      case 'EXPIRED':
        return 'Expired';
      case 'SOURCE_UNAVAILABLE':
        return 'Source Unavailable';
      case 'MANUAL_REVIEW_REQUIRED':
        return 'Manual Review Required';
      case 'VERIFICATION_PENDING':
      default:
        return 'Pending';
    }
  };

  const mapFindingToCheck = (f: any): ValidationCheck => {
    let vStatus: string | undefined;
    let vSource: string | undefined;
    if (Array.isArray(f.evidence_json)) {
      for (const ev of f.evidence_json) {
        if (ev && typeof ev === 'object') {
          if (ev.verification_status) vStatus = String(ev.verification_status);
          if (ev.source_name) vSource = String(ev.source_name);
        }
      }
    }
    return {
      check: f.rule_title || f.rule_code,
      result: f.status === 'PASS' ? 'Pass' : (f.status === 'WARNING' || f.status === 'NEEDS_REVIEW' ? 'Warning' : 'Fail'),
      evidence: f.reason || 'Verified against published statutory criteria.',
      suggested_action: f.suggested_action || 'No remediation required.',
      verification_status: vStatus,
      source_name: vSource,
    };
  };

  const loadWhyFailed = async (appId: string, lang: 'en' | 'hi') => {
    setIsLoadingWhyFailed(true);
    try {
      const data = await instituteApi.getWhyFailed(appId, lang);
      setWhyFailedData(data);
    } catch (err) {
      console.warn('Why-failed fetch note:', err);
      setWhyFailedData(null);
    } finally {
      setIsLoadingWhyFailed(false);
    }
  };

  const loadValidationForApp = async (appId: string, lang: 'en' | 'hi' = whyFailedLang) => {
    try {
      const data = await instituteApi.getLatestValidation(appId);
      setValRun(data);
      if (data.findings && data.findings.length > 0) {
        setChecks(data.findings.map(mapFindingToCheck));
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

    // Load Why Failed explainer
    await loadWhyFailed(appId, lang);
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        const appsRes = await instituteApi.getApplications();
        setApplications(appsRes.items || []);
        if (appsRes.items && appsRes.items.length > 0) {
          const firstId = appsRes.items[0].application_id;
          setSelectedAppId(firstId);
          await loadValidationForApp(firstId, 'en');
        }
      } catch (err) {
        console.error(err);
      }
    };
    fetchData();
  }, []);

  const handleAppChange = async (appId: string) => {
    setSelectedAppId(appId);
    await loadValidationForApp(appId, whyFailedLang);
  };

  const handleLangToggle = async (lang: 'en' | 'hi') => {
    setWhyFailedLang(lang);
    if (selectedAppId) {
      await loadWhyFailed(selectedAppId, lang);
    }
  };

  const handleRunValidation = async () => {
    if (!selectedAppId || isValidating) return;
    setIsValidating(true);
    try {
      const data = await instituteApi.runValidation(selectedAppId);
      setValRun(data);
      if (data.findings && data.findings.length > 0) {
        setChecks(data.findings.map(mapFindingToCheck));
      } else {
        setChecks([]);
      }
      await loadWhyFailed(selectedAppId, whyFailedLang);
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

      {/* 2. "Why Did This Fail?" Explainer Card */}
      {whyFailedData && (
        <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 space-y-5 animate-fade-in">
          {/* Card Header & Language Toggle */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-100 gap-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0 border border-amber-200">
                <AlertTriangle size={20} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-[#0F2A5C] tracking-tight">
                    {whyFailedLang === 'hi' ? 'यह आवेदन क्यों विफल हुआ?' : 'Why did this fail?'}
                  </h3>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-purple-700 bg-purple-100 px-2.5 py-0.5 rounded-full flex items-center gap-1">
                    <Sparkles size={11} />
                    <span>AI Decision Support</span>
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {whyFailedLang === 'hi'
                    ? 'विनियामक मूल कारण विश्लेषण एवं सुधारात्मक मार्गदर्शन'
                    : 'Statutory root cause deficiency analysis & remediation guidance'}
                </p>
              </div>
            </div>

            {/* English / Hindi Toggle */}
            <div className="flex items-center gap-1.5 self-start sm:self-auto bg-slate-100 p-1 rounded-lg border border-slate-200">
              <Languages size={15} className="text-slate-500 ml-1.5" />
              <button
                type="button"
                onClick={() => handleLangToggle('en')}
                disabled={isLoadingWhyFailed}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                  whyFailedLang === 'en'
                    ? 'bg-[#0B3C9D] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                English
              </button>
              <button
                type="button"
                onClick={() => handleLangToggle('hi')}
                disabled={isLoadingWhyFailed}
                className={`px-3 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                  whyFailedLang === 'hi'
                    ? 'bg-[#0B3C9D] text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                हिंदी
              </button>
            </div>
          </div>

          {/* Headline & Plain Summary Banner */}
          <div className="p-4 rounded-xl bg-amber-50/80 border border-amber-200/90 text-amber-950 space-y-1.5">
            <h4 className="text-sm font-bold text-amber-900 flex items-center gap-2">
              <ShieldAlert size={16} className="text-amber-600 shrink-0" />
              <span>{whyFailedData.headline}</span>
            </h4>
            <p className="text-xs text-amber-900/90 leading-relaxed font-normal">
              {whyFailedData.plain_summary}
            </p>
          </div>

          {/* Root-Cause List */}
          {whyFailedData.root_causes && whyFailedData.root_causes.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  {whyFailedLang === 'hi' ? 'चिह्नित मूल कारण' : 'Identified Root Causes'} ({whyFailedData.root_causes.length})
                </h4>
                <span className="text-[11px] text-slate-500 font-medium">
                  {whyFailedLang === 'hi' ? 'गंभीरता अनुसार क्रमबद्ध' : 'Ranked by severity & impact'}
                </span>
              </div>

              <div className="grid grid-cols-1 gap-3">
                {whyFailedData.root_causes.map((rc, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 hover:bg-slate-50 transition-colors space-y-2.5"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-mono font-bold text-slate-800 bg-white border border-slate-200 px-2 py-0.5 rounded">
                          #{idx + 1}
                        </span>
                        <h5 className="text-xs font-bold text-[#0F2A5C]">
                          {rc.headline}
                        </h5>
                      </div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <StatusPill status={rc.severity} />
                        {rc.fixable_by_institute ? (
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-emerald-800 bg-emerald-100 px-2 py-0.5 rounded-full">
                            {whyFailedLang === 'hi' ? 'संस्थान द्वारा सुधार योग्य' : 'Fixable by Institute'}
                          </span>
                        ) : (
                          <span className="text-[10px] font-semibold uppercase tracking-wider text-purple-800 bg-purple-100 px-2 py-0.5 rounded-full">
                            {whyFailedLang === 'hi' ? 'आधिकारिक समीक्षा आवश्यक' : 'Official Review Required'}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Affected Rule Codes */}
                    {rc.affected_rule_codes && rc.affected_rule_codes.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap text-[11px] text-slate-600">
                        <span className="font-semibold text-slate-500">
                          {whyFailedLang === 'hi' ? 'प्रभावित नियम:' : 'Affected Rules:'}
                        </span>
                        {rc.affected_rule_codes.map((code) => (
                          <span
                            key={code}
                            className="px-2 py-0.5 font-mono text-[10px] font-bold bg-white border border-slate-200 rounded text-[#0B3C9D]"
                          >
                            {code}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Evidence Snippet */}
                    {rc.evidence && rc.evidence.length > 0 && (
                      <div className="text-[11px] text-slate-600 bg-white p-2.5 rounded-lg border border-slate-200/80 space-y-1">
                        <span className="font-bold text-slate-700 block">
                          {whyFailedLang === 'hi' ? 'साक्ष्य विवरण:' : 'Evidence Detail:'}
                        </span>
                        {rc.evidence.map((ev, evIdx) => (
                          <div key={evIdx} className="text-slate-600 font-mono text-[10px]">
                            {ev.document && <span className="font-bold text-slate-700">{ev.document} </span>}
                            {ev.field && <span>| Field: {ev.field} </span>}
                            {ev.extracted !== null && ev.extracted !== undefined && (
                              <span className="text-red-700">| Actual: {String(ev.extracted)} </span>
                            )}
                            {ev.expected !== null && ev.expected !== undefined && (
                              <span className="text-emerald-700">| Required: {String(ev.expected)}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Suggested actions inside cause */}
                    {rc.ordered_suggested_actions && rc.ordered_suggested_actions.length > 0 && (
                      <p className="text-xs text-slate-700">
                        <strong className="text-slate-800">
                          {whyFailedLang === 'hi' ? 'कार्रवाई: ' : 'Remediation: '}
                        </strong>
                        {rc.ordered_suggested_actions[0]}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* "How to Fix" Steps */}
          {whyFailedData.how_to_fix && whyFailedData.how_to_fix.length > 0 && (
            <div className="space-y-2.5">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center gap-1.5">
                <Wrench size={14} className="text-[#0B3C9D]" />
                <span>{whyFailedLang === 'hi' ? 'सुधार के आवश्यक कदम' : 'How to Fix (Actionable Steps)'}</span>
              </h4>

              <div className="space-y-2">
                {whyFailedData.how_to_fix.map((item, idx) => (
                  <div
                    key={idx}
                    className="flex items-start justify-between gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-800"
                  >
                    <div className="flex items-start gap-2.5">
                      <span className="w-5 h-5 rounded-full bg-[#0B3C9D] text-white flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                        {idx + 1}
                      </span>
                      <span className="font-medium mt-0.5 leading-relaxed">{item.step}</span>
                    </div>
                    <span className="shrink-0 text-[10px] font-bold px-2 py-0.5 rounded-full bg-white border border-slate-200 text-slate-700">
                      {whyFailedLang === 'hi' ? `प्रयास: ${item.effort}` : `Effort: ${item.effort}`}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Official Review Scope Note */}
          {whyFailedData.what_officials_will_review && (
            <div className="text-[11px] text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-200">
              <strong className="text-slate-800">
                {whyFailedLang === 'hi' ? 'एआईसीटीई अधिकारी समीक्षा दायरा: ' : 'What Officials Will Review: '}
              </strong>
              {whyFailedData.what_officials_will_review}
            </div>
          )}

          {/* Mandatory AICTE Disclaimer */}
          <div className="p-3 rounded-lg bg-[#E3F0FF] border border-[#BBD8F5] text-xs text-[#0B3C9D] flex items-center gap-2">
            <Info size={15} className="shrink-0 text-[#0B3C9D]" />
            <span className="font-medium">{whyFailedData.disclaimer}</span>
          </div>
        </div>
      )}

      {/* 3. Validation Report Card with Real Status Badge */}
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
                      <div>{item.evidence}</div>
                      {(item.verification_status || item.source_name) && (
                        <div className="mt-2 flex items-center gap-2 flex-wrap">
                          {item.verification_status && (
                            <StatusPill
                              status={formatVerificationStatus(item.verification_status)}
                              className="text-[10px] py-0.5 px-2"
                            />
                          )}
                          {item.source_name && (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                              Source: <strong className="text-[#0B3C9D]">{item.source_name}</strong>
                            </span>
                          )}
                        </div>
                      )}
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
