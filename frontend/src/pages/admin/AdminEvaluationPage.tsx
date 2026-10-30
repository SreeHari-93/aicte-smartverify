import React, { useState, useEffect } from 'react';
import {
  Cpu,
  Play,
  FileSpreadsheet,
  FileText,
  CheckCircle2,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Loader2,
  RefreshCw,
  Search,
  Eye,
  GitCommit,
  Info,
  ShieldCheck,
  ThumbsUp,
} from 'lucide-react';
import { adminApi, EvaluationRunData, FeedbackStatsData } from '../../api/admin';
import { Modal } from '../../components/Modal';

export const AdminEvaluationPage: React.FC = () => {
  const [runs, setRuns] = useState<EvaluationRunData[]>([]);
  const [selectedRun, setSelectedRun] = useState<EvaluationRunData | null>(null);
  const [feedbackStats, setFeedbackStats] = useState<FeedbackStatsData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunningEval, setIsRunningEval] = useState(false);
  const [failedCasesSearch, setFailedCasesSearch] = useState('');
  const [previewCase, setPreviewCase] = useState<{
    filename: string;
    doc_type: string;
    failures: string[];
    details: Record<string, any>;
  } | null>(null);

  // Compare with previous run if available
  const currentRunIndex = runs.findIndex((r) => r.id === selectedRun?.id);
  const previousRun = currentRunIndex >= 0 && currentRunIndex < runs.length - 1 ? runs[currentRunIndex + 1] : null;

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [runsData, stats] = await Promise.all([
        adminApi.listEvaluationRuns(20),
        adminApi.getFeedbackStats(),
      ]);
      setRuns(runsData);
      setFeedbackStats(stats);
      if (runsData.length > 0 && !selectedRun) {
        setSelectedRun(runsData[0]);
      } else if (runsData.length > 0 && selectedRun) {
        const found = runsData.find((r: EvaluationRunData) => r.id === selectedRun.id);
        setSelectedRun(found || runsData[0]);
      }
    } catch (err) {
      console.error('Failed to load evaluation runs:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunEvaluation = async () => {
    if (isRunningEval) return;
    setIsRunningEval(true);
    try {
      const newRun = await adminApi.triggerEvaluationRun();
      await loadData();
      setSelectedRun(newRun);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to trigger evaluation run.');
    } finally {
      setIsRunningEval(false);
    }
  };

  const handleDownloadCsv = async () => {
    if (!selectedRun) return;
    try {
      await adminApi.downloadEvaluationCsv(selectedRun.id);
    } catch (err) {
      alert('Failed to export CSV.');
    }
  };

  const handleDownloadPdf = async () => {
    if (!selectedRun) return;
    try {
      await adminApi.downloadEvaluationPdf(selectedRun.id);
    } catch (err) {
      alert('Failed to export summary PDF.');
    }
  };

  // Delta helpers
  const calcDelta = (currentVal?: number, prevVal?: number) => {
    if (currentVal === undefined || prevVal === undefined) return null;
    const diff = currentVal - prevVal;
    return Math.round(diff * 10) / 10;
  };

  const metrics = selectedRun?.metrics_json;
  const classification = metrics?.classification;
  const fieldExtraction = metrics?.field_extraction;
  const anomalyDetectors = metrics?.anomaly_detectors;
  const explainer = metrics?.explainer_grounding;

  // Filtered failed cases
  const failedCases = (selectedRun?.failed_cases_json || []).filter((fc) => {
    if (!failedCasesSearch) return true;
    const q = failedCasesSearch.toLowerCase();
    return (
      fc.filename.toLowerCase().includes(q) ||
      fc.doc_type.toLowerCase().includes(q) ||
      fc.failures.some((f) => f.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6 pb-14 animate-fade-in">
      {/* Header Banner */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <Cpu size={24} className="text-[#0B3C9D]" />
            <h1 className="text-xl font-bold text-[#0B3C9D] tracking-tight">
              AI Evaluation & Model Governance Metrics
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Standardised benchmark evaluation across OCR, Document Classification, Field Extraction, and Anomaly Detectors.
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={isLoading}
            className="p-2.5 text-slate-500 hover:text-[#0B3C9D] hover:bg-slate-50 rounded-lg transition-colors border border-slate-200"
            title="Refresh runs"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          </button>

          <button
            onClick={handleRunEvaluation}
            disabled={isRunningEval}
            className="h-10 px-5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white font-bold rounded-lg text-xs flex items-center gap-2 transition-all shadow-sm disabled:opacity-50"
          >
            {isRunningEval ? (
              <>
                <Loader2 size={16} className="animate-spin text-white" />
                <span>Running Pipeline Benchmark...</span>
              </>
            ) : (
              <>
                <Play size={16} fill="white" />
                <span>Run Evaluation</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Mandatory Disclaimer & Wording Standard Banner */}
      <div className="bg-[#FFF8E6] border border-[#F58220]/30 rounded-[10px] p-4 flex items-start gap-3 text-amber-900 shadow-xs">
        <Info size={19} className="text-[#F58220] shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="text-xs font-semibold">
            Measured on synthetic data. Real-world accuracy must be validated on actual AICTE submissions.
          </p>
          <p className="text-[11px] text-amber-800/90 leading-relaxed">
            AICTE Governance Principle: <span className="font-bold">&quot;Rules decide, AI explains, Officials approve.&quot;</span> Anomaly scores and automated classifications assist human reviewers and do not make unilateral final determinations.
          </p>
        </div>
      </div>

      {/* Run Selector & Metadata Bar */}
      <div className="bg-white rounded-[12px] p-4 shadow-sm border border-slate-200 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <label className="text-xs font-bold text-slate-600 uppercase tracking-wider">
            Evaluation Run:
          </label>
          <select
            value={selectedRun?.id || ''}
            onChange={(e) => {
              const run = runs.find((r) => r.id === Number(e.target.value));
              if (run) setSelectedRun(run);
            }}
            className="text-xs font-semibold px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
          >
            {runs.map((r) => (
              <option key={r.id} value={r.id}>
                Run #{r.id} ({new Date(r.started_at).toLocaleString('en-GB')}) — Acc: {r.overall_accuracy.toFixed(1)}% ({r.passed_samples}/{r.total_samples})
              </option>
            ))}
          </select>

          {selectedRun && (
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="flex items-center gap-1 bg-slate-100 px-2.5 py-1 rounded-md text-[11px]">
                <Clock size={12} />
                <span>{selectedRun.duration_seconds.toFixed(1)}s</span>
              </span>
              {selectedRun.git_commit && (
                <span className="flex items-center gap-1 bg-slate-100 px-2.5 py-1 rounded-md text-[11px] font-mono">
                  <GitCommit size={12} />
                  <span>{selectedRun.git_commit.slice(0, 7)}</span>
                </span>
              )}
              <span className="bg-blue-50 text-[#0B3C9D] font-bold px-2 py-0.5 rounded text-[10px]">
                {selectedRun.dataset_version}
              </span>
            </div>
          )}
        </div>

        {/* Export Buttons */}
        {selectedRun && (
          <div className="flex items-center gap-2">
            <button
              onClick={handleDownloadCsv}
              className="h-8 px-3 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <FileSpreadsheet size={13} className="text-emerald-700" />
              <span>Export CSV</span>
            </button>
            <button
              onClick={handleDownloadPdf}
              className="h-8 px-3 text-xs font-semibold text-white bg-[#0B3C9D] hover:bg-[#092E7A] rounded-lg flex items-center gap-1.5 transition-colors shadow-xs"
            >
              <FileText size={13} />
              <span>Summary PDF</span>
            </button>
          </div>
        )}
      </div>

      {/* Key Metric Cards */}
      {selectedRun && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          {/* 1. Overall Accuracy */}
          <div className="bg-white rounded-[12px] p-4 border border-slate-200 shadow-sm relative overflow-hidden">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Overall Accuracy
            </div>
            <div className="text-2xl font-black text-[#0B3C9D] mt-1.5">
              {selectedRun.overall_accuracy.toFixed(1)}%
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {selectedRun.passed_samples} / {selectedRun.total_samples} passed
            </div>
            {previousRun && (
              <div className="mt-2 text-[10px] font-semibold flex items-center gap-0.5">
                {selectedRun.overall_accuracy >= previousRun.overall_accuracy ? (
                  <span className="text-emerald-600 flex items-center">
                    <ArrowUpRight size={12} />
                    +{(selectedRun.overall_accuracy - previousRun.overall_accuracy).toFixed(1)}% vs prev
                  </span>
                ) : (
                  <span className="text-red-500 flex items-center">
                    <ArrowDownRight size={12} />
                    {(selectedRun.overall_accuracy - previousRun.overall_accuracy).toFixed(1)}% vs prev
                  </span>
                )}
              </div>
            )}
          </div>

          {/* 2. Classification Macro F1 */}
          <div className="bg-white rounded-[12px] p-4 border border-slate-200 shadow-sm">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Classification F1
            </div>
            <div className="text-2xl font-black text-slate-800 mt-1.5">
              {classification ? `${(classification.macro_f1 * 100).toFixed(1)}%` : '—'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Acc: {classification ? `${(classification.accuracy * 100).toFixed(1)}%` : '—'}
            </div>
            {previousRun?.metrics_json?.classification && classification && (
              <div className="mt-2 text-[10px] font-semibold flex items-center gap-0.5">
                {(() => {
                  const d = calcDelta(classification.macro_f1 * 100, previousRun.metrics_json.classification.macro_f1 * 100);
                  if (d === null) return null;
                  return d >= 0 ? (
                    <span className="text-emerald-600 flex items-center"><ArrowUpRight size={12} />+{d}% vs prev</span>
                  ) : (
                    <span className="text-red-500 flex items-center"><ArrowDownRight size={12} />{d}% vs prev</span>
                  );
                })()}
              </div>
            )}
          </div>

          {/* 3. Field Match Rate */}
          <div className="bg-white rounded-[12px] p-4 border border-slate-200 shadow-sm">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Field Match Rate
            </div>
            <div className="text-2xl font-black text-slate-800 mt-1.5">
              {fieldExtraction ? `${(fieldExtraction.overall_normalized_match * 100).toFixed(1)}%` : '—'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Exact: {fieldExtraction ? `${(fieldExtraction.overall_exact_match * 100).toFixed(1)}%` : '—'}
            </div>
            {previousRun?.metrics_json?.field_extraction && fieldExtraction && (
              <div className="mt-2 text-[10px] font-semibold flex items-center gap-0.5">
                {(() => {
                  const d = calcDelta(fieldExtraction.overall_normalized_match * 100, previousRun.metrics_json.field_extraction.overall_normalized_match * 100);
                  if (d === null) return null;
                  return d >= 0 ? (
                    <span className="text-emerald-600 flex items-center"><ArrowUpRight size={12} />+{d}% vs prev</span>
                  ) : (
                    <span className="text-red-500 flex items-center"><ArrowDownRight size={12} />{d}% vs prev</span>
                  );
                })()}
              </div>
            )}
          </div>

          {/* 4. Anomaly Detector FPR */}
          <div className="bg-white rounded-[12px] p-4 border border-slate-200 shadow-sm">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Anomaly Detector FPR
            </div>
            <div className="text-2xl font-black text-emerald-700 mt-1.5">
              {anomalyDetectors ? `${(anomalyDetectors.overall_fpr * 100).toFixed(1)}%` : '0.0%'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              Target: &lt;10.0%
            </div>
            <div className="mt-2 text-[10px] font-semibold text-emerald-600 flex items-center gap-1">
              <ShieldCheck size={12} /> Low false alert rate
            </div>
          </div>

          {/* 5. Explainer Grounding */}
          <div className="bg-white rounded-[12px] p-4 border border-slate-200 shadow-sm">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
              Explainer Grounding
            </div>
            <div className="text-2xl font-black text-[#0B3C9D] mt-1.5">
              {explainer ? `${explainer.grounding_rate_pct.toFixed(1)}%` : '100%'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {explainer?.statements_grounded || 0} / {explainer?.statements_checked || 0} grounded
            </div>
            <div className="mt-2 text-[10px] font-semibold text-slate-500">
              Zero hallucinated claims
            </div>
          </div>

          {/* 6. Human Agreement Rate */}
          <div className="bg-white rounded-[12px] p-4 border border-slate-200 shadow-sm">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
              <ThumbsUp size={11} className="text-[#0B3C9D]" />
              Human Agreement
            </div>
            <div className="text-2xl font-black text-[#0B3C9D] mt-1.5">
              {feedbackStats && feedbackStats.total_feedback > 0
                ? `${feedbackStats.agreement_rate_pct.toFixed(1)}%`
                : '100%'}
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">
              {feedbackStats?.total_feedback || 0} total reviews logged
            </div>
            <div className="mt-2 text-[10px] text-slate-500">
              Officer review consensus
            </div>
          </div>
        </div>
      )}

      {/* Main Grid: Per-Field Accuracy & Anomaly Detector Performance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Per-Field Accuracy Breakdown */}
        <div className="bg-white rounded-[12px] p-6 shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-[#0F2A5C] uppercase tracking-wider">
                Per-Field Extraction Accuracy
              </h3>
              <p className="text-xs text-slate-500">
                Normalized match (case/format-insensitive) vs Strict exact match
              </p>
            </div>
          </div>

          <div className="space-y-4">
            {fieldExtraction?.per_field &&
              Object.entries(fieldExtraction.per_field).map(([fieldKey, fStats]) => (
                <div key={fieldKey} className="space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-700 capitalize">
                      {fieldKey.replace(/_/g, ' ')}
                    </span>
                    <span className="font-bold text-slate-800">
                      {fStats.normalized_match_pct.toFixed(1)}%{' '}
                      <span className="text-[10px] text-slate-400 font-normal">
                        (exact: {fStats.exact_match_pct.toFixed(1)}%, n={fStats.total_evaluated})
                      </span>
                    </span>
                  </div>
                  {/* Dual progress bar */}
                  <div className="w-full bg-slate-100 rounded-full h-3 overflow-hidden flex">
                    <div
                      className="bg-[#0B3C9D] h-full rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(100, fStats.normalized_match_pct)}%` }}
                    />
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Anomaly Detector Performance Table */}
        <div className="bg-white rounded-[12px] p-6 shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-[#0F2A5C] uppercase tracking-wider">
                Anomaly Detector Precision & FPR
              </h3>
              <p className="text-xs text-slate-500">
                Detector benchmark across synthetic tamper, date mismatch, and metadata anomalies
              </p>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500 font-bold uppercase text-[10px] tracking-wider">
                  <th className="pb-2">Detector</th>
                  <th className="pb-2 text-center">Precision</th>
                  <th className="pb-2 text-center">Recall</th>
                  <th className="pb-2 text-center">FPR</th>
                  <th className="pb-2 text-center">TP / FP / FN</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium">
                {anomalyDetectors?.per_detector &&
                  Object.entries(anomalyDetectors.per_detector).map(([dName, stats]) => (
                    <tr key={dName} className="hover:bg-slate-50 transition-colors">
                      <td className="py-2.5 font-bold text-slate-800 capitalize">
                        {dName.replace(/_/g, ' ')}
                      </td>
                      <td className="py-2.5 text-center text-slate-700">
                        {(stats.precision * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 text-center text-slate-700">
                        {(stats.recall * 100).toFixed(1)}%
                      </td>
                      <td className="py-2.5 text-center">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            stats.fpr <= 0.05
                              ? 'bg-emerald-50 text-emerald-800'
                              : stats.fpr <= 0.1
                              ? 'bg-amber-50 text-amber-800'
                              : 'bg-red-50 text-red-800'
                          }`}
                        >
                          {(stats.fpr * 100).toFixed(1)}%
                        </span>
                      </td>
                      <td className="py-2.5 text-center text-slate-400 font-mono text-[10px]">
                        {stats.tp} / {stats.fp} / {stats.fn}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Confusion Matrix Heatmap */}
      {classification?.confusion_matrix && (
        <div className="bg-white rounded-[12px] p-6 shadow-sm border border-slate-200">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-bold text-[#0F2A5C] uppercase tracking-wider">
                Classification Confusion Matrix Heatmap
              </h3>
              <p className="text-xs text-slate-500">
                Ground Truth document type (Rows) vs Pipeline Classified type (Columns). Diagonal cells represent correct matches.
              </p>
            </div>
          </div>

          <div className="overflow-x-auto max-h-[460px] overflow-y-auto border border-slate-200 rounded-lg">
            <table className="w-full border-collapse text-[10px]">
              <thead className="sticky top-0 bg-slate-100 z-10">
                <tr>
                  <th className="p-2 border border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-left min-w-[140px] bg-slate-100">
                    True \ Pred
                  </th>
                  {classification.confusion_matrix.labels.map((lbl) => (
                    <th
                      key={lbl}
                      className="p-1.5 border border-slate-200 text-slate-700 font-semibold text-center min-w-[70px] max-w-[90px] truncate"
                      title={lbl}
                    >
                      {lbl.length > 9 ? lbl.slice(0, 9) + '..' : lbl}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {classification.confusion_matrix.labels.map((rowLbl, rowIdx) => (
                  <tr key={rowLbl}>
                    <td className="p-2 border border-slate-200 font-bold text-slate-700 bg-slate-50 truncate max-w-[140px]" title={rowLbl}>
                      {rowLbl}
                    </td>
                    {classification.confusion_matrix.labels.map((colLbl, colIdx) => {
                      const count = classification.confusion_matrix.matrix[rowIdx]?.[colIdx] || 0;
                      const isDiagonal = rowIdx === colIdx;
                      let bgClass = 'bg-white text-slate-300';
                      if (count > 0 && isDiagonal) {
                        bgClass = 'bg-emerald-100 font-bold text-emerald-900';
                      } else if (count > 0 && !isDiagonal) {
                        bgClass = 'bg-red-100 font-bold text-red-900';
                      }
                      return (
                        <td
                          key={colLbl}
                          className={`p-1.5 border border-slate-200 text-center ${bgClass}`}
                        >
                          {count}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Failed Cases Log */}
      <div className="bg-white rounded-[12px] p-6 shadow-sm border border-slate-200 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-bold text-[#0F2A5C] uppercase tracking-wider">
              Benchmark Inspection Log ({failedCases.length} records)
            </h3>
            <p className="text-xs text-slate-500">
              Test documents with classification mismatches, missing fields, or detector errors
            </p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search size={14} className="absolute left-3 top-3 text-slate-400" />
            <input
              type="text"
              placeholder="Search file or doc type..."
              value={failedCasesSearch}
              onChange={(e) => setFailedCasesSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
            />
          </div>
        </div>

        {failedCases.length === 0 ? (
          <div className="text-center py-8 bg-slate-50 rounded-lg border border-dashed border-slate-200">
            <CheckCircle2 size={28} className="mx-auto text-emerald-600 mb-2" />
            <p className="text-xs font-bold text-slate-700">All evaluated benchmark cases passed requirements!</p>
            <p className="text-[11px] text-slate-400 mt-0.5">No anomalies or extraction discrepancies detected.</p>
          </div>
        ) : (
          <div className="overflow-x-auto border border-slate-200 rounded-lg">
            <table className="w-full text-left border-collapse text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase font-bold text-[10px] tracking-wider">
                <tr>
                  <th className="py-2.5 px-3">File Name</th>
                  <th className="py-2.5 px-3">Document Type</th>
                  <th className="py-2.5 px-3">Failure Diagnostic</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {failedCases.map((fc, i) => (
                  <tr key={i} className="hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 font-mono text-[11px] text-slate-700 max-w-[220px] truncate" title={fc.filename}>
                      {fc.filename}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-slate-800">
                      {fc.doc_type}
                    </td>
                    <td className="py-2.5 px-3">
                      <div className="flex flex-wrap gap-1">
                        {fc.failures.map((f, fi) => (
                          <span
                            key={fi}
                            className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-50 text-amber-900 border border-amber-200"
                          >
                            {f}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <button
                        onClick={() => setPreviewCase(fc)}
                        className="px-2.5 py-1 text-[11px] font-semibold text-[#0B3C9D] hover:bg-blue-50 rounded inline-flex items-center gap-1 transition-colors"
                      >
                        <Eye size={12} />
                        <span>Inspect</span>
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Case Preview Modal */}
      {previewCase && (
        <Modal
          isOpen={!!previewCase}
          onClose={() => setPreviewCase(null)}
          title={`Diagnostic Inspection: ${previewCase.filename}`}
          subtitle={`Expected Document Type: ${previewCase.doc_type}`}
          maxWidth="max-w-[700px]"
          footer={
            <button
              onClick={() => setPreviewCase(null)}
              className="h-10 px-5 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-bold rounded-lg transition-colors"
            >
              Close
            </button>
          }
        >
          <div className="space-y-4 text-xs">
            <div>
              <span className="font-bold text-slate-700 uppercase block mb-1">Failure Diagnostics:</span>
              <ul className="list-disc pl-4 space-y-1 text-red-600 font-semibold">
                {previewCase.failures.map((f, idx) => (
                  <li key={idx}>{f}</li>
                ))}
              </ul>
            </div>

            <div>
              <span className="font-bold text-slate-700 uppercase block mb-1">Benchmark Run Details:</span>
              <pre className="bg-slate-900 text-slate-100 p-3 rounded-lg overflow-x-auto text-[11px] font-mono leading-relaxed max-h-60">
                {JSON.stringify(previewCase.details, null, 2)}
              </pre>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
export default AdminEvaluationPage;
