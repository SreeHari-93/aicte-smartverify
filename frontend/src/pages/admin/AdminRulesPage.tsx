import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Clock,
  Files,
  ListChecks,
  Bell,
  Mail,
  ShieldAlert,
  Edit2,
  Check,
  AlertTriangle,
  RefreshCw,
  GitFork,
  HardDrive,
  ShieldCheck,
  UploadCloud,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { WorkflowTimelinesManager } from '../../components/WorkflowTimelinesManager';
import { AdminDocumentTypesPage } from './AdminDocumentTypesPage';
import { AdminChecklistsPage } from './AdminChecklistsPage';
import { alertsApi, NotificationRuleItem, EscalationMatrixItem } from '../../api/alerts';
import { workflowApi, CommunicationTemplate } from '../../api/workflow';
import { Modal } from '../../components/Modal';

export const AdminRulesPage: React.FC = () => {
  const { user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  // Role check: Regional Officer & Bureau Officer have VIEW-ONLY access
  const isReadOnly = user?.role === 'REGIONAL_OFFICER' || user?.role === 'BUREAU_OFFICER';

  // 8 Tabs: Workflow SLAs, Document Types, Checklists, Alert Rules, Communications, Category Mappings, Integrations, Safeguards
  const tabParam = searchParams.get('tab');
  const validTabs = ['slas', 'types', 'checklists', 'alert_rules', 'communications', 'mappings', 'integrations', 'safeguards'] as const;
  type TabKey = typeof validTabs[number];

  const initialTab: TabKey = (tabParam && validTabs.includes(tabParam as TabKey))
    ? (tabParam as TabKey)
    : 'slas';

  const [activeTab, setActiveTab] = useState<TabKey>(initialTab);

  const handleSelectTab = (tab: TabKey) => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  // Sync tab with URL search parameter if changed externally
  useEffect(() => {
    if (tabParam && validTabs.includes(tabParam as TabKey)) {
      setActiveTab(tabParam as TabKey);
    }
  }, [tabParam]);

  // Alert Rules State (Tab 4)
  const [rules, setRules] = useState<NotificationRuleItem[]>([]);
  const [matrix, setMatrix] = useState<EscalationMatrixItem[]>([]);
  const [isLoadingAlerts, setIsLoadingAlerts] = useState(false);
  const [alertError, setAlertError] = useState<string | null>(null);

  // Communications Templates State (Tab 5)
  const [commTemplates, setCommTemplates] = useState<CommunicationTemplate[]>([]);
  const [isLoadingComm, setIsLoadingComm] = useState(false);
  const [commError, setCommError] = useState<string | null>(null);
  const [editingComm, setEditingComm] = useState<CommunicationTemplate | null>(null);
  const [commName, setCommName] = useState('');
  const [commSubject, setCommSubject] = useState('');
  const [commBody, setCommBody] = useState('');
  const [commEnabled, setCommEnabled] = useState(true);
  const [commSaveError, setCommSaveError] = useState<string | null>(null);

  // Category Mappings State (Tab 6)
  const [categoryMappings, setCategoryMappings] = useState<Array<{ category: string; template_code: string; description: string }>>([]);
  const [isLoadingMappings, setIsLoadingMappings] = useState(false);
  const [isSavingMappings, setIsSavingMappings] = useState(false);
  const [mappingMessage, setMappingMessage] = useState<string | null>(null);

  // Integrations State (Tab 7)
  const [integrationsStatus, setIntegrationsStatus] = useState<any>(null);
  const [isLoadingIntegrations, setIsLoadingIntegrations] = useState(false);
  const [isSyncingFeed, setIsSyncingFeed] = useState(false);
  const [feedSyncResult, setFeedSyncResult] = useState<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Safeguards State (Tab 8)
  const [safeguards, setSafeguards] = useState<Record<string, string>>({});
  const [isLoadingSafeguards, setIsLoadingSafeguards] = useState(false);
  const [isSavingSafeguards, setIsSavingSafeguards] = useState(false);
  const [safeguardsMessage, setSafeguardsMessage] = useState<string | null>(null);

  // Edit Alert Rule Modal
  const [editingRule, setEditingRule] = useState<NotificationRuleItem | null>(null);
  const [ruleTitle, setRuleTitle] = useState('');
  const [ruleTemplate, setRuleTemplate] = useState('');
  const [ruleOffsets, setRuleOffsets] = useState('');
  const [ruleChannel, setRuleChannel] = useState('BOTH');
  const [ruleRole, setRuleRole] = useState('INSTITUTE');
  const [ruleEnabled, setRuleEnabled] = useState(true);
  const [ruleSaveError, setRuleSaveError] = useState<string | null>(null);

  const loadAlertConfig = async () => {
    setIsLoadingAlerts(true);
    setAlertError(null);
    try {
      const [rulesData, matrixData] = await Promise.all([
        alertsApi.getRules(),
        alertsApi.getEscalationMatrix(),
      ]);
      setRules(rulesData);
      setMatrix(matrixData);
    } catch (err: any) {
      setAlertError(err.response?.data?.detail || 'Failed to load alert rules configuration.');
    } finally {
      setIsLoadingAlerts(false);
    }
  };

  const loadCommTemplates = async () => {
    setIsLoadingComm(true);
    setCommError(null);
    try {
      const data = await workflowApi.getCommunicationTemplates();
      setCommTemplates(data);
    } catch (err: any) {
      setCommError(err.response?.data?.detail || 'Failed to load communication templates.');
    } finally {
      setIsLoadingComm(false);
    }
  };

  const loadMappings = async () => {
    setIsLoadingMappings(true);
    setMappingMessage(null);
    try {
      const data = await workflowApi.getCategoryMappings();
      setCategoryMappings(data);
    } catch (err: any) {
      setMappingMessage('Failed to load category mappings.');
    } finally {
      setIsLoadingMappings(false);
    }
  };

  const loadIntegrations = async () => {
    setIsLoadingIntegrations(true);
    try {
      const data = await workflowApi.getIntegrationsStatus();
      setIntegrationsStatus(data);
    } catch (err: any) {
      console.error('Failed to load integrations status', err);
    } finally {
      setIsLoadingIntegrations(false);
    }
  };

  const loadSafeguards = async () => {
    setIsLoadingSafeguards(true);
    setSafeguardsMessage(null);
    try {
      const data = await workflowApi.getSafeguardSettings();
      setSafeguards(data);
    } catch (err: any) {
      setSafeguardsMessage('Failed to load safeguard settings.');
    } finally {
      setIsLoadingSafeguards(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'alert_rules') {
      loadAlertConfig();
    } else if (activeTab === 'communications') {
      loadCommTemplates();
    } else if (activeTab === 'mappings') {
      loadMappings();
    } else if (activeTab === 'integrations') {
      loadIntegrations();
    } else if (activeTab === 'safeguards') {
      loadSafeguards();
    }
  }, [activeTab]);

  const openCommEditor = (t: CommunicationTemplate) => {
    if (isReadOnly) return;
    setEditingComm(t);
    setCommName(t.name);
    setCommSubject(t.subject_template);
    setCommBody(t.body_template);
    setCommEnabled(t.is_enabled);
    setCommSaveError(null);
  };

  const handleSaveComm = async () => {
    if (!editingComm || isReadOnly) return;
    setCommSaveError(null);
    try {
      await workflowApi.updateCommunicationTemplate(editingComm.id, {
        name: commName,
        subject_template: commSubject,
        body_template: commBody,
        is_enabled: commEnabled,
      });
      setEditingComm(null);
      await loadCommTemplates();
    } catch (err: any) {
      setCommSaveError(err.response?.data?.detail || 'Failed to update template.');
    }
  };

  const openRuleEditor = (r: NotificationRuleItem) => {
    if (isReadOnly) return;
    setEditingRule(r);
    setRuleTitle(r.title);
    setRuleTemplate(r.message_template);
    setRuleOffsets(r.offsets_days.join(', '));
    setRuleChannel(r.channel);
    setRuleRole(r.recipient_role);
    setRuleEnabled(r.is_enabled);
    setRuleSaveError(null);
  };

  const handleSaveRule = async () => {
    if (!editingRule || isReadOnly) return;
    setRuleSaveError(null);
    try {
      const parsedOffsets = ruleOffsets
        .split(',')
        .map((s) => parseInt(s.trim(), 10))
        .filter((n) => !isNaN(n));

      await alertsApi.updateRule(editingRule.id, {
        title: ruleTitle,
        message_template: ruleTemplate,
        offsets_days: parsedOffsets,
        channel: ruleChannel,
        recipient_role: ruleRole,
        is_enabled: ruleEnabled,
      });

      setEditingRule(null);
      await loadAlertConfig();
    } catch (err: any) {
      setRuleSaveError(err.response?.data?.detail || 'Failed to update rule.');
    }
  };

  const handleSaveMappings = async () => {
    if (isReadOnly) return;
    setIsSavingMappings(true);
    setMappingMessage(null);
    try {
      await workflowApi.updateCategoryMappings(categoryMappings);
      setMappingMessage('Category mappings updated successfully and take effect immediately.');
      setTimeout(() => setMappingMessage(null), 4000);
    } catch (err: any) {
      setMappingMessage('Failed to update category mappings.');
    } finally {
      setIsSavingMappings(false);
    }
  };

  const handleSyncSimulatedFeed = async () => {
    setIsSyncingFeed(true);
    setFeedSyncResult(null);
    try {
      const res = await workflowApi.triggerSimulatedSync();
      setFeedSyncResult(res);
      await loadIntegrations();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Sync failed.');
    } finally {
      setIsSyncingFeed(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsSyncingFeed(true);
    setFeedSyncResult(null);
    try {
      const res = await workflowApi.importFeedFile(file);
      setFeedSyncResult(res);
      await loadIntegrations();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to import file.');
    } finally {
      setIsSyncingFeed(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleSaveSafeguards = async () => {
    if (isReadOnly) return;
    setIsSavingSafeguards(true);
    setSafeguardsMessage(null);
    try {
      await workflowApi.updateSafeguardSettings(safeguards);
      setSafeguardsMessage('Safeguard and retention settings saved successfully.');
      setTimeout(() => setSafeguardsMessage(null), 4000);
    } catch (err: any) {
      setSafeguardsMessage('Failed to save safeguard settings.');
    } finally {
      setIsSavingSafeguards(false);
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Top Banner / Role Notice */}
      {isReadOnly && (
        <div className="bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded-xl flex items-center justify-between gap-3 text-xs shadow-xs">
          <div className="flex items-center gap-2">
            <ShieldAlert size={16} className="text-amber-600 shrink-0" />
            <span>
              <strong>View-only mode:</strong> You are logged in as <strong>{user?.role}</strong>. Regulatory rules, SLAs, checklists, and notification rules are displayed for guidance. Modifications require Central Administrator credentials.
            </span>
          </div>
          <span className="px-2 py-0.5 rounded bg-amber-200 text-amber-800 font-extrabold uppercase text-[10px] shrink-0">
            Read-Only
          </span>
        </div>
      )}

      {/* Main Header Card */}
      <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Rules and timelines
            </h1>
            <p className="text-xs text-slate-600 mt-0.5">
              Configure SLAs, checklists, alerts, and integration rules.
            </p>
          </div>
        </div>

        {/* Unified Tabs Navigation: single scrollable row */}
        <div className="flex items-center gap-2 pt-4 overflow-x-auto no-scrollbar pb-1">
          <button
            onClick={() => handleSelectTab('slas')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              activeTab === 'slas'
                ? 'bg-[#0B3C9D] text-white font-semibold shadow-sm'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-300 font-medium'
            }`}
          >
            <Clock size={14} />
            <span>Workflow SLAs</span>
          </button>

          <button
            onClick={() => handleSelectTab('types')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              activeTab === 'types'
                ? 'bg-[#0B3C9D] text-white font-semibold shadow-sm'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-300 font-medium'
            }`}
          >
            <Files size={14} />
            <span>Document types</span>
          </button>

          <button
            onClick={() => handleSelectTab('checklists')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              activeTab === 'checklists'
                ? 'bg-[#0B3C9D] text-white font-semibold shadow-sm'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-300 font-medium'
            }`}
          >
            <ListChecks size={14} />
            <span>Checklists</span>
          </button>

          <button
            onClick={() => handleSelectTab('alert_rules')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              activeTab === 'alert_rules'
                ? 'bg-[#0B3C9D] text-white font-semibold shadow-sm'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-300 font-medium'
            }`}
          >
            <Bell size={14} />
            <span>Alert rules</span>
          </button>

          <button
            onClick={() => handleSelectTab('communications')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              activeTab === 'communications'
                ? 'bg-[#0B3C9D] text-white font-semibold shadow-sm'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-300 font-medium'
            }`}
          >
            <Mail size={14} />
            <span>Communications</span>
          </button>

          <button
            onClick={() => handleSelectTab('mappings')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              activeTab === 'mappings'
                ? 'bg-[#0B3C9D] text-white font-semibold shadow-sm'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-300 font-medium'
            }`}
          >
            <GitFork size={14} />
            <span>Category mappings</span>
          </button>

          <button
            onClick={() => handleSelectTab('integrations')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              activeTab === 'integrations'
                ? 'bg-[#0B3C9D] text-white font-semibold shadow-sm'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-300 font-medium'
            }`}
          >
            <HardDrive size={14} />
            <span>Integrations</span>
          </button>

          <button
            onClick={() => handleSelectTab('safeguards')}
            className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-md text-xs whitespace-nowrap shrink-0 transition-colors ${
              activeTab === 'safeguards'
                ? 'bg-[#0B3C9D] text-white font-semibold shadow-sm'
                : 'bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 border border-slate-300 font-medium'
            }`}
          >
            <ShieldCheck size={14} />
            <span>Safeguards</span>
          </button>
        </div>
      </div>

      {/* Tab Content Display */}
      {activeTab === 'slas' && (
        <WorkflowTimelinesManager readOnly={isReadOnly} />
      )}

      {activeTab === 'types' && (
        <AdminDocumentTypesPage readOnly={isReadOnly} />
      )}

      {activeTab === 'checklists' && (
        <AdminChecklistsPage readOnly={isReadOnly} />
      )}

      {activeTab === 'alert_rules' && (
        <div className="space-y-6">
          {alertError && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs">
              {alertError}
            </div>
          )}

          {/* Section 1: Notification rules */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Notification rules
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Pre-configured offsets in days, recipient roles, channels, and message templates.
                </p>
              </div>
              <button
                onClick={loadAlertConfig}
                disabled={isLoadingAlerts}
                className="p-2 border border-slate-300 rounded-lg hover:bg-white text-slate-600"
              >
                <RefreshCw size={14} className={isLoadingAlerts ? 'animate-spin' : ''} />
              </button>
            </div>

            <div className="table-container">
              <table className="aicte-table">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-xs">
                  <tr>
                    <th className="py-2.5 px-3">Event type</th>
                    <th className="py-2.5 px-3">Title</th>
                    <th className="py-2.5 px-3">Offsets</th>
                    <th className="py-2.5 px-3">Recipient role</th>
                    <th className="py-2.5 px-3">Channel</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {rules.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50">
                      <td className="p-3 font-mono font-bold text-[#0B3C9D]">{r.event_type}</td>
                      <td className="p-3 font-semibold text-slate-800 max-w-[200px] truncate">{r.title}</td>
                      <td className="p-3">
                        <div className="flex gap-1 flex-wrap">
                          {r.offsets_days.map((o) => {
                            const lbl = o > 0 ? `${o} days before due` : o === 0 ? 'On due date' : `${Math.abs(o)} days overdue`;
                            return (
                              <span
                                key={o}
                                className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200"
                              >
                                {lbl}
                              </span>
                            );
                          })}
                        </div>
                      </td>
                      <td className="p-3">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-50 text-[#0B3C9D] border border-blue-200">
                          {r.recipient_role}
                        </span>
                      </td>
                      <td className="p-3 font-semibold text-slate-600">{r.channel}</td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            r.is_enabled ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {r.is_enabled ? 'ENABLED' : 'DISABLED'}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        {isReadOnly ? (
                          <span className="text-[11px] text-slate-600 font-medium">View-Only</span>
                        ) : (
                          <button
                            onClick={() => openRuleEditor(r)}
                            className="px-2.5 py-1 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 font-bold rounded-md shadow-2xs inline-flex items-center gap-1"
                          >
                            <Edit2 size={12} />
                            <span>Edit</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Section 2: Escalation Matrix */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200">
              <h3 className="text-sm font-semibold text-slate-900">
                Escalation matrix
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Automatically notifies designated officers as deadlines are exceeded.
              </p>
            </div>

            <div className="table-container">
              <table className="aicte-table">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-xs">
                  <tr>
                    <th className="py-2.5 px-3">Event type</th>
                    <th className="py-2.5 px-3">Level</th>
                    <th className="py-2.5 px-3">Days overdue</th>
                    <th className="py-2.5 px-3">Designated role</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
              <tbody className="divide-y divide-slate-200">
                {matrix.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-50">
                    <td className="p-3 font-mono font-bold text-[#0B3C9D]">{m.event_type}</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300">
                        Level {m.level}
                      </span>
                    </td>
                    <td className="p-3 font-bold text-red-600">+{m.days_overdue} days</td>
                    <td className="p-3 font-bold text-slate-700">{m.designated_role}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          m.is_enabled ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'
                        }`}
                      >
                        {m.is_enabled ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                    <td className="p-3 text-right text-slate-600 font-medium">
                      {isReadOnly ? 'View-Only' : 'Configured'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Communications Templates */}
      {activeTab === 'communications' && (
        <div className="space-y-6">
          {commError && (
            <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl text-xs">
              {commError}
            </div>
          )}

          {/* Guidelines Banner */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3 text-xs text-blue-950">
            <Mail size={18} className="text-[#0B3C9D] shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-[#0B3C9D] mb-1">Standardised communications</h4>
              <p className="leading-relaxed text-slate-700">
                Communications dispatch in-app notifications, queue outbox records, and generate official downloadable PDF letters formatted with council crest and signature blocks.
                Available placeholders: <code className="bg-white px-1.5 py-0.5 rounded border border-blue-200 text-[#0B3C9D] font-mono">{"{institute}"}</code>, <code className="bg-white px-1.5 py-0.5 rounded border border-blue-200 text-[#0B3C9D] font-mono">{"{application_code}"}</code>, <code className="bg-white px-1.5 py-0.5 rounded border border-blue-200 text-[#0B3C9D] font-mono">{"{stage}"}</code>, <code className="bg-white px-1.5 py-0.5 rounded border border-blue-200 text-[#0B3C9D] font-mono">{"{due_date}"}</code>, <code className="bg-white px-1.5 py-0.5 rounded border border-blue-200 text-[#0B3C9D] font-mono">{"{reason}"}</code>.
              </p>
              <p className="mt-1.5 font-medium text-slate-600 italic">
                Disclaimer: Every dispatch automatically terminates with &quot;This is a system reminder. Decisions remain with the competent authority.&quot;
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Communication notice templates ({commTemplates.length})
                </h3>
                <p className="text-xs text-slate-500">
                  Editable communication templates used across scrutiny, visits, undertakings, and renewals.
                </p>
              </div>
              <button
                onClick={loadCommTemplates}
                className="p-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100 transition-colors"
                title="Refresh Templates"
              >
                <RefreshCw size={14} className={isLoadingComm ? 'animate-spin' : ''} />
              </button>
            </div>

            <div className="divide-y divide-slate-100">
              {isLoadingComm ? (
                <div className="p-8 text-center text-slate-600 text-xs">Loading communication templates...</div>
              ) : commTemplates.length === 0 ? (
                <div className="p-8 text-center text-slate-600 text-xs">No communication templates found.</div>
              ) : (
                commTemplates.map((t) => (
                  <div key={t.id} className="p-4 hover:bg-slate-50/70 transition-colors space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800 text-xs">{t.name}</span>
                        <span className="font-mono text-[10px] text-slate-600 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                          {t.code}
                        </span>
                        <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-blue-100 text-[#0B3C9D]">
                          {t.category}
                        </span>
                        {t.is_enabled ? (
                          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-emerald-100 text-emerald-800">
                            Active
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-100 text-slate-600">
                            Disabled
                          </span>
                        )}
                      </div>

                      {!isReadOnly && (
                        <button
                          onClick={() => openCommEditor(t)}
                          className="px-2.5 py-1 bg-white hover:bg-slate-100 text-[#0B3C9D] border border-slate-300 rounded text-xs font-semibold flex items-center gap-1 transition-colors shadow-xs"
                        >
                          <Edit2 size={12} />
                          <span>Edit Template</span>
                        </button>
                      )}
                    </div>

                    <div className="text-xs">
                      <span className="text-slate-500 font-medium">Subject Line: </span>
                      <span className="font-semibold text-slate-800">{t.subject_template}</span>
                    </div>

                    <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-slate-700 font-mono text-[11px] whitespace-pre-line max-h-32 overflow-y-auto">
                      {t.body_template}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Tab 6: Category Mappings */}
      {activeTab === 'mappings' && (
        <div className="space-y-6">
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3 text-xs text-blue-950">
            <GitFork size={18} className="text-[#0B3C9D] shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-[#0B3C9D] mb-1">Application category routing</h4>
              <p className="leading-relaxed text-slate-700">
                Maps incoming application categories to workflow templates. When an institution submits an application or an external feed imports a case, the assigned template and initial SLA duration are applied automatically from this table without requiring code modifications.
              </p>
            </div>
          </div>

          {mappingMessage && (
            <div className="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs flex items-center gap-2">
              <CheckCircle2 size={15} />
              <span>{mappingMessage}</span>
            </div>
          )}

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-4 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-800">Category Routing Rules</h3>
                <p className="text-xs text-slate-500">Configure template mapping per application type</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={loadMappings}
                  className="p-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100 transition-colors"
                  title="Refresh Mappings"
                >
                  <RefreshCw size={14} className={isLoadingMappings ? 'animate-spin' : ''} />
                </button>
                {!isReadOnly && (
                  <button
                    onClick={handleSaveMappings}
                    disabled={isSavingMappings}
                    className="px-4 py-2 bg-[#0B3C9D] hover:bg-[#082b70] text-white rounded-lg font-bold text-xs shadow-xs transition-colors flex items-center gap-1.5"
                  >
                    <Check size={14} />
                    <span>{isSavingMappings ? 'Saving...' : 'Save Category Mappings'}</span>
                  </button>
                )}
              </div>
            </div>

            <div className="table-container">
              <table className="aicte-table">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 text-xs">
                    <th className="py-2.5 px-3 w-[30%]">Application category</th>
                    <th className="py-2.5 px-3 w-[35%]">Workflow template</th>
                    <th className="py-2.5 px-3 w-[35%]">Rationale</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {categoryMappings.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-4 font-bold text-slate-800">
                        {item.category}
                      </td>
                      <td className="py-3.5 px-4">
                        {isReadOnly ? (
                          <span className="font-mono font-bold text-[#0B3C9D] bg-blue-50 px-2 py-1 rounded border border-blue-200">
                            {item.template_code}
                          </span>
                        ) : (
                          <select
                            value={item.template_code}
                            onChange={(e) => {
                              const updated = [...categoryMappings];
                              updated[idx].template_code = e.target.value;
                              setCategoryMappings(updated);
                            }}
                            className="px-2.5 py-1.5 rounded-lg border border-slate-300 font-mono text-xs bg-white text-[#0B3C9D] font-bold"
                          >
                            <option value="ONLY_SCRUTINY">ONLY_SCRUTINY (2 stages: Scrutiny -&gt; Decision)</option>
                            <option value="SCRUTINY_EVC">SCRUTINY_EVC (3 stages: Scrutiny -&gt; EVC -&gt; Decision)</option>
                            <option value="EVC_SAC_SHC">EVC_SAC_SHC (4 stages: Scrutiny -&gt; EVC -&gt; SAC/SHC -&gt; Decision)</option>
                            <option value="ONLY_EVC">ONLY_EVC (2 stages: EVC Visit -&gt; Decision)</option>
                          </select>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600">
                        {item.description}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 7: Integrations Layer */}
      {activeTab === 'integrations' && (
        <div className="space-y-6">
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start justify-between gap-4 text-xs text-blue-950">
            <div className="flex items-start gap-3">
              <HardDrive size={18} className="text-[#0B3C9D] shrink-0 mt-0.5" />
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-bold text-[#0B3C9D]">AICTE External Integrations Layer</h4>
                  <span className="bg-amber-100 text-amber-900 border border-amber-300 px-2 py-0.5 rounded text-[10px] font-extrabold uppercase">
                    Simulated Adapters
                  </span>
                </div>
                <p className="leading-relaxed text-slate-700">
                  Connects to existing AICTE legacy systems using decoupled adapter interfaces. ApplicationFeedAdapter ingests application records skipping duplicates idempotently; InstituteRecordAdapter fetches accreditation profile and historical multi-year approval status.
                </p>
                <p className="mt-1 font-semibold text-slate-600">
                  Security Boundary: All adapters are read-only, role-restricted, and strictly never bypass system access controls.
                </p>
              </div>
            </div>

            <button
              onClick={loadIntegrations}
              className="p-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100 transition-colors shrink-0"
              title="Refresh Integrations Status"
            >
              <RefreshCw size={14} className={isLoadingIntegrations ? 'animate-spin' : ''} />
            </button>
          </div>

          {/* Sync Actions Bar */}
          {!isReadOnly && (
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex flex-wrap items-center justify-between gap-3">
              <div>
                <h4 className="font-bold text-xs text-slate-800">Trigger Integration Data Feed</h4>
                <p className="text-[11px] text-slate-500">Import application records into workflow pipeline</p>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".json,.csv"
                  className="hidden"
                />

                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isSyncingFeed}
                  className="flex items-center gap-1.5 px-3.5 py-2 border border-slate-300 hover:border-[#0B3C9D] text-slate-700 rounded-lg text-xs font-bold transition-colors"
                >
                  <UploadCloud size={14} />
                  <span>Import from File (JSON / CSV)</span>
                </button>

                <button
                  onClick={handleSyncSimulatedFeed}
                  disabled={isSyncingFeed}
                  className="flex items-center gap-1.5 px-4 py-2 bg-[#0B3C9D] hover:bg-[#082b70] text-white rounded-lg text-xs font-bold shadow-xs transition-colors"
                >
                  <RefreshCw size={14} className={isSyncingFeed ? 'animate-spin' : ''} />
                  <span>{isSyncingFeed ? 'Synchronizing...' : 'Sync Simulated Feed Now'}</span>
                </button>
              </div>
            </div>
          )}

          {/* Feed Sync Results Card */}
          {feedSyncResult && (
            <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs space-y-2">
              <div className="flex items-center gap-2 font-bold text-emerald-900">
                <CheckCircle2 size={16} />
                <span>Integration Ingestion Completed: {feedSyncResult.status}</span>
              </div>
              <div className="grid grid-cols-4 gap-2 pt-1">
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <span className="text-[10px] text-slate-600 block">Total Ingested</span>
                  <strong className="text-sm text-slate-800">{feedSyncResult.total_records}</strong>
                </div>
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <span className="text-[10px] text-slate-600 block">New Created</span>
                  <strong className="text-sm text-emerald-700">{feedSyncResult.created_workflows}</strong>
                </div>
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <span className="text-[10px] text-slate-600 block">Duplicates Skipped</span>
                  <strong className="text-sm text-amber-700">{feedSyncResult.skipped_duplicates}</strong>
                </div>
                <div className="bg-white p-2 rounded border border-emerald-200">
                  <span className="text-[10px] text-slate-600 block">Ingestion Source</span>
                  <strong className="text-xs text-slate-700 truncate block">{feedSyncResult.source}</strong>
                </div>
              </div>
            </div>
          )}

          {/* Adapters Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {integrationsStatus?.adapters?.map((adapter: any, idx: number) => (
              <div key={idx} className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <HardDrive size={16} className="text-[#0B3C9D]" />
                    <h3 className="font-bold text-sm text-[#0F2A5C]">{adapter.name}</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                    {adapter.health?.status || 'HEALTHY'}
                  </span>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed">
                  {adapter.metadata?.description}
                </p>

                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Adapter Type:</span>
                    <span className="font-mono font-semibold text-slate-700">{adapter.type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Mode:</span>
                    <span className="font-bold text-amber-700 bg-amber-50 px-1.5 rounded border border-amber-200">
                      SIMULATED
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Supported Formats:</span>
                    <span className="font-mono text-slate-700">{adapter.metadata?.supported_formats?.join(', ')}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Total Processed:</span>
                    <span className="font-bold text-slate-800">{adapter.metadata?.total_processed || 0} records</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Last Synced:</span>
                    <span className="font-mono text-slate-700">
                      {adapter.metadata?.last_sync ? new Date(adapter.metadata.last_sync).toLocaleString() : 'Never'}
                    </span>
                  </div>
                </div>

                <div className="text-[11px] text-slate-500 italic">
                  {adapter.metadata?.documentation}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 8: Safeguards & Retention */}
      {activeTab === 'safeguards' && (
        <div className="space-y-6">
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3 text-xs text-blue-950">
            <ShieldCheck size={18} className="text-[#0B3C9D] shrink-0 mt-0.5" />
            <div>
              <h4 className="font-bold text-[#0B3C9D] mb-1">Safeguards and retention</h4>
              <p className="leading-relaxed text-slate-700">
                Configure data retention windows, document upload limits, and EVC deadlines. All modifications are logged in the central audit trail. Stack traces are sanitized in API responses, and brute-force login attempts are rate-limited at the authentication gateway.
              </p>
              <p className="mt-1 font-semibold text-amber-900 bg-amber-100/60 px-2 py-0.5 rounded border border-amber-200 inline-block">
                Core principle: System decisions strictly remain with officials. No code path auto-approves or auto-rejects an application.
              </p>
            </div>
          </div>

          {safeguardsMessage && (
            <div className="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs flex items-center gap-2">
              <CheckCircle2 size={15} />
              <span>{safeguardsMessage}</span>
            </div>
          )}

          <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden p-6 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-100 pb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-800">System Parameters &amp; Deadlines</h3>
                <p className="text-xs text-slate-500">Fine-tune regulatory thresholds without code deployment</p>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={loadSafeguards}
                  className="p-1.5 rounded-lg border border-slate-300 text-slate-600 hover:bg-slate-100 transition-colors"
                  title="Refresh Safeguards"
                >
                  <RefreshCw size={14} className={isLoadingSafeguards ? 'animate-spin' : ''} />
                </button>
                {!isReadOnly && (
                  <button
                    onClick={handleSaveSafeguards}
                    disabled={isSavingSafeguards}
                    className="px-4 py-2 bg-[#0B3C9D] hover:bg-[#082b70] text-white rounded-lg font-bold text-xs shadow-xs transition-colors flex items-center gap-1.5"
                  >
                    <Check size={14} />
                    <span>{isSavingSafeguards ? 'Saving...' : 'Save Safeguards'}</span>
                  </button>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Document Retention (Days)</label>
                <input
                  type="number"
                  disabled={isReadOnly}
                  value={safeguards.document_retention_days || '1825'}
                  onChange={(e) => setSafeguards({ ...safeguards, document_retention_days: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Default: 1825 days (5 years)</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Audit Log Retention (Days)</label>
                <input
                  type="number"
                  disabled={isReadOnly}
                  value={safeguards.audit_retention_days || '2555'}
                  onChange={(e) => setSafeguards({ ...safeguards, audit_retention_days: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Default: 2555 days (7 years regulatory audit)</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Max Upload File Size (MB)</label>
                <input
                  type="number"
                  disabled={isReadOnly}
                  value={safeguards.max_upload_size_mb || '25'}
                  onChange={(e) => setSafeguards({ ...safeguards, max_upload_size_mb: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Default: 25 MB per document payload</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Allowed File Extensions</label>
                <input
                  type="text"
                  disabled={isReadOnly}
                  value={safeguards.allowed_upload_extensions || '.pdf, .png, .jpg, .jpeg'}
                  onChange={(e) => setSafeguards({ ...safeguards, allowed_upload_extensions: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Comma-separated MIME whitelist</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">EVC Scheduling Deadline (Standard, Days)</label>
                <input
                  type="number"
                  disabled={isReadOnly}
                  value={safeguards.evc_scheduling_days_default || '7'}
                  onChange={(e) => setSafeguards({ ...safeguards, evc_scheduling_days_default: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Limit for committee scheduling</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">EVC Scheduling Deadline (New Institute, Days)</label>
                <input
                  type="number"
                  disabled={isReadOnly}
                  value={safeguards.evc_scheduling_days_new_institute || '3'}
                  onChange={(e) => setSafeguards({ ...safeguards, evc_scheduling_days_new_institute: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Accelerated timeline for new institutions</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">EVC Completion Deadline (Standard, Days)</label>
                <input
                  type="number"
                  disabled={isReadOnly}
                  value={safeguards.evc_completion_days_default || '10'}
                  onChange={(e) => setSafeguards({ ...safeguards, evc_completion_days_default: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Physical inspection &amp; report upload limit</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">EVC Completion Deadline (New Institute, Days)</label>
                <input
                  type="number"
                  disabled={isReadOnly}
                  value={safeguards.evc_completion_days_new_institute || '5'}
                  onChange={(e) => setSafeguards({ ...safeguards, evc_completion_days_new_institute: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Accelerated completion for new applicants</span>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Validity Expiring-Soon Horizon (Days)</label>
                <input
                  type="number"
                  disabled={isReadOnly}
                  value={safeguards.validity_expiring_soon_days || '60'}
                  onChange={(e) => setSafeguards({ ...safeguards, validity_expiring_soon_days: e.target.value })}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
                <span className="text-[10px] text-slate-600 mt-1 block">Advance window to flag expiring documents</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit Notification Rule Modal */}
      {editingRule && (
        <Modal
          isOpen={true}
          onClose={() => setEditingRule(null)}
          title={`Edit notification rule: ${editingRule.event_type}`}
          subtitle="Configure reminder offsets, dispatch channels, and template wording."
        >
          <div className="space-y-4 text-xs">
            {ruleSaveError && (
              <div className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg flex items-center gap-2">
                <AlertTriangle size={14} className="shrink-0" />
                <span>{ruleSaveError}</span>
              </div>
            )}

            <div>
              <label className="block font-bold text-slate-700 mb-1">Rule Title</label>
              <input
                type="text"
                value={ruleTitle}
                onChange={(e) => setRuleTitle(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Reminder Offsets (Days, comma-separated)</label>
                <input
                  type="text"
                  value={ruleOffsets}
                  onChange={(e) => setRuleOffsets(e.target.value)}
                  placeholder="e.g. 30, 15, 7, 1, 0"
                  className="w-full px-3 py-2 rounded-lg border border-slate-300"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Recipient Role</label>
                <select
                  value={ruleRole}
                  onChange={(e) => setRuleRole(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white"
                >
                  <option value="INSTITUTE">INSTITUTE</option>
                  <option value="OFFICER">OFFICER (Assigned)</option>
                  <option value="REGIONAL_OFFICER">REGIONAL_OFFICER</option>
                  <option value="BUREAU_OFFICER">BUREAU_OFFICER</option>
                  <option value="COMMITTEE_MEMBER">COMMITTEE_MEMBER</option>
                  <option value="ALL">ALL (Multi-recipient)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Dispatch Channel</label>
                <select
                  value={ruleChannel}
                  onChange={(e) => setRuleChannel(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 bg-white"
                >
                  <option value="IN_APP">In-App Notification Only</option>
                  <option value="EMAIL">Email Outbox Only</option>
                  <option value="BOTH">Both (In-App + Email Outbox)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Rule Activation</label>
                <label className="flex items-center gap-2 mt-2 cursor-pointer font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={ruleEnabled}
                    onChange={(e) => setRuleEnabled(e.target.checked)}
                    className="rounded text-[#0B3C9D]"
                  />
                  <span>Active &amp; Scanned Hourly</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Message Template</label>
              <textarea
                rows={3}
                value={ruleTemplate}
                onChange={(e) => setRuleTemplate(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 font-mono text-[11px]"
              />
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
              <button
                onClick={() => setEditingRule(null)}
                className="px-4 py-2 border border-slate-300 text-slate-600 rounded-lg font-semibold hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRule}
                className="px-4 py-2 bg-[#0B3C9D] text-white rounded-lg font-bold hover:bg-[#082b70] flex items-center gap-1.5"
              >
                <Check size={14} />
                <span>Save Rule</span>
              </button>
            </div>
          </div>
        </Modal>
      )}

      {/* Edit Communication Template Modal */}
      {editingComm && (
        <Modal
          isOpen={true}
          onClose={() => setEditingComm(null)}
          title={`Edit Communication Template: ${editingComm.name}`}
          subtitle="Customize letter wording, subject format, and available placeholders."
        >
          <div className="space-y-4 text-xs">
            {commSaveError && (
              <div className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg flex items-center gap-2">
                <AlertTriangle size={14} className="shrink-0" />
                <span>{commSaveError}</span>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Template Name</label>
                <input
                  type="text"
                  value={commName}
                  onChange={(e) => setCommName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg border border-slate-300 font-semibold text-slate-800"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Activation Status</label>
                <label className="flex items-center gap-2 mt-2 cursor-pointer font-semibold text-slate-700">
                  <input
                    type="checkbox"
                    checked={commEnabled}
                    onChange={(e) => setCommEnabled(e.target.checked)}
                    className="rounded text-[#0B3C9D]"
                  />
                  <span>Active &amp; Available for Dispatch</span>
                </label>
              </div>
            </div>

            <div>
              <label className="block font-bold text-slate-700 mb-1">Subject Line Template</label>
              <input
                type="text"
                value={commSubject}
                onChange={(e) => setCommSubject(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 font-medium text-slate-800"
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="font-bold text-slate-700">Formal Letter Body Template</label>
                <span className="text-[10px] text-slate-500 font-mono">KaTeX &amp; Text formatting</span>
              </div>
              <textarea
                rows={8}
                value={commBody}
                onChange={(e) => setCommBody(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 font-mono text-[11px] leading-relaxed text-slate-800"
              />
            </div>

            {/* Placeholder Quick Chips */}
            <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
              <span className="font-bold text-slate-600 block text-[10px] uppercase">
                Supported Dynamic Placeholders (Click to insert):
              </span>
              <div className="flex flex-wrap gap-1.5">
                {['{institute}', '{application_code}', '{stage}', '{due_date}', '{reason}'].map((tok) => (
                  <button
                    key={tok}
                    type="button"
                    onClick={() => setCommBody((prev) => `${prev} ${tok}`)}
                    className="px-2 py-0.5 bg-white border border-slate-300 rounded text-[10px] font-mono font-bold text-[#0B3C9D] hover:bg-blue-50 transition-colors"
                  >
                    + {tok}
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-slate-600 italic">
                Note: The official disclaimer is appended automatically to all dispatches.
              </p>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-200">
              <button
                onClick={() => setEditingComm(null)}
                className="px-4 py-2 border border-slate-300 text-slate-600 rounded-lg font-semibold hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveComm}
                className="px-4 py-2 bg-[#0B3C9D] text-white rounded-lg font-bold hover:bg-[#082b70] flex items-center gap-1.5"
              >
                <Check size={14} />
                <span>Save Template</span>
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
