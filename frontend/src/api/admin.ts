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
};

