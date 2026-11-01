import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getAlertTarget, canUserAccessAlert } from '../../utils/alertRouting';
import {
  Bell,
  Clock,
  RefreshCw,
  Sliders,
  TrendingUp,
  History,
  Play,
  CheckCircle2,
  AlertTriangle,
  ExternalLink,
  Calendar,
  Edit2,
  Check,
  Search,
  Filter,
} from 'lucide-react';
import {
  alertsApi,
  AlertItem,
  NotificationRuleItem,
  EscalationMatrixItem,
  EscalationRecordItem,
  SchedulerLogItem,
  DemoClockStatus,
} from '../../api/alerts';
import { Modal } from '../../components/Modal';
import { DataTable, ColumnDef } from '../../components/DataTable';

export const AdminAlertsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'feed' | 'rules' | 'matrix' | 'history' | 'scheduler'>('feed');
  const { user } = useAuth();
  const navigate = useNavigate();
  const [accessDeniedAlertId, setAccessDeniedAlertId] = useState<number | null>(null);

  const handleOpenCase = async (alertItem: AlertItem, ids?: number[]) => {
    if (!canUserAccessAlert(alertItem, user)) {
      setAccessDeniedAlertId(alertItem.id);
      return;
    }
    setAccessDeniedAlertId(null);
    const idsToMark = ids && ids.length > 0 ? ids : [alertItem.id];
    try {
      await handleMarkRead(idsToMark);
    } catch {
      // quiet fallback
    }
    const target = getAlertTarget(alertItem, user?.role);
    navigate(target);
  };
  const [isLoading, setIsLoading] = useState(true);

  // Data states
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [rules, setRules] = useState<NotificationRuleItem[]>([]);
  const [matrix, setMatrix] = useState<EscalationMatrixItem[]>([]);
  const [escalations, setEscalations] = useState<EscalationRecordItem[]>([]);
  const [schedulerLogs, setSchedulerLogs] = useState<SchedulerLogItem[]>([]);
  const [demoClock, setDemoClock] = useState<DemoClockStatus | null>(null);

  // Filters
  const [filterType, setFilterType] = useState<string>('ALL');
  const [filterSearch, setFilterSearch] = useState<string>('');
  const [filterUnread, setFilterUnread] = useState<boolean>(false);

  // Editing Rule modal state
  const [editingRule, setEditingRule] = useState<NotificationRuleItem | null>(null);
  const [ruleTitle, setRuleTitle] = useState('');
  const [ruleTemplate, setRuleTemplate] = useState('');
  const [ruleOffsets, setRuleOffsets] = useState<string>('');
  const [ruleChannel, setRuleChannel] = useState<string>('BOTH');
  const [ruleRole, setRuleRole] = useState<string>('INSTITUTE');
  const [ruleEnabled, setRuleEnabled] = useState<boolean>(true);
  const [ruleSaveError, setRuleSaveError] = useState<string | null>(null);

  // Demo Clock input
  const [simulatedDateInput, setSimulatedDateInput] = useState<string>('2026-11-15T10:00');
  const [isSettingClock, setIsSettingClock] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  const loadAllData = async () => {
    setIsLoading(true);
    try {
      const [alRes, rRes, mRes, escRes, logRes, clkRes] = await Promise.all([
        alertsApi.getAlerts({ limit: 100 }),
        alertsApi.getRules(),
        alertsApi.getEscalationMatrix(),
        alertsApi.getEscalationRecords(),
        alertsApi.getSchedulerLogs(),
        alertsApi.getDemoClock(),
      ]);
      setAlerts(alRes.items || []);
      setRules(rRes || []);
      setMatrix(mRes || []);
      setEscalations(escRes || []);
      setSchedulerLogs(logRes || []);
      setDemoClock(clkRes || null);
    } catch (err) {
      console.error('Failed to load alert data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleRunScanner = async () => {
    setIsScanning(true);
    setScanMessage(null);
    try {
      const res = await alertsApi.triggerSchedulerScan();
      setScanMessage(
        `Scheduler scan finished! Checked ${res.items_checked} items, created ${res.alerts_created} new alerts, ${res.escalations_triggered} escalations in ${res.duration_ms}ms.`
      );
      await loadAllData();
    } catch (err: any) {
      setScanMessage(`Scanner error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  const handleSetDemoClock = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSettingClock(true);
    try {
      await alertsApi.setDemoClock(simulatedDateInput);
      window.dispatchEvent(new Event('demo-clock-updated'));
      await loadAllData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to set demo clock.');
    } finally {
      setIsSettingClock(false);
    }
  };

  const handleResetDemoClock = async () => {
    if (!window.confirm('Reset simulated demonstration clock back to real system time?')) return;
    try {
      await alertsApi.resetDemoClock();
      window.dispatchEvent(new Event('demo-clock-updated'));
      await loadAllData();
    } catch (err: any) {
      alert('Failed to reset demo clock.');
    }
  };

  const handleMarkRead = async (ids: number[]) => {
    try {
      await Promise.all(ids.map((id) => alertsApi.markAlertRead(id)));
      setAlerts((prev) => prev.map((a) => (ids.includes(a.id) ? { ...a, is_read: true } : a)));
    } catch (err) {
      console.error(err);
    }
  };

  const formatDDMMYYYY = (iso?: string | null) => {
    if (!iso) return 'N/A';
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return iso;
      const dd = String(d.getDate()).padStart(2, '0');
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const yyyy = d.getFullYear();
      return `${dd}-${mm}-${yyyy}`;
    } catch {
      return iso;
    }
  };

  const formatOffsetLabel = (offset: number) => {
    if (offset > 0) return `${offset} days before due`;
    if (offset === 0) return 'On due date';
    return `${Math.abs(offset)} days overdue`;
  };

  const openRuleEditor = (r: NotificationRuleItem) => {
    setEditingRule(r);
    setRuleTitle(r.title);
    setRuleTemplate(r.message_template);
    setRuleOffsets(r.offsets_days.join(', '));
    setRuleChannel(r.channel);
    setRuleRole(r.recipient_role);
    setRuleEnabled(r.is_enabled);
    setRuleSaveError(null);
  };

  const handleSaveRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingRule) return;

    // Check inflammatory terms
    const forbidden = ['forgery', 'fraud', 'misconduct'];
    const combined = (ruleTitle + ' ' + ruleTemplate).toLowerCase();
    for (const f of forbidden) {
      if (combined.includes(f)) {
        setRuleSaveError(`Forbidden word detected: '${f}' is strictly prohibited in communications.`);
        return;
      }
    }

    const parsedOffsets = ruleOffsets
      .split(',')
      .map((s) => parseInt(s.trim()))
      .filter((n) => !isNaN(n));

    try {
      await alertsApi.updateRule(editingRule.id, {
        title: ruleTitle,
        message_template: ruleTemplate,
        offsets_days: parsedOffsets,
        channel: ruleChannel,
        recipient_role: ruleRole,
        is_enabled: ruleEnabled,
      });
      setEditingRule(null);
      await loadAllData();
    } catch (err: any) {
      setRuleSaveError(err.response?.data?.detail || 'Failed to update rule.');
    }
  };

  // Filtered alerts
  const filteredAlerts = alerts.filter((a) => {
    if (filterType !== 'ALL' && a.event_type !== filterType) return false;
    if (filterUnread && a.is_read) return false;
    if (filterSearch) {
      const q = filterSearch.toLowerCase();
      const match =
        a.case_id.toLowerCase().includes(q) ||
        a.title.toLowerCase().includes(q) ||
        a.message.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  // Grouped filtered alerts for deduplication
  const groupedAlerts = React.useMemo(() => {
    const groups: { [key: string]: { primary: AlertItem; count: number; ids: number[]; hasUnread: boolean } } = {};
    const order: string[] = [];

    for (const a of filteredAlerts) {
      const key = a.case_id ? `${a.event_type}__${a.case_id}` : `alert_${a.id}`;
      if (!groups[key]) {
        groups[key] = { primary: a, count: 1, ids: [a.id], hasUnread: !a.is_read };
        order.push(key);
      } else {
        groups[key].count += 1;
        groups[key].ids.push(a.id);
        if (!a.is_read) groups[key].hasUnread = true;
        if (new Date(a.created_at || 0).getTime() > new Date(groups[key].primary.created_at || 0).getTime()) {
          groups[key].primary = a;
        }
      }
    }

    return order.map((k) => groups[k]);
  }, [filteredAlerts]);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Alerts
          </h1>
          <p className="text-xs text-slate-600 mt-0.5">
            Reminders and escalation matrix.
          </p>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            onClick={handleRunScanner}
            disabled={isScanning}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-[#0B3C9D] hover:bg-[#082b70] text-white text-xs font-medium rounded-md shadow-sm transition-colors cursor-pointer"
          >
            <Play size={14} className={isScanning ? 'animate-spin' : ''} />
            <span>{isScanning ? 'Running scan...' : 'Run check now'}</span>
          </button>

          <button
            onClick={loadAllData}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-1.5 bg-white border border-slate-300 hover:border-slate-400 text-slate-800 text-xs font-medium rounded-md shadow-sm cursor-pointer transition-colors"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Demo Clock Card */}
      <div className="bg-white border border-slate-200 rounded-lg p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Clock size={18} className="text-slate-500 shrink-0" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-semibold text-slate-800">
                Demo clock: {demoClock?.is_active ? 'Simulated' : 'Real-time'}
              </h3>
              {demoClock?.is_active && (
                <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-amber-100 text-amber-800">
                  Active
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Effective date:{' '}
              <span className="font-mono font-medium text-slate-700">
                {demoClock?.effective_time ? formatDDMMYYYY(demoClock.effective_time) : '—'}
              </span>
            </p>
          </div>
        </div>

        <form onSubmit={handleSetDemoClock} className="flex items-center gap-2">
          <input
            type="datetime-local"
            value={simulatedDateInput}
            onChange={(e) => setSimulatedDateInput(e.target.value)}
            className="text-xs px-3 py-1.5 rounded-md border border-slate-300 bg-white text-slate-800 font-mono shadow-xs focus:ring-1 focus:ring-[#0B3C9D] outline-none"
          />
          <button
            type="submit"
            disabled={isSettingClock}
            className="px-3.5 py-1.5 bg-[#0B3C9D] hover:bg-[#082B70] text-white text-xs font-medium rounded-md shadow-sm transition-colors cursor-pointer"
          >
            Apply
          </button>
          {demoClock?.is_active && (
            <button
              type="button"
              onClick={handleResetDemoClock}
              className="px-3.5 py-1.5 bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-xs font-medium rounded-md shadow-sm transition-colors cursor-pointer"
            >
              Reset
            </button>
          )}
        </form>
      </div>

      {scanMessage && (
        <div className="p-3.5 bg-blue-50 border border-blue-200 text-blue-900 rounded-xl text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-blue-600 shrink-0" />
            <span>{scanMessage}</span>
          </div>
          <button onClick={() => setScanMessage(null)} className="text-blue-500 hover:text-blue-700 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Tab Navigation inside solid white card */}
      <div className="bg-white rounded-lg p-1.5 border border-slate-200 shadow-sm flex flex-wrap gap-2">
        {[
          { id: 'feed', label: `Alerts (${alerts.length})`, icon: Bell },
          { id: 'rules', label: `Notification rules (${rules.length})`, icon: Sliders },
          { id: 'matrix', label: `Escalation matrix (${matrix.length})`, icon: TrendingUp },
          { id: 'history', label: `Escalation history (${escalations.length})`, icon: History },
          { id: 'scheduler', label: `Scheduler log (${schedulerLogs.length})`, icon: Calendar },
        ].map((t) => {
          const Icon = t.icon;
          const isActive = activeTab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id as any)}
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-xs font-medium transition-colors cursor-pointer ${
                isActive
                  ? 'bg-[#0B3C9D] text-white'
                  : 'bg-white text-slate-600 hover:bg-slate-50 border border-transparent'
              }`}
            >
              <Icon size={14} className={isActive ? 'text-white' : 'text-slate-500'} />
              <span>{t.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB 1: ALERTS FEED */}
      {activeTab === 'feed' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="bg-white rounded-lg p-4 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-3 flex-wrap">
              <div className="relative">
                <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
                <input
                  type="text"
                  placeholder="Filter by case or title..."
                  value={filterSearch}
                  onChange={(e) => setFilterSearch(e.target.value)}
                  className="pl-8 pr-3 py-1.5 rounded-md border border-slate-300 w-64 focus:border-[#0B3C9D] outline-none text-xs"
                />
              </div>

              <div className="flex items-center gap-1.5">
                <Filter size={14} className="text-slate-500" />
                <select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                  className="px-3 py-1.5 rounded-md border border-slate-300 bg-white font-normal text-xs"
                >
                  <option value="ALL">All event types</option>
                  <option value="STAGE_DUE_SOON">Stage due soon</option>
                  <option value="STAGE_OVERDUE">Stage overdue</option>
                  <option value="EVC_PENDING_SCHEDULING">EVC pending scheduling</option>
                  <option value="EVC_SCHEDULING_OVERDUE">EVC scheduling overdue</option>
                  <option value="VISIT_APPROACHING">Visit approaching</option>
                  <option value="VISIT_COMPLETED_REPORT_PENDING">Visit report pending</option>
                  <option value="UNDERTAKING_DUE_SOON">Undertaking due soon</option>
                  <option value="UNDERTAKING_OVERDUE">Undertaking overdue</option>
                  <option value="DOCUMENT_EXPIRING">Document expiring</option>
                  <option value="DOCUMENT_EXPIRED">Document expired</option>
                  <option value="RENEWAL_PENDING">Renewal pending</option>
                </select>
              </div>

              <label className="flex items-center gap-2 cursor-pointer text-slate-600 font-normal">
                <input
                  type="checkbox"
                  checked={filterUnread}
                  onChange={(e) => setFilterUnread(e.target.checked)}
                  className="rounded text-[#0B3C9D]"
                />
                <span>Unread only</span>
              </label>
            </div>

            <span className="text-slate-500 font-normal">
              Showing {groupedAlerts.length} groups ({filteredAlerts.length} total)
            </span>
          </div>

          {/* Alert Feed Items */}
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm divide-y divide-slate-100">
            {groupedAlerts.length === 0 ? (
              <div className="py-14 text-center text-slate-600">
                <p className="text-sm font-medium text-slate-600">No alerts found</p>
                <p className="text-xs text-slate-600 mt-1">Try adjusting your filters or click Run check now.</p>
              </div>
            ) : (
              groupedAlerts.map((item) => {
                const a = item.primary;
                return (
                  <div
                    key={a.id}
                    className={`p-4 transition-colors flex items-start justify-between gap-4 ${
                      item.hasUnread ? 'bg-orange-50/50 hover:bg-orange-50/80' : 'hover:bg-slate-50/80'
                    }`}
                  >
                    <div className="flex items-start gap-3.5">
                      <div
                        className={`p-2.5 rounded-lg shrink-0 mt-0.5 ${
                          a.event_type.includes('OVERDUE') || a.event_type.includes('EXPIRED')
                            ? 'bg-red-100 text-red-700'
                            : 'bg-blue-100 text-[#0B3C9D]'
                        }`}
                      >
                        {a.event_type.includes('OVERDUE') || a.event_type.includes('EXPIRED') ? (
                          <AlertTriangle size={18} />
                        ) : (
                          <Bell size={18} />
                        )}
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-bold text-slate-900">{a.title}</span>
                          {item.count > 1 && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-black bg-[#E8650A] text-white">
                              ×{item.count}
                            </span>
                          )}
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-800 border border-slate-200 font-mono">
                            {a.case_id}
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-[#0B3C9D] border border-blue-200">
                            {a.recipient_role}
                          </span>
                          <span className="text-[10px] font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                            {formatOffsetLabel(a.offset_days)}
                          </span>
                          {item.hasUnread && (
                            <span className="w-2 h-2 rounded-full bg-red-500 shrink-0" title="Unread" />
                          )}
                        </div>

                        <p className="text-xs text-slate-800 leading-relaxed whitespace-pre-line max-w-3xl font-medium">
                          {a.message}
                        </p>

                        <div className="flex items-center gap-3 text-[11px] text-slate-600 font-medium pt-1">
                          <span>Logged: {formatDDMMYYYY(a.created_at)}</span>
                          {a.due_date && <span>Target Due: {formatDDMMYYYY(a.due_date)}</span>}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {item.hasUnread && (
                        <button
                          onClick={() => handleMarkRead(item.ids)}
                          className="p-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-200 rounded-lg text-xs font-medium cursor-pointer"
                          title="Mark as read"
                        >
                          <Check size={14} />
                        </button>
                      )}
                      {(a.case_id || a.link) && (
                        <div className="flex flex-col items-end">
                          <button
                            type="button"
                            onClick={() => handleOpenCase(a, item.ids)}
                            className="flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-300 hover:border-[#0B3C9D] text-[#0B3C9D] text-xs font-bold rounded-lg shadow-2xs cursor-pointer"
                          >
                            <span>Open case</span>
                            <ExternalLink size={12} />
                          </button>
                          {accessDeniedAlertId === a.id && (
                            <span className="text-[10px] text-red-600 font-medium mt-1">
                              You don't have access to this case.
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* TAB 2: NOTIFICATION RULES */}
      {activeTab === 'rules' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-4">
            <div className="pb-3 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Notification rules
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Offsets, recipient roles, channels and templates.
                </p>
              </div>
            </div>

            <div className="pt-3">
              {(() => {
                const columns: ColumnDef<NotificationRuleItem>[] = [
                  {
                    key: 'event_type',
                    header: 'Event type',
                    width: '16%',
                    align: 'left',
                    render: (r) => (
                      <span className="font-mono font-medium text-[#0B3C9D] text-xs">
                        {r.event_type}
                      </span>
                    ),
                  },
                  {
                    key: 'title',
                    header: 'Title',
                    width: '24%',
                    align: 'left',
                    render: (r) => (
                      <span className="font-medium text-slate-800 text-xs line-clamp-2 block" title={r.title}>
                        {r.title}
                      </span>
                    ),
                  },
                  {
                    key: 'offsets',
                    header: 'Offsets',
                    width: '22%',
                    align: 'left',
                    render: (r) => (
                      <div className="flex gap-1 flex-wrap">
                        {r.offsets_days.map((o) => (
                          <span
                            key={o}
                            className="px-1.5 py-0.2 rounded text-[10px] font-medium bg-slate-100 text-slate-700 border border-slate-200"
                          >
                            {formatOffsetLabel(o)}
                          </span>
                        ))}
                      </div>
                    ),
                  },
                  {
                    key: 'recipient_role',
                    header: 'Recipient',
                    width: '14%',
                    align: 'left',
                    render: (r) => (
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                        {r.recipient_role}
                      </span>
                    ),
                  },
                  {
                    key: 'channel',
                    header: 'Channel',
                    width: '8%',
                    align: 'left',
                    render: (r) => <span className="text-xs text-slate-600">{r.channel}</span>,
                  },
                  {
                    key: 'status',
                    header: 'Status',
                    width: '8%',
                    align: 'left',
                    render: (r) => (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                          r.is_enabled ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {r.is_enabled ? 'Active' : 'Disabled'}
                      </span>
                    ),
                  },
                  {
                    key: 'action',
                    header: 'Action',
                    width: '8%',
                    align: 'right',
                    render: (r) => (
                      <button
                        onClick={() => openRuleEditor(r)}
                        className="px-2.5 py-1 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 rounded text-xs font-medium inline-flex items-center gap-1"
                      >
                        <Edit2 size={11} />
                        <span>Edit</span>
                      </button>
                    ),
                  },
                ];

                return (
                  <DataTable
                    columns={columns}
                    data={rules}
                    keyExtractor={(r) => r.id}
                    isLoading={isLoading}
                    emptyMessage="No notification rules configured."
                    isLong={rules.length > 12}
                  />
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: ESCALATION MATRIX */}
      {activeTab === 'matrix' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-4">
            <div className="pb-3 border-b border-slate-200">
              <h3 className="text-sm font-semibold text-slate-900">
                Escalation matrix
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Automatically notifies designated officers as deadlines are exceeded.
              </p>
            </div>

            <div className="pt-3">
              {(() => {
                const columns: ColumnDef<EscalationMatrixItem>[] = [
                  {
                    key: 'event_type',
                    header: 'Event type',
                    width: '26%',
                    align: 'left',
                    render: (m) => (
                      <span className="font-mono font-medium text-[#0B3C9D] text-xs">
                        {m.event_type}
                      </span>
                    ),
                  },
                  {
                    key: 'level',
                    header: 'Escalation level',
                    width: '18%',
                    align: 'left',
                    render: (m) => (
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-200">
                        Level {m.level}
                      </span>
                    ),
                  },
                  {
                    key: 'days_overdue',
                    header: 'Overdue threshold',
                    width: '20%',
                    align: 'right',
                    render: (m) => (
                      <span className="font-semibold text-red-600 text-xs">
                        ≥ {m.days_overdue} day(s) overdue
                      </span>
                    ),
                  },
                  {
                    key: 'designated_role',
                    header: 'Designated role',
                    width: '24%',
                    align: 'left',
                    render: (m) => <span className="text-slate-800 text-xs font-medium">{m.designated_role}</span>,
                  },
                  {
                    key: 'status',
                    header: 'Status',
                    width: '12%',
                    align: 'left',
                    render: () => (
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-100 text-emerald-800">
                        Active
                      </span>
                    ),
                  },
                ];

                return (
                  <DataTable
                    columns={columns}
                    data={matrix}
                    keyExtractor={(m) => m.id}
                    isLoading={isLoading}
                    emptyMessage="No escalation matrix configured."
                    isLong={matrix.length > 12}
                  />
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: ESCALATION HISTORY */}
      {activeTab === 'history' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-4">
            <div className="pb-3 border-b border-slate-200">
              <h3 className="text-sm font-semibold text-slate-900">
                Escalation records ({escalations.length})
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Permanent immutable record of who was notified, overdue days, and auto-closure on case resolution.
              </p>
            </div>

            <div className="pt-3">
              {(() => {
                const columns: ColumnDef<EscalationRecordItem>[] = [
                  {
                    key: 'case_id',
                    header: 'Case ID',
                    width: '12%',
                    align: 'left',
                    render: (e) => (
                      <span className="font-mono font-medium text-[#0B3C9D] text-xs">
                        {e.case_id}
                      </span>
                    ),
                  },
                  {
                    key: 'case_type',
                    header: 'Type',
                    width: '12%',
                    align: 'left',
                    render: (e) => <span className="text-slate-600 text-xs">{e.case_type}</span>,
                  },
                  {
                    key: 'level',
                    header: 'Level',
                    width: '8%',
                    align: 'left',
                    render: (e) => (
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-red-100 text-red-800 border border-red-200">
                        Level {e.level}
                      </span>
                    ),
                  },
                  {
                    key: 'notified_role',
                    header: 'Notified role',
                    width: '22%',
                    align: 'left',
                    render: (e) => (
                      <div>
                        <span className="font-medium text-slate-800 text-xs block">{e.notified_role}</span>
                        {e.notified_user_email && (
                          <span className="text-[11px] text-slate-600 block truncate" title={e.notified_user_email}>
                            {e.notified_user_email}
                          </span>
                        )}
                      </div>
                    ),
                  },
                  {
                    key: 'days_overdue',
                    header: 'Days overdue',
                    width: '10%',
                    align: 'right',
                    render: (e) => <span className="font-semibold text-red-600 text-xs">{e.days_overdue} d</span>,
                  },
                  {
                    key: 'status',
                    header: 'Status',
                    width: '12%',
                    align: 'left',
                    render: (e) => (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                          e.status === 'AUTO_CLOSED'
                            ? 'bg-blue-100 text-blue-800 border border-blue-200'
                            : 'bg-red-100 text-red-800 border border-red-200'
                        }`}
                      >
                        {e.status === 'AUTO_CLOSED' ? 'Auto closed' : e.status}
                      </span>
                    ),
                  },
                  {
                    key: 'created_at',
                    header: 'Triggered',
                    width: '12%',
                    align: 'left',
                    render: (e) => (
                      <span className="text-slate-600 text-xs">
                        {new Date(e.created_at).toLocaleDateString('en-GB')}
                      </span>
                    ),
                  },
                  {
                    key: 'resolved_at',
                    header: 'Resolved',
                    width: '12%',
                    align: 'left',
                    render: (e) => (
                      <span className="text-slate-600 text-xs">
                        {e.resolved_at ? new Date(e.resolved_at).toLocaleDateString('en-GB') : 'Pending'}
                      </span>
                    ),
                  },
                ];

                return (
                  <DataTable
                    columns={columns}
                    data={escalations}
                    keyExtractor={(e) => e.id}
                    isLoading={isLoading}
                    emptyMessage="No escalations have been triggered yet."
                    isLong={escalations.length > 12}
                  />
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: SCHEDULER RUN LOGS */}
      {activeTab === 'scheduler' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-4">
            <div className="pb-3 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-800">
                  Background Scanner Execution Logs ({schedulerLogs.length})
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Hourly background service scan history. Idempotent check ensures zero duplicate alerts for matching offsets.
                </p>
              </div>
            </div>

            <div className="pt-3">
              {(() => {
                const columns: ColumnDef<SchedulerLogItem>[] = [
                  {
                    key: 'run_timestamp',
                    header: 'Run timestamp',
                    width: '18%',
                    align: 'left',
                    render: (l) => (
                      <span className="font-mono text-xs text-slate-700">
                        {new Date(l.run_at).toLocaleDateString('en-GB')} {new Date(l.run_at).toLocaleTimeString('en-GB')}
                      </span>
                    ),
                  },
                  {
                    key: 'simulated_clock',
                    header: 'Simulated clock',
                    width: '18%',
                    align: 'left',
                    render: (l) => (
                      <span className="font-mono text-xs text-slate-600">
                        {l.simulated_clock ? `${new Date(l.simulated_clock).toLocaleDateString('en-GB')} ${new Date(l.simulated_clock).toLocaleTimeString('en-GB')}` : 'System real-time'}
                      </span>
                    ),
                  },
                  {
                    key: 'items_checked',
                    header: 'Checked',
                    width: '12%',
                    align: 'right',
                    render: (l) => <span className="font-semibold text-slate-800 text-xs">{l.items_checked}</span>,
                  },
                  {
                    key: 'alerts_created',
                    header: 'Alerts',
                    width: '12%',
                    align: 'right',
                    render: (l) => <span className="font-semibold text-[#0B3C9D] text-xs">{l.alerts_created}</span>,
                  },
                  {
                    key: 'escalations_triggered',
                    header: 'Escalations',
                    width: '14%',
                    align: 'right',
                    render: (l) => (
                      <span className={`font-semibold text-xs ${l.escalations_triggered > 0 ? 'text-red-600' : 'text-slate-600'}`}>
                        {l.escalations_triggered}
                      </span>
                    ),
                  },
                  {
                    key: 'duration_ms',
                    header: 'Duration',
                    width: '14%',
                    align: 'right',
                    render: (l) => <span className="text-xs text-slate-600">{l.duration_ms} ms</span>,
                  },
                  {
                    key: 'status',
                    header: 'Status',
                    width: '12%',
                    align: 'left',
                    render: (l) => (
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-medium ${
                          l.status === 'SUCCESS' ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {l.status}
                      </span>
                    ),
                  },
                ];

                return (
                  <DataTable
                    columns={columns}
                    data={schedulerLogs}
                    keyExtractor={(l) => l.id}
                    isLoading={isLoading}
                    emptyMessage="No background scanner logs recorded yet."
                    isLong={schedulerLogs.length > 12}
                  />
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {/* EDIT RULE MODAL */}
      {editingRule && (
        <Modal
          isOpen={true}
          onClose={() => setEditingRule(null)}
          title={`Edit Rule: ${editingRule.event_type}`}
        >
          <form onSubmit={handleSaveRule} className="space-y-4 text-xs">
            {ruleSaveError && (
              <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 font-semibold">
                {ruleSaveError}
              </div>
            )}

            <div>
              <label className="block text-slate-700 font-bold mb-1">Rule Display Title</label>
              <input
                type="text"
                value={ruleTitle}
                onChange={(e) => setRuleTitle(e.target.value)}
                required
                className="w-full p-2.5 rounded-lg border border-slate-300 focus:border-[#0B3C9D] outline-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Offset Days (comma-separated)</label>
                <input
                  type="text"
                  value={ruleOffsets}
                  onChange={(e) => setRuleOffsets(e.target.value)}
                  placeholder="30, 15, 7, 1, 0"
                  required
                  className="w-full p-2.5 rounded-lg border border-slate-300 focus:border-[#0B3C9D] outline-none font-mono"
                />
                <span className="text-[10px] text-slate-600 mt-0.5 block">0 represents On Due / Expiry date</span>
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Recipient role</label>
                <select
                  value={ruleRole}
                  onChange={(e) => setRuleRole(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-300 bg-white"
                >
                  <option value="INSTITUTE">INSTITUTE</option>
                  <option value="ASSIGNED_OFFICER">ASSIGNED_OFFICER</option>
                  <option value="REGIONAL_OFFICER">REGIONAL_OFFICER</option>
                  <option value="BUREAU_OFFICER">BUREAU_OFFICER</option>
                  <option value="COMMITTEE_MEMBER">COMMITTEE_MEMBER</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-slate-700 font-bold mb-1">Delivery Channel</label>
                <select
                  value={ruleChannel}
                  onChange={(e) => setRuleChannel(e.target.value)}
                  className="w-full p-2.5 rounded-lg border border-slate-300 bg-white"
                >
                  <option value="BOTH">Both (In-App & Email Outbox)</option>
                  <option value="IN_APP">In-App Only</option>
                  <option value="EMAIL">Email Outbox Only</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-700 font-bold mb-1">Active Status</label>
                <div className="flex items-center gap-2 mt-2">
                  <input
                    type="checkbox"
                    checked={ruleEnabled}
                    onChange={(e) => setRuleEnabled(e.target.checked)}
                    id="ruleEnabled"
                    className="rounded text-[#0B3C9D]"
                  />
                  <label htmlFor="ruleEnabled" className="font-semibold text-slate-700 cursor-pointer">
                    Rule Enabled
                  </label>
                </div>
              </div>
            </div>

            <div>
              <label className="block text-slate-700 font-bold mb-1">
                Message Template (supports placeholders: {'{case_id}'}, {'{institute_name}'}, {'{days_left}'}, etc.)
              </label>
              <textarea
                rows={3}
                value={ruleTemplate}
                onChange={(e) => setRuleTemplate(e.target.value)}
                required
                className="w-full p-2.5 rounded-lg border border-slate-300 focus:border-[#0B3C9D] outline-none font-mono text-xs"
              />
              <p className="text-[10px] text-slate-500 mt-1">
                Note: Mandatory reminder suffix &ldquo;This is a system reminder. Decisions remain with the competent authority.&rdquo; is appended automatically.
              </p>
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
              <button
                type="button"
                onClick={() => setEditingRule(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-600 hover:bg-slate-100 font-semibold"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 bg-[#0B3C9D] text-white rounded-lg hover:bg-[#082b70] font-bold"
              >
                Save rule
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
};
