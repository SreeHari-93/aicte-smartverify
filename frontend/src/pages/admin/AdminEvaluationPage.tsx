import React, { useState, useEffect, useRef } from 'react';
import {
  RefreshCw,
  CheckCircle2,
  Play,
  Check,
  AlertTriangle,
  History,
  TrendingUp,
  TrendingDown,
  Minus,
  Clock,
  RotateCcw,
} from 'lucide-react';
import { apiClient } from '../../api/client';
import { DataTable, ColumnDef } from '../../components/DataTable';

interface ScenarioItem {
  dimension: string;
  score: number;
  unit: string;
  status: 'PASSED' | 'FAILED' | 'WARNING';
  details: string;
  failure_reason?: string | null;
  test_cases: string[];
}

interface RecentRunItem {
  id: number;
  evaluated_at: string;
  overall_result: number;
  duration_seconds: number;
  status: string;
}

interface EvaluationResponse {
  id: number;
  overall_accuracy: number;
  note: string;
  evaluated_at: string;
  duration_seconds: number;
  scenarios: ScenarioItem[];
  previous_run?: {
    id: number;
    overall_accuracy: number;
    evaluated_at: string;
    dimension_scores: Record<string, number>;
  } | null;
  recent_runs: RecentRunItem[];
  active_run?: {
    id: number;
    status: string;
    progress_step: number;
    progress_total: number;
    progress_text: string;
  } | null;
}

const getPlainDimensionName = (name: string): string => {
  const n = name.toLowerCase();
  if (n.includes('routing')) return 'Routing accuracy';
  if (n.includes('deadline')) return 'Deadline accuracy';
  if (n.includes('timeliness')) return 'Alert timeliness';
  if (n.includes('duplicate')) return 'Duplicate alerts';
  if (n.includes('escalation correctness') || n.includes('escalation accuracy') || n.includes('escalation')) return 'Escalation accuracy';
  if (n.includes('audit')) return 'Audit completeness';
  if (n.includes('return') || n.includes('resubmit')) return 'Return and resubmit';
  if (n.includes('late renewal') || n.includes('renewal')) return 'Renewal escalation';
  return name;
};

const formatPlainWording = (text: string): string => {
  if (!text) return '';
  return text
    .replace(/STAGE_DUE_SOON/g, 'Stage due soon')
    .replace(/UNDERTAKING_DUE_SOON/g, 'Undertaking due soon')
    .replace(/DOCUMENT_EXPIRING/g, 'Document expiring')
    .replace(/T-90/g, '90 days before')
    .replace(/T-60/g, '60 days before')
    .replace(/T-30/g, '30 days before')
    .replace(/T-7/g, '7 days before')
    .replace(/T-2/g, '2 days before')
    .replace(/SCRUTINY_EVC/g, 'Scrutiny + EVC')
    .replace(/ONLY_SCRUTINY/g, 'Scrutiny only')
    .replace(/ONLY_EVC/g, 'EVC only')
    .replace(/EVC_SAC_SHC/g, 'EVC + SAC / SHC review')
    .replace(/\b3d\b/g, '3 days')
    .replace(/\b7d\b/g, '7 days')
    .replace(/\b14d\b/g, '14 days');
};

const formatDateTime = (isoString?: string): string => {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const mins = String(d.getMinutes()).padStart(2, '0');
    return `${day}-${month}-${year} ${hours}:${mins}`;
  } catch {
    return isoString;
  }
};

export const AdminEvaluationPage: React.FC = () => {
  const [evalData, setEvalData] = useState<EvaluationResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRunning, setIsRunning] = useState(false);
  const [progressText, setProgressText] = useState<string>('');
  const [errorReason, setErrorReason] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  };

  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, []);

  const loadEvaluation = async () => {
    setIsLoading(true);
    setErrorReason(null);
    try {
      const res = await apiClient.get<EvaluationResponse>('/api/evaluation/synthetic-scenarios');
      const data = res.data;
      setEvalData(data);

      // If a run is actively executing on the server, resume polling
      if (data.active_run && data.active_run.status === 'RUNNING') {
        setIsRunning(true);
        setProgressText(data.active_run.progress_text || 'Checking scenarios...');
        startPolling();
      } else {
        setIsRunning(false);
        setProgressText('');
        stopPolling();
      }
    } catch (err: any) {
      console.error('Failed to load evaluation results:', err);
      setErrorReason(err.response?.data?.detail || err.message || 'Failed to load evaluation metrics.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadEvaluation();
  }, []);

  const startPolling = () => {
    stopPolling();
    pollIntervalRef.current = setInterval(async () => {
      try {
        const res = await apiClient.get<EvaluationResponse>('/api/evaluation/synthetic-scenarios');
        const data = res.data;

        if (data.active_run && data.active_run.status === 'RUNNING') {
          setProgressText(data.active_run.progress_text || 'Checking scenarios...');
        } else {
          // Completed
          stopPolling();
          setEvalData(data);
          setIsRunning(false);
          setProgressText('');
          setSuccessToast('Evaluation complete');
          setTimeout(() => setSuccessToast(null), 4000);
        }
      } catch (err: any) {
        console.error('Polling error:', err);
        stopPolling();
        setIsRunning(false);
        setErrorReason(err.response?.data?.detail || err.message || 'Error occurred while checking evaluation run.');
      }
    }, 1000);
  };

  const handleRunEvaluation = async () => {
    if (isRunning) return; // Prevent double trigger
    setIsRunning(true);
    setErrorReason(null);
    setProgressText('Initiating evaluation suite...');

    try {
      const res = await apiClient.post('/api/evaluation/trigger-scenarios');
      const data = res.data;

      if (data.active_run) {
        setProgressText(data.active_run.progress_text || 'Checking scenario 1 of 8...');
      }

      startPolling();
    } catch (err: any) {
      console.error('Trigger evaluation error:', err);
      setIsRunning(false);
      setProgressText('');
      setErrorReason(err.response?.data?.detail || err.message || 'Failed to re-run evaluation suite.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Evaluation
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Benchmark accuracy across workflow scenarios.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRunEvaluation}
            disabled={isRunning}
            className="flex items-center gap-2 px-4 py-2 bg-[#0B3C9D] hover:bg-[#082b70] text-white text-xs font-bold rounded-lg shadow-sm transition-colors disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed"
          >
            <Play size={14} className={isRunning ? 'animate-spin' : ''} />
            <span>{isRunning ? 'Running…' : 'Re-run evaluation'}</span>
          </button>

          <button
            onClick={loadEvaluation}
            disabled={isLoading || isRunning}
            className="flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 text-xs font-semibold rounded-lg shadow-xs disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Live Run Progress Banner */}
      {isRunning && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 shadow-sm flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin shrink-0" />
            <div>
              <span className="text-xs font-bold text-blue-900 block">
                Evaluation in progress
              </span>
              <span className="text-xs text-blue-700 font-medium">
                {progressText || 'Checking scenarios...'}
              </span>
            </div>
          </div>
          <span className="text-[11px] font-semibold text-blue-600 bg-blue-100 px-2.5 py-1 rounded-md">
            Background job active
          </span>
        </div>
      )}

      {/* Success Notification */}
      {successToast && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl p-4 shadow-sm flex items-center gap-2.5 text-xs font-semibold animate-in fade-in duration-200">
          <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Failure Error Alert with Retry Button */}
      {errorReason && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle size={18} className="text-red-600 shrink-0" />
            <div>
              <span className="text-xs font-bold text-red-900 block">
                Evaluation run failed
              </span>
              <span className="text-xs text-red-700">{errorReason}</span>
            </div>
          </div>
          <button
            onClick={handleRunEvaluation}
            disabled={isRunning}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-bold rounded-lg shadow-sm transition-colors"
          >
            <RotateCcw size={13} />
            <span>Retry</span>
          </button>
        </div>
      )}

      {/* Primary Benchmark Score Banner */}
      {evalData && (
        <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-6">
          <div className="space-y-2">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
              {evalData.overall_accuracy}% overall accuracy
            </h2>
            <p className="text-xs text-slate-600 max-w-xl leading-relaxed">
              Scripted scenarios based on the stage rules in this system.
            </p>
            <div className="pt-1 flex items-center gap-2 flex-wrap">
              <span className="text-[11px] font-semibold text-slate-700 bg-slate-100 px-3 py-1 rounded-md border border-slate-200">
                {evalData.note || 'Measured on synthetic scenarios.'}
              </span>
              {evalData.duration_seconds > 0 && (
                <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200">
                  <Clock size={12} />
                  <span>Duration: {evalData.duration_seconds}s</span>
                </span>
              )}
            </div>
          </div>

          <div className="text-right sm:border-l sm:border-slate-200 sm:pl-8 space-y-1">
            <span className="text-xs text-slate-600 block font-medium">
              Evaluated at
            </span>
            <span className="text-sm font-mono font-bold text-slate-900 block">
              {formatDateTime(evalData.evaluated_at)}
            </span>
            <div className="text-[11px] text-emerald-600 font-medium flex items-center justify-end gap-1 pt-1">
              <CheckCircle2 size={13} />
              <span>
                {evalData.overall_accuracy === 100
                  ? 'Zero regressions'
                  : `${evalData.scenarios.filter((s) => s.status === 'PASSED').length} of ${evalData.scenarios.length} passed`}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Scenario Dimension Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {evalData?.scenarios.map((sc, idx) => {
          const isPassed = sc.status === 'PASSED';
          const plainTitle = getPlainDimensionName(sc.dimension);

          // Previous run score comparison
          const prevScore = evalData.previous_run?.dimension_scores?.[sc.dimension];
          const hasPrev = prevScore !== undefined && prevScore !== null;
          const scoreDiff = hasPrev ? sc.score - prevScore : 0;

          return (
            <div
              key={idx}
              className={`bg-white rounded-xl border p-5 shadow-sm flex flex-col justify-between space-y-4 transition-all ${
                isPassed ? 'border-slate-200 hover:border-[#0B3C9D]' : 'border-red-300 ring-1 ring-red-200 bg-red-50/10'
              }`}
            >
              <div className="space-y-2.5">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-sm font-bold text-slate-900 leading-snug">
                    {plainTitle}
                  </h3>
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold border shrink-0 ${
                      isPassed
                        ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                        : 'bg-red-100 text-red-800 border-red-200 font-bold'
                    }`}
                  >
                    {isPassed ? 'Passed' : 'Failed'}
                  </span>
                </div>

                <div className="flex items-baseline gap-1.5 flex-wrap">
                  <span className="text-2xl font-bold text-[#0B3C9D]">{sc.score}</span>
                  <span className="text-xs font-semibold text-slate-600">{sc.unit}</span>

                  {/* Previous run marker */}
                  {hasPrev && (
                    <span className="ml-auto text-[11px] font-medium flex items-center gap-1 text-slate-500">
                      <span>Prev: {prevScore}{sc.unit}</span>
                      {scoreDiff > 0 ? (
                        <span className="text-emerald-700 flex items-center font-bold" title={`Increased by ${scoreDiff.toFixed(1)}`}>
                          <TrendingUp size={12} />
                          <span>+{scoreDiff.toFixed(1)}</span>
                        </span>
                      ) : scoreDiff < 0 ? (
                        <span className="text-red-700 flex items-center font-bold" title={`Decreased by ${Math.abs(scoreDiff).toFixed(1)}`}>
                          <TrendingDown size={12} />
                          <span>{scoreDiff.toFixed(1)}</span>
                        </span>
                      ) : (
                        <span className="text-slate-400 flex items-center" title="Unchanged">
                          <Minus size={11} />
                        </span>
                      )}
                    </span>
                  )}
                </div>

                {/* Failure Reason Callout */}
                {!isPassed && sc.failure_reason && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-2.5 text-xs text-red-800 font-medium leading-relaxed">
                    <span className="font-bold block text-red-900 mb-0.5">Failure reason:</span>
                    {formatPlainWording(sc.failure_reason)}
                  </div>
                )}

                <p className="text-xs text-slate-600 leading-relaxed">
                  {formatPlainWording(sc.details)}
                </p>
              </div>

              {/* Scenario Checks List */}
              <div className="pt-3 border-t border-slate-100 space-y-1.5">
                <span className="text-[11px] font-semibold text-slate-700 block">
                  Scenario checks
                </span>
                {sc.test_cases.map((tc, cIdx) => (
                  <div key={cIdx} className="flex items-start gap-1.5 text-[11px] text-slate-700">
                    <Check size={12} className="text-emerald-600 shrink-0 mt-0.5" />
                    <span className="leading-tight">{formatPlainWording(tc)}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Recent Evaluation Runs List */}
      {evalData && evalData.recent_runs && evalData.recent_runs.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-3">
          <div className="flex items-center gap-2">
            <History size={16} className="text-slate-600" />
            <h3 className="text-sm font-bold text-slate-900">
              Recent evaluation runs
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {evalData.recent_runs.map((r, rIdx) => {
              const isCurrent = r.id === evalData.id;
              const isComp = r.status === 'COMPLETED';
              return (
                <div
                  key={r.id || rIdx}
                  className={`p-3 rounded-lg border text-xs space-y-1.5 ${
                    isCurrent ? 'bg-blue-50/60 border-blue-200 ring-1 ring-blue-100' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-slate-800">
                      Run #{r.id} {isCurrent && '(Latest)'}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                        isComp ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                      }`}
                    >
                      {isComp ? 'Completed' : 'Failed'}
                    </span>
                  </div>
                  <div className="flex items-baseline justify-between pt-1">
                    <span className="font-bold text-slate-900 text-sm">{r.overall_result}%</span>
                    <span className="text-[11px] text-slate-500 font-mono">{r.duration_seconds}s</span>
                  </div>
                  <span className="text-[10px] text-slate-500 block truncate" title={formatDateTime(r.evaluated_at)}>
                    {formatDateTime(r.evaluated_at)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Detailed Evaluation Verification Table */}
      {evalData && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Evaluation verification details
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Synthetic scenarios, verification matrices, and automated benchmark validations.
              </p>
            </div>
          </div>

          <div>
            {(() => {
              const columns: ColumnDef<ScenarioItem>[] = [
                {
                  key: 'dimension',
                  header: 'Dimension',
                  width: '24%',
                  align: 'left',
                  sticky: true,
                  render: (sc) => (
                    <div>
                      <span className="font-semibold text-slate-900 text-xs block">
                        {getPlainDimensionName(sc.dimension)}
                      </span>
                      <span className="text-[11px] text-slate-500 block mt-0.5">
                        {sc.dimension}
                      </span>
                    </div>
                  ),
                },
                {
                  key: 'score',
                  header: 'Metric score',
                  width: '18%',
                  align: 'left',
                  render: (sc) => {
                    const prevScore = evalData.previous_run?.dimension_scores?.[sc.dimension];
                    const hasPrev = prevScore !== undefined && prevScore !== null;
                    const diff = hasPrev ? sc.score - prevScore : 0;
                    return (
                      <div>
                        <div className="flex items-baseline gap-1">
                          <span className="font-bold text-[#0B3C9D] text-sm">{sc.score}</span>
                          <span className="text-xs text-slate-600">{sc.unit}</span>
                        </div>
                        {hasPrev && (
                          <span className="text-[10px] text-slate-500 block mt-0.5">
                            Prev: {prevScore}{sc.unit} ({diff > 0 ? `+${diff.toFixed(1)}` : diff < 0 ? diff.toFixed(1) : '—'})
                          </span>
                        )}
                      </div>
                    );
                  },
                },
                {
                  key: 'details',
                  header: 'Evaluation details',
                  width: '32%',
                  align: 'left',
                  render: (sc) => (
                    <div>
                      <span className="text-xs text-slate-700 leading-relaxed block line-clamp-2" title={formatPlainWording(sc.details)}>
                        {formatPlainWording(sc.details)}
                      </span>
                      {sc.status === 'FAILED' && sc.failure_reason && (
                        <span className="text-[11px] text-red-700 font-semibold block mt-1">
                          ⚠️ {formatPlainWording(sc.failure_reason)}
                        </span>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'checks',
                  header: 'Validation checks',
                  width: '16%',
                  align: 'left',
                  render: (sc) => (
                    <div className="text-[11px] text-slate-600 space-y-1">
                      <span className="font-medium text-emerald-700 block">
                        {sc.test_cases.length} check(s) passed
                      </span>
                    </div>
                  ),
                },
                {
                  key: 'status',
                  header: 'Status',
                  width: '10%',
                  align: 'left',
                  render: (sc) => (
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                        sc.status === 'PASSED'
                          ? 'bg-emerald-100 text-emerald-800 border-emerald-200'
                          : 'bg-red-100 text-red-800 border-red-200 font-bold'
                      }`}
                    >
                      {sc.status === 'PASSED' ? 'Passed' : 'Failed'}
                    </span>
                  ),
                },
              ];

              return (
                <DataTable
                  columns={columns}
                  data={evalData.scenarios}
                  keyExtractor={(sc, i) => sc.dimension || i}
                  isLoading={isLoading}
                  emptyMessage="No evaluation data found."
                  isWide={true}
                />
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
};
