import React, { useState, useEffect, useMemo } from 'react';
import {
  Scale,
  Plus,
  Play,
  RotateCcw,
  UploadCloud,
  Copy,
  Trash2,
  Edit,
  Eye,
  GitCompare,
  Search,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from 'lucide-react';
import {
  adminApi,
  RuleOut,
  RuleDetailOut,
  RuleSetOut,
  PublishPreviewOut,
  RuleDiffOut,
  AdminApplicationOut,
} from '../../api/admin';
import { StatusPill } from '../../components/StatusPill';
import { Modal } from '../../components/Modal';

const RULE_TYPES = [
  'DOCUMENT_REQUIRED',
  'FIELD_REQUIRED',
  'VALIDITY_PERIOD',
  'CROSS_FIELD_MATCH',
  'NUMERIC_THRESHOLD',
  'COUNT_AT_LEAST',
  'EXTERNAL_VERIFICATION',
  'INFRASTRUCTURE',
  'COMPOSITE',
];

const SEVERITIES = ['BLOCKER', 'WARNING', 'INFO'];

export const AdminRulesPage: React.FC = () => {
  // State: Rules and RuleSets
  const [rules, setRules] = useState<RuleOut[]>([]);
  const [ruleSets, setRuleSets] = useState<RuleSetOut[]>([]);
  const [applications, setApplications] = useState<AdminApplicationOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');

  // Modals
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  // Active items for modals
  const [selectedRule, setSelectedRule] = useState<RuleOut | null>(null);
  const [selectedRuleDetail, setSelectedRuleDetail] = useState<RuleDetailOut | null>(null);
  const [publishPreview, setPublishPreview] = useState<PublishPreviewOut | null>(null);
  const [publishForm, setPublishForm] = useState({ name: 'APH 2026-27 Version Release', version_label: 'v2.0' });

  // Rule Form State
  const [isEditing, setIsEditing] = useState(false);
  const [ruleFormTab, setRuleFormTab] = useState<'visual' | 'json'>('visual');
  const [jsonValidation, setJsonValidation] = useState<{ valid: boolean; message: string } | null>(null);

  const [ruleForm, setRuleForm] = useState({
    code: '',
    title: '',
    description: '',
    handbook_ref: '',
    rule_type: 'DOCUMENT_REQUIRED',
    severity: 'BLOCKER',
    mandatory: true,
    status: 'DRAFT',
    applies_to_categories: ['EOA'],
    // Visual params
    doc_type: 'FIRE_NOC',
    min_validity_days: 30,
    field_path: 'application.academic_year',
    numeric_field: 'institute.nirf_rank',
    numeric_operator: '<=',
    numeric_value: 100,
    cross_left: 'doc.AFFIDAVIT.institute_name',
    cross_right: 'institute.name',
    cross_match: 'EXACT',
    count_collection: 'documents',
    count_min: 1,
    ext_document: 'FIRE_NOC',
    ext_service: 'API',
    raw_definition_json: '{\n  "type": "DOCUMENT_REQUIRED",\n  "document": "FIRE_NOC",\n  "min_validity_days": 30\n}',
  });

  // Test Modal State
  const [testMode, setTestMode] = useState<'app' | 'custom'>('app');
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [customContextJson, setCustomContextJson] = useState('{\n  "institute": {\n    "nirf_rank": 73\n  }\n}');
  const [testResult, setTestResult] = useState<any | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  // Diff Modal State
  const [diffRuleCode, setDiffRuleCode] = useState('');
  const [diffV1, setDiffV1] = useState(1);
  const [diffV2, setDiffV2] = useState(2);
  const [diffData, setDiffData] = useState<RuleDiffOut | null>(null);
  const [isLoadingDiff, setIsLoadingDiff] = useState(false);

  // Initial Data Load
  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [rulesData, rulesetsData, appsData] = await Promise.all([
        adminApi.listRules(),
        adminApi.listRuleSets(),
        adminApi.listApplications(),
      ]);
      setRules(rulesData);
      setRuleSets(rulesetsData);
      setApplications(appsData);
      if (appsData.length > 0) {
        setSelectedAppId(String(appsData[0].id));
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load rules metadata.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Filtered Rules
  const filteredRules = useMemo(() => {
    return rules.filter((r) => {
      const matchesSearch =
        r.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (r.description || '').toLowerCase().includes(searchQuery.toLowerCase());
      const matchesStatus = statusFilter === 'ALL' || r.status === statusFilter;
      const matchesSeverity =
        severityFilter === 'ALL' ||
        r.severity === severityFilter ||
        (severityFilter === 'WARNING' && r.severity === 'MAJOR') ||
        (severityFilter === 'INFO' && (r.severity === 'MINOR' || r.severity === 'ADVISORY'));
      const matchesType = typeFilter === 'ALL' || r.rule_type === typeFilter;
      return matchesSearch && matchesStatus && matchesSeverity && matchesType;
    });
  }, [rules, searchQuery, statusFilter, severityFilter, typeFilter]);

  // Build JSON definition from visual fields
  const buildDefinitionFromVisual = () => {
    switch (ruleForm.rule_type) {
      case 'DOCUMENT_REQUIRED':
        return {
          type: 'DOCUMENT_REQUIRED',
          document: ruleForm.doc_type,
          min_validity_days: Number(ruleForm.min_validity_days) || 0,
        };
      case 'FIELD_REQUIRED':
        return {
          type: 'FIELD_REQUIRED',
          field: ruleForm.field_path,
        };
      case 'VALIDITY_PERIOD':
        return {
          type: 'VALIDITY_PERIOD',
          document: ruleForm.doc_type,
          must_be_valid_on: 'today',
          buffer_days: Number(ruleForm.min_validity_days) || 0,
        };
      case 'CROSS_FIELD_MATCH':
        return {
          type: 'CROSS_FIELD_MATCH',
          left: ruleForm.cross_left,
          right: ruleForm.cross_right,
          match: ruleForm.cross_match,
        };
      case 'NUMERIC_THRESHOLD':
        return {
          type: 'NUMERIC_THRESHOLD',
          field: ruleForm.numeric_field,
          operator: ruleForm.numeric_operator,
          value: Number(ruleForm.numeric_value),
        };
      case 'COUNT_AT_LEAST':
        return {
          type: 'COUNT_AT_LEAST',
          source: ruleForm.count_collection,
          min_count: Number(ruleForm.count_min),
        };
      case 'EXTERNAL_VERIFICATION':
        return {
          type: 'EXTERNAL_VERIFICATION',
          document: ruleForm.ext_document,
          verification_service: ruleForm.ext_service,
          required_status: 'VERIFIED',
        };
      case 'INFRASTRUCTURE':
        return {
          type: 'INFRASTRUCTURE',
          metric: 'instructional_area',
          operator: '>=',
          target: 40000,
        };
      case 'COMPOSITE':
        return {
          type: 'COMPOSITE',
          operator: 'all',
          all: [
            { type: 'DOCUMENT_REQUIRED', document: ruleForm.doc_type, min_validity_days: 30 },
            { type: 'FIELD_REQUIRED', field: ruleForm.field_path },
          ],
        };
      default:
        return { type: ruleForm.rule_type };
    }
  };

  // Switch to JSON tab: serialize current visual values
  const handleSwitchTab = (tab: 'visual' | 'json') => {
    if (tab === 'json') {
      const def = buildDefinitionFromVisual();
      setRuleForm((prev) => ({ ...prev, raw_definition_json: JSON.stringify(def, null, 2) }));
    }
    setRuleFormTab(tab);
  };

  // Validate JSON Definition with backend
  const handleValidateJson = async () => {
    setJsonValidation(null);
    try {
      const parsed = JSON.parse(ruleForm.raw_definition_json);
      const res = await adminApi.validateDefinition(parsed);
      setJsonValidation({
        valid: res.valid,
        message: res.valid ? `Valid rule definition schema (depth ${res.depth})` : res.message,
      });
    } catch (err: any) {
      setJsonValidation({
        valid: false,
        message: `JSON syntax error: ${err.message}`,
      });
    }
  };

  // Open Create Modal
  const openCreateModal = () => {
    setIsEditing(false);
    setSelectedRule(null);
    setRuleForm({
      code: `RULE-${Math.floor(1000 + Math.random() * 9000)}`,
      title: '',
      description: '',
      handbook_ref: 'AICTE APH Section 2.1',
      rule_type: 'DOCUMENT_REQUIRED',
      severity: 'BLOCKER',
      mandatory: true,
      status: 'DRAFT',
      applies_to_categories: ['EOA'],
      doc_type: 'FIRE_NOC',
      min_validity_days: 30,
      field_path: 'application.academic_year',
      numeric_field: 'institute.nirf_rank',
      numeric_operator: '<=',
      numeric_value: 100,
      cross_left: 'doc.AFFIDAVIT.institute_name',
      cross_right: 'institute.name',
      cross_match: 'EXACT',
      count_collection: 'documents',
      count_min: 1,
      ext_document: 'FIRE_NOC',
      ext_service: 'API',
      raw_definition_json: '{\n  "type": "DOCUMENT_REQUIRED",\n  "document": "FIRE_NOC",\n  "min_validity_days": 30\n}',
    });
    setRuleFormTab('visual');
    setJsonValidation(null);
    setIsCreateModalOpen(true);
  };

  // Open Edit Modal
  const openEditModal = (rule: RuleOut) => {
    setIsEditing(true);
    setSelectedRule(rule);
    const def = rule.definition || {};
    setRuleForm({
      code: rule.code,
      title: rule.title,
      description: rule.description || '',
      handbook_ref: rule.handbook_ref || '',
      rule_type: rule.rule_type || 'DOCUMENT_REQUIRED',
      severity: rule.severity || 'BLOCKER',
      mandatory: rule.mandatory,
      status: rule.status,
      applies_to_categories: rule.applies_to_categories || ['EOA'],
      doc_type: def.document || 'FIRE_NOC',
      min_validity_days: def.min_validity_days || 30,
      field_path: def.field || 'application.academic_year',
      numeric_field: def.field || 'institute.nirf_rank',
      numeric_operator: def.operator || '<=',
      numeric_value: def.value || 100,
      cross_left: def.left || 'doc.AFFIDAVIT.institute_name',
      cross_right: def.right || 'institute.name',
      cross_match: def.match || 'EXACT',
      count_collection: def.source || 'documents',
      count_min: def.min_count || 1,
      ext_document: def.document || 'FIRE_NOC',
      ext_service: def.verification_service || 'API',
      raw_definition_json: JSON.stringify(def, null, 2),
    });
    setRuleFormTab('visual');
    setJsonValidation(null);
    setIsCreateModalOpen(true);
  };

  // Submit Rule Form (Create or Update)
  const handleSaveRule = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);

    let finalDefinition: Record<string, any>;
    if (ruleFormTab === 'json') {
      try {
        finalDefinition = JSON.parse(ruleForm.raw_definition_json);
      } catch (e: any) {
        setErrorMsg(`Invalid JSON definition: ${e.message}`);
        return;
      }
    } else {
      finalDefinition = buildDefinitionFromVisual();
    }

    try {
      if (isEditing && selectedRule) {
        await adminApi.updateRule(selectedRule.code, {
          expected_version: selectedRule.current_version,
          title: ruleForm.title,
          description: ruleForm.description,
          handbook_ref: ruleForm.handbook_ref,
          rule_type: ruleForm.rule_type,
          severity: ruleForm.severity,
          mandatory: ruleForm.mandatory,
          status: ruleForm.status,
          applies_to_categories: ruleForm.applies_to_categories,
          definition: finalDefinition,
          change_note: `Updated rule ${selectedRule.code} via Admin Console`,
        });
        setSuccessMsg(`Rule '${selectedRule.code}' updated successfully.`);
      } else {
        await adminApi.createRule({
          code: ruleForm.code.trim().toUpperCase(),
          title: ruleForm.title.trim(),
          description: ruleForm.description,
          handbook_ref: ruleForm.handbook_ref,
          rule_type: ruleForm.rule_type,
          severity: ruleForm.severity,
          mandatory: ruleForm.mandatory,
          status: ruleForm.status,
          applies_to_categories: ruleForm.applies_to_categories,
          definition: finalDefinition,
        });
        setSuccessMsg(`Rule '${ruleForm.code.toUpperCase()}' created successfully as ${ruleForm.status}.`);
      }
      setIsCreateModalOpen(false);
      loadData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to save rule.');
    }
  };

  // Toggle Active
  const handleToggleActive = async (rule: RuleOut) => {
    try {
      await adminApi.toggleRuleActive(rule.code);
      setRules((prev) =>
        prev.map((r) => (r.code === rule.code ? { ...r, is_active: !r.is_active } : r))
      );
      setSuccessMsg(`Rule '${rule.code}' active state updated.`);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to update rule state.');
    }
  };

  // Delete Rule (Draft Only)
  const handleDeleteRule = async (rule: RuleOut) => {
    if (rule.status !== 'DRAFT') {
      alert('Only DRAFT rules can be deleted. Published rules cannot be deleted.');
      return;
    }
    if (!window.confirm(`Are you sure you want to permanently delete draft rule ${rule.code}?`)) {
      return;
    }
    try {
      await adminApi.deleteRule(rule.code);
      setRules((prev) => prev.filter((r) => r.code !== rule.code));
      setSuccessMsg(`Draft rule '${rule.code}' deleted successfully.`);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to delete draft rule.');
    }
  };

  // Clone Rule
  const handleCloneRule = async (rule: RuleOut) => {
    const newCode = window.prompt(`Enter code for cloned rule:`, `${rule.code}-COPY`);
    if (!newCode) return;
    try {
      const cloned = await adminApi.cloneRule(rule.code, newCode.trim().toUpperCase());
      setSuccessMsg(`Rule cloned as '${cloned.code}'.`);
      loadData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to clone rule.');
    }
  };

  // Open Test Modal
  const openTestModal = (rule: RuleOut) => {
    setSelectedRule(rule);
    setTestResult(null);
    setIsTestModalOpen(true);
  };

  // Run Test Simulation
  const handleRunTest = async () => {
    if (!selectedRule) return;
    setIsTesting(true);
    setTestResult(null);
    try {
      let contextPayload: Record<string, any> = {};
      let appIdPayload: string | undefined = undefined;

      if (testMode === 'app' && selectedAppId) {
        appIdPayload = selectedAppId;
      } else {
        try {
          contextPayload = JSON.parse(customContextJson);
        } catch (e: any) {
          alert(`Invalid Context JSON: ${e.message}`);
          setIsTesting(false);
          return;
        }
      }

      const res = await adminApi.simulateRule({
        definition: selectedRule.definition || {},
        context: contextPayload,
        application_id: appIdPayload,
        rule_meta: {
          code: selectedRule.code,
          title: selectedRule.title,
          severity: selectedRule.severity,
        },
      });
      setTestResult(res);
    } catch (err: any) {
      setTestResult({
        passed: false,
        message: err.response?.data?.detail || 'Simulation error.',
        details: {},
      });
    } finally {
      setIsTesting(false);
    }
  };

  // Open Publish Preview Modal
  const openPublishModal = async () => {
    try {
      const preview = await adminApi.getPublishPreview();
      setPublishPreview(preview);
      const nextVer = preview.active_ruleset_version
        ? `v${(parseFloat(preview.active_ruleset_version.replace('v', '')) + 0.1).toFixed(1)}`
        : 'v1.0';
      setPublishForm({
        name: preview.active_ruleset_name || 'APH 2026-27 Production Ruleset',
        version_label: nextVer,
      });
      setIsPublishModalOpen(true);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to generate publish preview.');
    }
  };

  // Confirm Publish
  const handleConfirmPublish = async () => {
    try {
      const res = await adminApi.publishRuleSet(publishForm);
      setSuccessMsg(`Published RuleSet '${res.name}' (${res.version_label}) successfully.`);
      setIsPublishModalOpen(false);
      loadData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to publish ruleset.');
    }
  };

  // Rollback RuleSet
  const handleRollback = async (rs: RuleSetOut) => {
    if (!window.confirm(`Are you sure you want to rollback to RuleSet '${rs.name}' (${rs.version_label})?`)) {
      return;
    }
    try {
      const res = await adminApi.rollbackRuleSet(rs.id);
      setSuccessMsg(res.message);
      loadData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to rollback ruleset.');
    }
  };

  // Open Version Diff Modal
  const openDiffModal = async (rule: RuleOut) => {
    setDiffRuleCode(rule.code);
    setDiffV1(rule.current_version > 1 ? rule.current_version - 1 : 1);
    setDiffV2(rule.current_version);
    setDiffData(null);
    setIsDiffModalOpen(true);
    loadDiff(rule.code, rule.current_version > 1 ? rule.current_version - 1 : 1, rule.current_version);
  };

  const loadDiff = async (code: string, v1: number, v2: number) => {
    setIsLoadingDiff(true);
    try {
      const res = await adminApi.getRuleDiff(code, v1, v2);
      setDiffData(res);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load diff.');
    } finally {
      setIsLoadingDiff(false);
    }
  };

  // Open Detail / History Modal
  const openDetailModal = async (rule: RuleOut) => {
    try {
      const detail = await adminApi.getRule(rule.code);
      setSelectedRuleDetail(detail);
      setIsDetailModalOpen(true);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to load rule history.');
    }
  };

  const activeRuleSet = ruleSets.find((rs) => rs.status === 'ACTIVE' || rs.status === 'PUBLISHED');

  return (
    <div className="space-y-6">
      {/* Alert Notices */}
      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 text-[#C62828] rounded-xl flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <AlertCircle size={20} className="shrink-0" />
            <p className="text-sm font-medium">{errorMsg}</p>
          </div>
          <button onClick={() => setErrorMsg(null)} className="text-sm font-bold ml-4">✕</button>
        </div>
      )}
      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-[#1E7036] rounded-xl flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-3">
            <CheckCircle2 size={20} className="shrink-0" />
            <p className="text-sm font-medium">{successMsg}</p>
          </div>
          <button onClick={() => setSuccessMsg(null)} className="text-sm font-bold ml-4">✕</button>
        </div>
      )}

      {/* 1. RuleSet Versioning Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 pb-6 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center gap-2 bg-[#E3F0FF] text-[#0B3C9D] text-xs font-semibold px-2.5 py-1 rounded-md mb-2">
              <Scale size={14} />
              <span>Declarative Rule Engine • Version Governance</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F2A5C] tracking-tight">
              AICTE Regulatory Rules Manager
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Configure validation rules, test against live applications, and publish immutable versioned RuleSets.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={openPublishModal}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#0B3C9D] text-white text-sm font-bold hover:bg-[#0F2A5C] shadow-sm transition-all hover:scale-[1.01]"
            >
              <UploadCloud size={18} />
              <span>Publish RuleSet</span>
            </button>
            <button
              onClick={openCreateModal}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-orange-500 text-white text-sm font-bold hover:bg-orange-600 shadow-sm transition-all"
            >
              <Plus size={18} />
              <span>Create Rule</span>
            </button>
            <button
              onClick={loadData}
              className="p-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
              title="Refresh rules"
            >
              <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Current Active RuleSet Indicator & Prior Versions */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-gradient-to-br from-blue-50/70 to-indigo-50/40 rounded-xl border border-blue-100">
            <span className="text-xs uppercase font-bold tracking-wider text-[#0B3C9D]">Active RuleSet</span>
            <div className="flex items-center justify-between mt-2">
              <div>
                <p className="text-lg font-bold text-[#0F2A5C]">{activeRuleSet?.name || 'APH 2026-27 Live'}</p>
                <p className="text-xs text-slate-600 mt-0.5">Version: {activeRuleSet?.version_label || 'v1.0'}</p>
              </div>
              <StatusPill status="ACTIVE" />
            </div>
            <div className="mt-3 text-[11px] text-slate-500 flex items-center justify-between pt-2 border-t border-blue-100/80">
              <span>{activeRuleSet?.rules_count || rules.length} Rules Bound</span>
              <span>Published: {activeRuleSet?.published_at ? new Date(activeRuleSet.published_at).toLocaleDateString() : 'Active'}</span>
            </div>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs uppercase font-bold tracking-wider text-slate-500">Draft Rules Isolation</span>
            <p className="text-xl font-bold text-[#0F2A5C] mt-2">
              {rules.filter((r) => r.status === 'DRAFT').length} in Draft
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Draft edits never alter live institute validations until a formal Publish action.
            </p>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 flex flex-col justify-between">
            <span className="text-xs uppercase font-bold tracking-wider text-slate-500">Total Configured Rules</span>
            <p className="text-xl font-bold text-[#0F2A5C] mt-2">{rules.length} Rules</p>
            <span className="text-xs text-slate-500">
              {rules.filter((r) => r.is_active).length} Active | {rules.filter((r) => !r.is_active).length} Inactive
            </span>
          </div>
        </div>

        {/* Previous RuleSets Rollback List */}
        {ruleSets.length > 1 && (
          <div className="mt-6 pt-4 border-t border-slate-100">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
              Version History & Rollback
            </h3>
            <div className="flex flex-wrap items-center gap-2">
              {ruleSets.map((rs) => (
                <div
                  key={rs.id}
                  className="flex items-center gap-3 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-700 shadow-2xs"
                >
                  <span className="font-bold text-[#0F2A5C]">{rs.name} ({rs.version_label})</span>
                  <StatusPill status={rs.status} className="scale-90" />
                  {rs.status !== 'ACTIVE' && (
                    <button
                      onClick={() => handleRollback(rs)}
                      className="ml-1 text-[#0B3C9D] hover:underline font-semibold flex items-center gap-1"
                    >
                      <RotateCcw size={12} />
                      <span>Rollback</span>
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 2. Filter Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="relative w-full md:w-80">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search rule code, title..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-medium bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
          >
            <option value="ALL">All Statuses</option>
            <option value="PUBLISHED">Published</option>
            <option value="DRAFT">Draft</option>
            <option value="ARCHIVED">Archived</option>
          </select>

          {/* Severity Filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-medium bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
          >
            <option value="ALL">All Severities</option>
            <option value="BLOCKER">Blocker</option>
            <option value="WARNING">Warning</option>
            <option value="INFO">Info</option>
          </select>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="px-3 py-2 rounded-lg border border-slate-200 text-xs font-medium bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
          >
            <option value="ALL">All Types</option>
            {RULE_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      {/* 3. Rules Table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase text-xs tracking-wider">
              <tr>
                <th className="py-4 px-5">Rule Code</th>
                <th className="py-4 px-5">Title & Reference</th>
                <th className="py-4 px-5">Type</th>
                <th className="py-4 px-5">Severity</th>
                <th className="py-4 px-5">Status</th>
                <th className="py-4 px-5">Ver</th>
                <th className="py-4 px-5">Active</th>
                <th className="py-4 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredRules.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No rules found matching the filters.
                  </td>
                </tr>
              ) : (
                filteredRules.map((rule) => (
                  <tr key={rule.code} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-4 px-5 font-mono font-bold text-[#0B3C9D] whitespace-nowrap">
                      {rule.code}
                    </td>
                    <td className="py-4 px-5 max-w-xs sm:max-w-md">
                      <p className="font-semibold text-[#0F2A5C] truncate">{rule.title}</p>
                      <p className="text-xs text-slate-400 truncate">{rule.handbook_ref || 'Handbook Section 2'}</p>
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap">
                      <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2.5 py-1 rounded">
                        {rule.rule_type}
                      </span>
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap">
                      <StatusPill status={rule.severity} />
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap">
                      <StatusPill status={rule.status} />
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap font-mono text-xs text-slate-500 font-semibold">
                      v{rule.current_version}
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap">
                      <button
                        onClick={() => handleToggleActive(rule)}
                        className={`w-10 h-5 flex items-center rounded-full p-0.5 transition-colors ${
                          rule.is_active ? 'bg-emerald-600 justify-end' : 'bg-slate-300 justify-start'
                        }`}
                        title={rule.is_active ? 'Disable rule' : 'Enable rule'}
                      >
                        <div className="w-4 h-4 rounded-full bg-white shadow-xs" />
                      </button>
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => openTestModal(rule)}
                          className="p-1.5 text-blue-700 hover:bg-blue-50 rounded-md transition-colors"
                          title="Test Rule"
                        >
                          <Play size={15} />
                        </button>
                        <button
                          onClick={() => openEditModal(rule)}
                          className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
                          title="Edit Rule"
                        >
                          <Edit size={15} />
                        </button>
                        <button
                          onClick={() => openDiffModal(rule)}
                          className="p-1.5 text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors"
                          title="View Version Diff"
                        >
                          <GitCompare size={15} />
                        </button>
                        <button
                          onClick={() => handleCloneRule(rule)}
                          className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-md transition-colors"
                          title="Duplicate Rule"
                        >
                          <Copy size={15} />
                        </button>
                        {rule.status === 'DRAFT' ? (
                          <button
                            onClick={() => handleDeleteRule(rule)}
                            className="p-1.5 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                            title="Delete Draft Rule"
                          >
                            <Trash2 size={15} />
                          </button>
                        ) : (
                          <span
                            className="p-1.5 text-slate-300 cursor-not-allowed"
                            title="Published rules cannot be deleted (deactivate instead)"
                          >
                            <Trash2 size={15} />
                          </span>
                        )}
                        <button
                          onClick={() => openDetailModal(rule)}
                          className="p-1.5 text-slate-500 hover:bg-slate-100 rounded-md transition-colors"
                          title="View History Details"
                        >
                          <Eye size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* CREATE / EDIT RULE MODAL                                                  */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        title={isEditing ? `Edit Rule: ${ruleForm.code}` : 'Create Regulatory Rule'}
        subtitle={isEditing ? 'Modify parameters, logic definition, or handbook references' : 'Configure declarative regulatory logic across the 9 validation evaluators'}
        maxWidth="max-w-[880px]"
        footer={
          <>
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(false)}
              className="px-5 py-2.5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-200/70 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSaveRule}
              className="px-6 py-2.5 rounded-xl text-sm font-bold bg-[#0B3C9D] text-white hover:bg-[#0F2A5C] shadow-sm transition-colors"
            >
              {isEditing ? 'Save Changes' : 'Create Rule'}
            </button>
          </>
        }
      >
        <div className="space-y-6">
          {/* Top Form Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Rule Code *
              </label>
              <input
                type="text"
                disabled={isEditing}
                value={ruleForm.code}
                onChange={(e) => setRuleForm({ ...ruleForm, code: e.target.value.toUpperCase() })}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D] disabled:bg-slate-100 font-semibold"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Handbook Reference
              </label>
              <input
                type="text"
                value={ruleForm.handbook_ref}
                onChange={(e) => setRuleForm({ ...ruleForm, handbook_ref: e.target.value })}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                placeholder="e.g. APH Section 4.3"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
              Rule Title *
            </label>
            <input
              type="text"
              value={ruleForm.title}
              onChange={(e) => setRuleForm({ ...ruleForm, title: e.target.value })}
              className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              placeholder="Descriptive title"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
              Description & Statutory Rationale
            </label>
            <textarea
              rows={2}
              value={ruleForm.description}
              onChange={(e) => setRuleForm({ ...ruleForm, description: e.target.value })}
              className="w-full p-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              placeholder="Explain why this rule is mandated by AICTE..."
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Rule Type *
              </label>
              <select
                value={ruleForm.rule_type}
                onChange={(e) => setRuleForm({ ...ruleForm, rule_type: e.target.value })}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-semibold text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              >
                {RULE_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Severity *
              </label>
              <select
                value={ruleForm.severity}
                onChange={(e) => setRuleForm({ ...ruleForm, severity: e.target.value })}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-semibold text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              >
                {SEVERITIES.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Status *
              </label>
              <select
                value={ruleForm.status}
                onChange={(e) => setRuleForm({ ...ruleForm, status: e.target.value })}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-semibold text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              >
                <option value="DRAFT">DRAFT (Isolated)</option>
                <option value="PUBLISHED">PUBLISHED (Active in Run)</option>
              </select>
            </div>
          </div>

          {/* Form Tabs: Visual Parameters vs Advanced JSON */}
          <div className="pt-2 border-t border-slate-200">
            <div className="flex items-center justify-between mb-4">
              <span className="text-xs font-bold uppercase tracking-wider text-[#0B3C9D]">
                Rule Logic Definition
              </span>
              <div className="inline-flex rounded-xl bg-slate-100 p-1 text-xs font-bold border border-slate-200">
                <button
                  type="button"
                  onClick={() => handleSwitchTab('visual')}
                  className={`px-4 py-1.5 rounded-lg transition-all ${
                    ruleFormTab === 'visual'
                      ? 'bg-[#0B3C9D] text-white shadow-xs font-bold'
                      : 'text-slate-600 hover:text-[#0B3C9D]'
                  }`}
                >
                  Visual Form
                </button>
                <button
                  type="button"
                  onClick={() => handleSwitchTab('json')}
                  className={`px-4 py-1.5 rounded-lg transition-all ${
                    ruleFormTab === 'json'
                      ? 'bg-[#0B3C9D] text-white shadow-xs font-bold'
                      : 'text-slate-600 hover:text-[#0B3C9D]'
                  }`}
                >
                  Advanced JSON
                </button>
              </div>
            </div>

            {/* TAB 1: Visual Form Builder */}
            {ruleFormTab === 'visual' ? (
              <div className="p-5 bg-slate-50/90 rounded-xl border border-slate-200 space-y-4">
                {ruleForm.rule_type === 'DOCUMENT_REQUIRED' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-2">Document Code *</label>
                      <input
                        type="text"
                        value={ruleForm.doc_type}
                        onChange={(e) => setRuleForm({ ...ruleForm, doc_type: e.target.value.toUpperCase() })}
                        className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                        placeholder="e.g. FIRE_NOC"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-2">Min Days Remaining Validity</label>
                      <input
                        type="number"
                        value={ruleForm.min_validity_days}
                        onChange={(e) => setRuleForm({ ...ruleForm, min_validity_days: parseInt(e.target.value) || 0 })}
                        className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                      />
                    </div>
                  </div>
                )}

                {ruleForm.rule_type === 'FIELD_REQUIRED' && (
                  <div>
                    <label className="block text-xs font-bold text-slate-700 mb-2">Required Field Path *</label>
                    <input
                      type="text"
                      value={ruleForm.field_path}
                      onChange={(e) => setRuleForm({ ...ruleForm, field_path: e.target.value })}
                      className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                      placeholder="e.g. application.academic_year"
                    />
                  </div>
                )}

                {ruleForm.rule_type === 'NUMERIC_THRESHOLD' && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-2">Field Path</label>
                      <input
                        type="text"
                        value={ruleForm.numeric_field}
                        onChange={(e) => setRuleForm({ ...ruleForm, numeric_field: e.target.value })}
                        className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-2">Operator</label>
                      <select
                        value={ruleForm.numeric_operator}
                        onChange={(e) => setRuleForm({ ...ruleForm, numeric_operator: e.target.value })}
                        className="w-full h-11 px-3 rounded-lg border border-slate-300 text-sm font-mono bg-white focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                      >
                        <option value="<=">&lt;=</option>
                        <option value=">=">&gt;=</option>
                        <option value="<">&lt;</option>
                        <option value=">">&gt;</option>
                        <option value="==">==</option>
                        <option value="!=">!=</option>
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-2">Target Value</label>
                      <input
                        type="number"
                        value={ruleForm.numeric_value}
                        onChange={(e) => setRuleForm({ ...ruleForm, numeric_value: parseFloat(e.target.value) || 0 })}
                        className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                      />
                    </div>
                  </div>
                )}

                {ruleForm.rule_type === 'CROSS_FIELD_MATCH' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-2">Left Field</label>
                      <input
                        type="text"
                        value={ruleForm.cross_left}
                        onChange={(e) => setRuleForm({ ...ruleForm, cross_left: e.target.value })}
                        className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-2">Right Field</label>
                      <input
                        type="text"
                        value={ruleForm.cross_right}
                        onChange={(e) => setRuleForm({ ...ruleForm, cross_right: e.target.value })}
                        className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                      />
                    </div>
                  </div>
                )}

                {ruleForm.rule_type === 'EXTERNAL_VERIFICATION' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-2">Document Code</label>
                      <input
                        type="text"
                        value={ruleForm.ext_document}
                        onChange={(e) => setRuleForm({ ...ruleForm, ext_document: e.target.value.toUpperCase() })}
                        className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">Verification Adapter</label>
                      <select
                        value={ruleForm.ext_service}
                        onChange={(e) => setRuleForm({ ...ruleForm, ext_service: e.target.value })}
                        className="w-full px-3 py-1.5 rounded-lg border border-slate-300 text-sm"
                      >
                        <option value="API">API Integration</option>
                        <option value="QR">QR Code Scanner</option>
                        <option value="PORTAL">External Statutory Portal</option>
                        <option value="SWAYAM">SWAYAM / NPTEL</option>
                        <option value="FIRE_AUTHORITY">State Fire Service</option>
                      </select>
                    </div>
                  </div>
                )}

                {/* Info message for complex types */}
                {(ruleForm.rule_type === 'COMPOSITE' || ruleForm.rule_type === 'INFRASTRUCTURE' || ruleForm.rule_type === 'COUNT_AT_LEAST' || ruleForm.rule_type === 'VALIDITY_PERIOD') && (
                  <p className="text-xs text-slate-500 italic">
                    Configuring default declarative structure for {ruleForm.rule_type}. You can fine-tune in the Advanced JSON tab anytime.
                  </p>
                )}
              </div>
            ) : (
              /* TAB 2: Advanced JSON */
              <div className="space-y-2">
                <textarea
                  rows={7}
                  value={ruleForm.raw_definition_json}
                  onChange={(e) => setRuleForm({ ...ruleForm, raw_definition_json: e.target.value })}
                  className="w-full p-3 font-mono text-xs bg-slate-900 text-emerald-400 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                />
                <div className="flex items-center justify-between">
                  <button
                    type="button"
                    onClick={handleValidateJson}
                    className="text-xs font-semibold text-[#0B3C9D] hover:underline flex items-center gap-1"
                  >
                    <CheckCircle2 size={14} />
                    <span>Validate JSON Schema</span>
                  </button>
                  {jsonValidation && (
                    <span
                      className={`text-xs font-medium ${
                        jsonValidation.valid ? 'text-emerald-700' : 'text-red-600'
                      }`}
                    >
                      {jsonValidation.message}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* TEST RULE MODAL                                                           */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isTestModalOpen}
        onClose={() => setIsTestModalOpen(false)}
        title={`Simulate & Test: ${selectedRule?.code || 'Rule'}`}
        subtitle="Evaluate this regulatory rule in a sandbox environment without altering any database records"
        maxWidth="max-w-[840px]"
        footer={
          <div className="flex items-center justify-between w-full">
            <button
              type="button"
              onClick={() => setIsTestModalOpen(false)}
              className="h-11 px-5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
            >
              Close
            </button>
            <button
              type="button"
              disabled={isTesting}
              onClick={handleRunTest}
              className="inline-flex items-center gap-2 h-11 px-6 rounded-xl bg-[#0B3C9D] text-white text-sm font-bold hover:bg-[#0F2A5C] transition-colors shadow-sm disabled:opacity-50"
            >
              <Play size={16} />
              <span>{isTesting ? 'Evaluating...' : 'Execute Simulation'}</span>
            </button>
          </div>
        }
      >
        <div className="space-y-6">
          <div className="flex items-center gap-4 border-b border-slate-200 pb-2">
            <button
              type="button"
              onClick={() => setTestMode('app')}
              className={`text-xs font-bold pb-2 border-b-2 transition-colors ${
                testMode === 'app' ? 'border-[#0B3C9D] text-[#0B3C9D]' : 'border-transparent text-slate-500'
              }`}
            >
              Choose Registered Application
            </button>
            <button
              type="button"
              onClick={() => setTestMode('custom')}
              className={`text-xs font-bold pb-2 border-b-2 transition-colors ${
                testMode === 'custom' ? 'border-[#0B3C9D] text-[#0B3C9D]' : 'border-transparent text-slate-500'
              }`}
            >
              Paste Custom Context (JSON)
            </button>
          </div>

          {testMode === 'app' ? (
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Select Application
              </label>
              <select
                value={selectedAppId}
                onChange={(e) => setSelectedAppId(e.target.value)}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-semibold text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              >
                {applications.map((app) => (
                  <option key={app.id} value={app.id}>
                    {app.application_id} - {app.institute_name} ({app.category})
                  </option>
                ))}
              </select>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Evaluation Context Payload (JSON)
              </label>
              <textarea
                rows={6}
                value={customContextJson}
                onChange={(e) => setCustomContextJson(e.target.value)}
                className="w-full p-3 font-mono text-xs bg-slate-900 text-emerald-400 rounded-lg focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
            </div>
          )}

          {/* Test Results */}
          {testResult && (
            <div
              className={`p-5 rounded-xl border ${
                testResult.passed
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                  : 'bg-red-50 border-red-200 text-red-900'
              }`}
            >
              <div className="flex items-center justify-between pb-3 border-b border-black/10">
                <span className="text-xs font-bold uppercase tracking-wider">
                  Simulation Outcome: {testResult.passed ? 'PASS' : 'FAIL'}
                </span>
                <StatusPill status={testResult.passed ? 'PASS' : 'FAIL'} />
              </div>
              <p className="text-sm font-semibold mt-3">{testResult.message}</p>
              {testResult.evaluated_context_summary && (
                <div className="mt-3 pt-3 border-t border-black/10 text-xs space-y-1 text-slate-600">
                  <p>Application: <strong>{testResult.evaluated_context_summary.application_id}</strong></p>
                  <p>Institute: <strong>{testResult.evaluated_context_summary.institute_name}</strong></p>
                </div>
              )}
            </div>
          )}
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* PUBLISH CONFIRMATION MODAL                                                */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        title="Confirm RuleSet Release"
        subtitle="Publish an immutable snapshot of all active rules, document types, and checklists"
        maxWidth="max-w-[840px]"
        footer={
          <>
            <button
              type="button"
              onClick={() => setIsPublishModalOpen(false)}
              className="h-11 px-5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirmPublish}
              className="h-11 px-6 rounded-xl text-sm font-bold bg-[#0B3C9D] text-white hover:bg-[#0F2A5C] shadow-sm transition-colors"
            >
              Confirm & Publish
            </button>
          </>
        }
      >
        <div className="space-y-6">
          <p className="text-xs text-slate-600 leading-relaxed">
            Publishing creates an immutable snapshot of all active rules, document types, and checklists. Once published, live institute validations will immediately execute against this RuleSet.
          </p>

          {publishPreview && (
            <div className="bg-slate-50 rounded-xl border border-slate-200 p-5 space-y-3 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Currently Active Version:</span>
                <span className="font-bold text-[#0F2A5C]">{publishPreview.active_ruleset_version || 'None'}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Total Rules Bound:</span>
                <span className="font-bold text-[#0F2A5C]">{publishPreview.total_rules_to_publish}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">New Rules in Draft to Publish:</span>
                <span className="font-bold text-emerald-700">+{publishPreview.new_rules.length}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Modified Rules to Promote:</span>
                <span className="font-bold text-orange-600">{publishPreview.modified_rules.length}</span>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                RuleSet Label *
              </label>
              <input
                type="text"
                value={publishForm.name}
                onChange={(e) => setPublishForm({ ...publishForm, name: e.target.value })}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Version Tag *
              </label>
              <input
                type="text"
                value={publishForm.version_label}
                onChange={(e) => setPublishForm({ ...publishForm, version_label: e.target.value })}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-mono font-bold focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
            </div>
          </div>
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* VERSION DIFF MODAL                                                        */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isDiffModalOpen}
        onClose={() => setIsDiffModalOpen(false)}
        title={`Version Diff: ${diffRuleCode}`}
        subtitle="Side-by-side comparison between regulatory rule snapshot revisions"
        maxWidth="max-w-[880px]"
        footer={
          <button
            type="button"
            onClick={() => setIsDiffModalOpen(false)}
            className="h-11 px-6 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
          >
            Close
          </button>
        }
      >
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-3 bg-slate-50 p-4 rounded-xl border border-slate-200">
            <span className="text-xs font-semibold text-slate-600">Compare version:</span>
            <input
              type="number"
              value={diffV1}
              min={1}
              onChange={(e) => setDiffV1(parseInt(e.target.value) || 1)}
              className="w-20 h-10 px-3 rounded-lg border border-slate-300 text-xs font-mono font-bold"
            />
            <span className="text-xs font-semibold text-slate-400">with</span>
            <input
              type="number"
              value={diffV2}
              min={1}
              onChange={(e) => setDiffV2(parseInt(e.target.value) || 2)}
              className="w-20 h-10 px-3 rounded-lg border border-slate-300 text-xs font-mono font-bold"
            />
            <button
              onClick={() => loadDiff(diffRuleCode, diffV1, diffV2)}
              className="h-10 px-4 bg-[#0B3C9D] text-white text-xs font-bold rounded-lg hover:bg-[#0F2A5C] transition-colors"
            >
              Compute Diff
            </button>
          </div>

          {isLoadingDiff ? (
            <p className="text-xs text-slate-500 py-6 text-center">Loading diff...</p>
          ) : diffData && Object.keys(diffData.differences).length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {Object.entries(diffData.differences).map(([key, change]) => (
                <div key={key} className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs">
                  <span className="font-bold text-[#0B3C9D] font-mono text-sm">{key}</span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                    <div className="p-3 bg-red-50 text-red-900 rounded-lg font-mono text-xs overflow-x-auto border border-red-200">
                      <span className="font-bold block text-red-700 mb-1">Version {diffV1}:</span>
                      <pre className="text-[11px] whitespace-pre-wrap">{JSON.stringify(change.from, null, 2)}</pre>
                    </div>
                    <div className="p-3 bg-emerald-50 text-emerald-900 rounded-lg font-mono text-xs overflow-x-auto border border-emerald-200">
                      <span className="font-bold block text-emerald-700 mb-1">Version {diffV2}:</span>
                      <pre className="text-[11px] whitespace-pre-wrap">{JSON.stringify(change.to, null, 2)}</pre>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-500 py-6 text-center">
              No field differences between version {diffV1} and {diffV2}.
            </p>
          )}
        </div>
      </Modal>

      {/* ========================================================================= */}
      {/* RULE DETAIL & VERSION SNAPSHOTS MODAL                                     */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        title={`Audit & Version History: ${selectedRuleDetail?.code || ''}`}
        subtitle="Append-only regulatory change trail and immutable historical versions"
        maxWidth="max-w-[840px]"
        footer={
          <button
            type="button"
            onClick={() => setIsDetailModalOpen(false)}
            className="h-11 px-6 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
          >
            Close
          </button>
        }
      >
        <div className="space-y-6">
          {selectedRuleDetail && (
            <>
              <div className="bg-slate-50 p-5 rounded-xl border border-slate-200 text-xs space-y-2">
                <p><strong>Code:</strong> <span className="font-mono text-[#0B3C9D] font-bold">{selectedRuleDetail.code}</span></p>
                <p><strong>Title:</strong> {selectedRuleDetail.title}</p>
                <p><strong>Current Version:</strong> v{selectedRuleDetail.current_version}</p>
                <p><strong>Status:</strong> {selectedRuleDetail.status}</p>
              </div>

              <h4 className="text-xs font-bold uppercase text-slate-600 tracking-wider">
                Historical Version Snapshots ({selectedRuleDetail.versions?.length || 0})
              </h4>

              <div className="space-y-3 max-h-72 overflow-y-auto">
                {selectedRuleDetail.versions?.length === 0 ? (
                  <p className="text-xs text-slate-400">No prior snapshot versions recorded.</p>
                ) : (
                  selectedRuleDetail.versions?.map((ver) => (
                    <div key={ver.id} className="p-4 bg-white border border-slate-200 rounded-xl text-xs space-y-1">
                      <div className="flex justify-between font-bold text-[#0F2A5C]">
                        <span>Version {ver.version_no}</span>
                        <span className="text-slate-400 font-normal">
                          {new Date(ver.changed_at).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-slate-600">{ver.change_note || 'Standard version iteration'}</p>
                    </div>
                  ))
                )}
              </div>
            </>
          )}
        </div>
      </Modal>
    </div>
  );
};
