import { apiClient } from './client';

export interface DocumentTypeOut {
  id: number;
  code: string;
  name: string;
  description?: string;
  issuing_authority?: string;
  accepted_formats: string[];
  max_size_mb: number;
  has_expiry: boolean;
  default_validity_months?: number;
  verification_method: string;
  authority_adapter?: string;
  statutory_verification_applies?: boolean;
  extraction_schema?: Array<{ key: string; label: string; type: string; required?: boolean }>;
  keywords?: string[];
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentTypeCreate {
  code: string;
  name: string;
  description?: string;
  issuing_authority?: string;
  accepted_formats?: string[];
  max_size_mb?: number;
  has_expiry?: boolean;
  default_validity_months?: number;
  verification_method?: string;
  authority_adapter?: string;
  statutory_verification_applies?: boolean;
  extraction_schema?: Array<{ key: string; label: string; type: string; required?: boolean }>;
  keywords?: string[];
  is_active?: boolean;
}

export interface DocumentTypeUpdate extends Partial<DocumentTypeCreate> {}

export interface ApplicationCategoryOut {
  id: number;
  code: string;
  name: string;
  description?: string;
  is_active: boolean;
}

export interface ChecklistItemOut {
  id: number;
  category_id: number;
  ruleset_id?: number;
  institute_type?: string;
  min_count: number;
  document_type_id: number;
  document_type?: DocumentTypeOut;
  is_mandatory: boolean;
  condition?: Record<string, any>;
  min_validity_days_remaining?: number;
  max_age_days?: number;
  display_order: number;
  help_text?: string;
  is_active: boolean;
  created_at?: string;
}

export interface ChecklistItemCreate {
  document_type_id: number;
  ruleset_id?: number;
  institute_type?: string;
  min_count?: number;
  is_mandatory?: boolean;
  condition?: Record<string, any>;
  min_validity_days_remaining?: number;
  max_age_days?: number;
  display_order?: number;
  help_text?: string;
  is_active?: boolean;
}

export interface ChecklistItemUpdate extends Partial<ChecklistItemCreate> {}

export interface RuleVersionOut {
  id: number;
  rule_id: number;
  version_no: number;
  change_note?: string;
  snapshot: Record<string, any>;
  changed_by?: number;
  changed_at: string;
}

export interface RuleOut {
  id: number;
  code: string;
  title: string;
  description?: string;
  handbook_ref?: string;
  rule_type: string;
  severity: string;
  mandatory: boolean;
  applies_to_categories?: string[];
  definition?: Record<string, any>;
  ai_checks?: string[];
  evidence_required?: string[];
  suggested_action?: string;
  status: string;
  current_version: number;
  is_active: boolean;
  created_by?: number;
  updated_by?: number;
  created_at?: string;
  updated_at?: string;
}

export interface RuleDetailOut extends RuleOut {
  versions: RuleVersionOut[];
}

export interface RuleCreate {
  code: string;
  title: string;
  description?: string;
  handbook_ref?: string;
  rule_type?: string;
  severity?: string;
  mandatory?: boolean;
  applies_to_categories?: string[];
  definition?: Record<string, any>;
  ai_checks?: string[];
  evidence_required?: string[];
  suggested_action?: string;
  status?: string;
  is_active?: boolean;
}

export interface RuleUpdate {
  expected_version: number;
  change_note?: string;
  title?: string;
  description?: string;
  handbook_ref?: string;
  rule_type?: string;
  severity?: string;
  mandatory?: boolean;
  applies_to_categories?: string[];
  definition?: Record<string, any>;
  ai_checks?: string[];
  evidence_required?: string[];
  suggested_action?: string;
  status?: string;
  is_active?: boolean;
}

export interface RuleSetOut {
  id: number;
  name: string;
  version_label: string;
  status: string;
  rules_count: number;
  published_at?: string;
  published_by?: number;
  created_at?: string;
}

export interface PublishPreviewOut {
  active_ruleset_name?: string;
  active_ruleset_version?: string;
  current_active_rules_count: number;
  new_rules: RuleOut[];
  modified_rules: Array<RuleOut & { changed_fields?: string[] }>;
  unchanged_rules_count: number;
  total_rules_to_publish: number;
  total_categories_count: number;
  total_checklists_count: number;
  total_document_types_count: number;
}

export interface RuleDiffOut {
  rule_code: string;
  version_1: number;
  version_2: number;
  differences: Record<string, { from: any; to: any }>;
}

export interface RuleSimulationRequest {
  definition: Record<string, any>;
  context?: Record<string, any>;
  rule_meta?: Record<string, any>;
  application_id?: number | string;
}

export interface RuleSimulationResponse {
  passed: boolean;
  message: string;
  details: Record<string, any>;
  rule_code: string;
  rule_title: string;
  severity: string;
  evaluated_context_summary?: {
    application_id?: string;
    category?: string;
    documents_count?: number;
    institute_name?: string;
  };
}

export interface DefinitionValidationResponse {
  valid: boolean;
  message: string;
  depth: number;
  errors: string[];
}

export interface AdminApplicationOut {
  id: number;
  application_id: string;
  institute_id: number;
  institute_name?: string;
  category: string;
  academic_year: string;
  status: string;
  filed_on?: string;
}

export interface AuditLogOut {
  id: number;
  user_id?: number;
  role?: string;
  ip_address?: string;
  action: string;
  reason?: string;
  details?: Record<string, any>;
  timestamp: string;
}

export const adminApi = {
  // 1. Rules
  listRules: async (params?: { category?: string; status?: string; severity?: string; rule_type?: string; search?: string; is_active?: boolean }) => {
    const res = await apiClient.get<RuleOut[]>('/api/v1/admin/rules', { params });
    return res.data;
  },
  getRule: async (code: string) => {
    const res = await apiClient.get<RuleDetailOut>(`/api/v1/admin/rules/${encodeURIComponent(code)}`);
    return res.data;
  },
  createRule: async (payload: RuleCreate) => {
    const res = await apiClient.post<RuleOut>('/api/v1/admin/rules', payload);
    return res.data;
  },
  updateRule: async (code: string, payload: RuleUpdate) => {
    const res = await apiClient.put<RuleOut>(`/api/v1/admin/rules/${encodeURIComponent(code)}`, payload);
    return res.data;
  },
  deleteRule: async (code: string) => {
    const res = await apiClient.delete<{ message: string }>(`/api/v1/admin/rules/${encodeURIComponent(code)}`);
    return res.data;
  },
  toggleRuleActive: async (code: string) => {
    const res = await apiClient.patch<RuleOut>(`/api/v1/admin/rules/${encodeURIComponent(code)}/toggle-active`);
    return res.data;
  },
  cloneRule: async (code: string, newCode: string, newTitle?: string) => {
    const res = await apiClient.post<RuleOut>(`/api/v1/admin/rules/${encodeURIComponent(code)}/clone`, {
      new_code: newCode,
      new_title: newTitle,
    });
    return res.data;
  },
  simulateRule: async (payload: RuleSimulationRequest) => {
    const res = await apiClient.post<RuleSimulationResponse>('/api/v1/admin/rules/simulate', payload);
    return res.data;
  },
  validateDefinition: async (definition: Record<string, any>) => {
    const res = await apiClient.post<DefinitionValidationResponse>('/api/v1/admin/rules/validate-definition', { definition });
    return res.data;
  },
  getRuleDiff: async (code: string, v1: number, v2: number) => {
    const res = await apiClient.get<RuleDiffOut>(`/api/v1/admin/rules/${encodeURIComponent(code)}/diff`, {
      params: { v1, v2 },
    });
    return res.data;
  },

  // 2. RuleSets & Publish Flow
  listRuleSets: async () => {
    const res = await apiClient.get<RuleSetOut[]>('/api/v1/admin/rulesets');
    return res.data;
  },
  getPublishPreview: async () => {
    const res = await apiClient.get<PublishPreviewOut>('/api/v1/admin/rulesets/preview-publish');
    return res.data;
  },
  publishRuleSet: async (payload: { name: string; version_label: string }) => {
    const res = await apiClient.post<RuleSetOut>('/api/v1/admin/rulesets/publish', payload);
    return res.data;
  },
  rollbackRuleSet: async (rulesetId: number) => {
    const res = await apiClient.post<{ message: string; restored_rules: number }>(`/api/v1/admin/rulesets/${rulesetId}/rollback`);
    return res.data;
  },

  // 3. Document Types
  listDocumentTypes: async (params?: { is_active?: boolean; search?: string }) => {
    const res = await apiClient.get<DocumentTypeOut[]>('/api/v1/admin/document-types', { params });
    return res.data;
  },
  getDocumentType: async (code: string) => {
    const res = await apiClient.get<DocumentTypeOut>(`/api/v1/admin/document-types/${encodeURIComponent(code)}`);
    return res.data;
  },
  createDocumentType: async (payload: DocumentTypeCreate) => {
    const res = await apiClient.post<DocumentTypeOut>('/api/v1/admin/document-types', payload);
    return res.data;
  },
  updateDocumentType: async (code: string, payload: DocumentTypeUpdate) => {
    const res = await apiClient.put<DocumentTypeOut>(`/api/v1/admin/document-types/${encodeURIComponent(code)}`, payload);
    return res.data;
  },
  deleteDocumentType: async (code: string) => {
    const res = await apiClient.delete<{ message: string }>(`/api/v1/admin/document-types/${encodeURIComponent(code)}`);
    return res.data;
  },

  // 4. Categories & Checklists
  listCategories: async (params?: { is_active?: boolean }) => {
    const res = await apiClient.get<ApplicationCategoryOut[]>('/api/v1/admin/categories', { params });
    return res.data;
  },
  getChecklist: async (categoryCode: string) => {
    const res = await apiClient.get<ChecklistItemOut[]>(`/api/v1/admin/checklists/${encodeURIComponent(categoryCode)}`);
    return res.data;
  },
  addChecklistItem: async (categoryCode: string, payload: ChecklistItemCreate) => {
    const res = await apiClient.post<ChecklistItemOut>(`/api/v1/admin/checklists/${encodeURIComponent(categoryCode)}/items`, payload);
    return res.data;
  },
  updateChecklistItem: async (categoryCode: string, itemId: number, payload: ChecklistItemUpdate) => {
    const res = await apiClient.put<ChecklistItemOut>(`/api/v1/admin/checklists/${encodeURIComponent(categoryCode)}/items/${itemId}`, payload);
    return res.data;
  },
  deleteChecklistItem: async (categoryCode: string, itemId: number) => {
    const res = await apiClient.delete<{ message: string }>(`/api/v1/admin/checklists/${encodeURIComponent(categoryCode)}/items/${itemId}`);
    return res.data;
  },
  reorderChecklist: async (categoryCode: string, items: Array<{ item_id: number; display_order: number }>) => {
    const res = await apiClient.post<{ message: string }>(`/api/v1/admin/checklists/${encodeURIComponent(categoryCode)}/reorder`, { items });
    return res.data;
  },

  // 5. Applications & Audit Logs
  listApplications: async () => {
    const res = await apiClient.get<AdminApplicationOut[]>('/api/v1/admin/applications');
    return res.data;
  },
  listAuditLogs: async (params?: { action?: string; user_id?: number; limit?: number; offset?: number }) => {
    const res = await apiClient.get<AuditLogOut[]>('/api/v1/admin/audit-logs', { params });
    return res.data;
  },

  // 6. Verification Queue & Decisions
  listVerificationQueue: async (params?: {
    status?: string;
    institute_id?: number;
    document_type?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const res = await apiClient.get<VerificationQueueItemDetailed[]>('/api/v1/admin/verification-queue', { params });
    return res.data;
  },
  reviewDocumentDecision: async (documentId: number, payload: { decision: string; reason: string }) => {
    const res = await apiClient.post<VerificationQueueItemDetailed>(`/api/v1/admin/documents/${documentId}/review-decision`, payload);
    return res.data;
  },
  assignDocumentOfficer: async (documentId: number, officerId?: number) => {
    const res = await apiClient.post<{ message: string; assigned_officer_id: number | null }>(`/api/v1/admin/documents/${documentId}/assign`, { officer_id: officerId });
    return res.data;
  },

  // 7. Anomalies
  listAnomalies: async (params?: {
    severity?: string;
    detector?: string;
    status?: string;
    institute_id?: number;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const res = await apiClient.get<AdminAnomalyFlagOut[]>('/api/v1/admin/anomalies', { params });
    return res.data;
  },
  recordAnomalyDecision: async (flagId: number, payload: { decision: string; note: string }) => {
    const res = await apiClient.post<AdminAnomalyFlagOut>(`/api/v1/admin/anomalies/${flagId}/decision`, payload);
    return res.data;
  },

  // 8. Complaints Inbox
  listComplaints: async (params?: {
    status?: string;
    category?: string;
    priority?: string;
    institute_id?: number;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const res = await apiClient.get<AdminComplaintOut[]>('/api/v1/admin/complaints', { params });
    return res.data;
  },
  getComplaintDetail: async (complaintId: number) => {
    const res = await apiClient.get<AdminComplaintOut>(`/api/v1/admin/complaints/${complaintId}`);
    return res.data;
  },
  replyComplaint: async (
    complaintId: number,
    payload: { notes: string; is_internal?: boolean; new_status?: string; assigned_to?: number }
  ) => {
    const res = await apiClient.post<AdminComplaintOut>(`/api/v1/admin/complaints/${complaintId}/reply`, payload);
    return res.data;
  },
  assignComplaintOfficer: async (complaintId: number, assignedTo?: number) => {
    const res = await apiClient.post<{ message: string; assigned_to: number | null }>(`/api/v1/admin/complaints/${complaintId}/assign`, { assigned_to: assignedTo });
    return res.data;
  },

  // 9. Dashboard Metrics
  getDashboardStats: async () => {
    const res = await apiClient.get<AdminDashboardStats>('/api/v1/admin/dashboard-stats');
    return res.data;
  },

  // 10. Reports Archive & Download
  listReports: async (limit: number = 100): Promise<AdminReportItem[]> => {
    const res = await apiClient.get<AdminReportItem[]>('/api/v1/admin/reports', { params: { limit } });
    return res.data;
  },
  downloadApplicationReportPdf: async (appId: string | number, lang: 'en' | 'hi' = 'en') => {
    const response = await apiClient.get(`/api/v1/admin/applications/${appId}/report.pdf`, {
      params: { lang },
      responseType: 'blob',
    });
    const blob = new Blob([response.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `validation_summary_${appId}_${lang}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
  downloadReportFile: async (reportId: number, filename?: string) => {
    const response = await apiClient.get(`/api/v1/admin/reports/${reportId}/download`, {
      responseType: 'blob',
    });
    const contentType = (response.headers['content-type'] as string) || 'application/octet-stream';
    const blob = new Blob([response.data], { type: contentType });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename || `report_${reportId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.parentNode?.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};

// -------------------------------------------------------------
// Stage 8-ii Interfaces
// -------------------------------------------------------------

export interface VerificationQueueItemDetailed {
  id: number;
  document_id: number;
  document_filename: string;
  document_type_code?: string;
  document_type_name?: string;
  institute_id: number;
  institute_name: string;
  status: string;
  original_status?: string;
  source_name?: string;
  source_ref?: string;
  checked_at?: string;
  created_at: string;
  age_days: number;
  assigned_officer_id?: number;
  assigned_officer_name?: string;
  file_size: number;
  mime_type?: string;
  manual_decision?: string;
  manual_reason?: string;
  manual_reviewed_by?: number;
  manual_reviewed_at?: string;
  message?: string;
  matched_fields: Array<Record<string, any>>;
  mismatched_fields: Array<Record<string, any>>;
  extracted_fields: Record<string, any>;
  official_values: Record<string, any>;
  timeline: Array<{
    event: string;
    timestamp?: string;
    actor: string;
    notes: string;
  }>;
}

export interface AdminAnomalyFlagOut {
  id: number;
  run_id: number;
  document_id: number;
  document_filename?: string;
  document_type_code?: string;
  institute_id?: number;
  institute_name?: string;
  detector: string;
  code: string;
  group_key?: string;
  severity: string;
  reason: string;
  confidence: number;
  recommended_action: string;
  review_status: string;
  reviewed_by?: number;
  reviewed_by_name?: string;
  review_note?: string;
  reviewed_at?: string;
  overlay_image_path?: string;
  has_overlay: boolean;
  evidence_json: Array<Record<string, any>>;
  created_at: string;
}

export interface ComplaintEventOut {
  id: number;
  complaint_id: number;
  action: string;
  notes: string;
  created_by: string;
  is_internal: boolean;
  created_at: string;
}

export interface AdminComplaintOut {
  id: number;
  ticket_id: string;
  institute_id: number;
  institute_name?: string;
  application_id?: number;
  application_ref?: string;
  attachment_document_id?: number;
  attachment_filename?: string;
  category: string;
  subject: string;
  description: string;
  status: string;
  priority: string;
  assigned_to?: number;
  assigned_officer_name?: string;
  created_at: string;
  updated_at: string;
  events: ComplaintEventOut[];
}

export interface AdminDashboardStats {
  pending_verifications_count: number;
  open_anomalies_count: number;
  open_complaints_count: number;
  total_rules_count: number;
  active_rules_count: number;
  draft_rules_count: number;
  document_types_count: number;
  checklists_count: number;
}

export interface AdminReportItem {
  id: number;
  institute_id: number;
  institute_name?: string;
  report_type: string;
  format: 'PDF' | 'CSV';
  date_range: string;
  filename: string;
  file_size: number;
  created_at: string;
  application_id?: string;
  language?: string;
  generated_by?: string;
}

