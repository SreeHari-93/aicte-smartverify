import { apiClient } from './client';

export interface DashboardData {
  institute_id: number;
  aicte_institute_id: string;
  name: string;
  state: string;
  stats: {
    filed: number;
    approved: number;
    pending: number;
    rejected: number;
  };
  accreditation?: {
    nirf_rank: number;
    naac_grade: string;
    nba_accredited_courses: number;
    college_code: string;
    location_address: string;
    phone: string;
  };
  courses: Array<{
    id: number;
    name: string;
    level: string;
    intake: number;
  }>;
}

export interface CertificateItem {
  id: number;
  application_id?: string;
  name: string;
  certificate_id: string;
  issue_date: string;
  expiry_date: string;
  document_id?: number;
  status: 'Valid' | 'Expiring Soon' | 'Expired';
  days_until_expiry: number;
}

export interface CertificateListResponse {
  items: CertificateItem[];
  total: number;
  page: number;
  page_size: number;
  stats: {
    total: number;
    expiring_soon: number;
    expired: number;
    renewed: number;
  };
}

export interface UpcomingExpiry {
  id: number;
  name: string;
  certificate_id: string;
  expiry_date: string;
  days_until_expiry: number;
  day: number;
  month_name: string;
  year: number;
}

export interface ApplicationItem {
  id: number;
  application_id: string;
  category: string;
  academic_year: string;
  programme: string;
  status: 'DRAFT' | 'SUBMITTED' | 'UNDER_REVIEW' | 'APPROVED' | 'REJECTED';
  filed_on?: string;
  created_at: string;
}

export interface ApplicationListResponse {
  items: ApplicationItem[];
  stats: {
    draft: number;
    submitted: number;
    under_review: number;
    approved: number;
    rejected: number;
    total: number;
  };
}

export interface RuleVersionEntry {
  version: string;
  date: string;
  note: string;
}

export interface RuleItem {
  id: number;
  rule_code: string;
  category: string;
  title: string;
  description: string;
  handbook_reference: string;
  version: string;
  is_mandatory: boolean;
  rule_type: 'MANDATORY' | 'ADVISORY';
  ai_checks: string[];
  evidence_required: string[];
  applies_to: string[];
  version_history: RuleVersionEntry[];
  created_at?: string;
  updated_at?: string;
}

export interface RuleGroup {
  category: string;
  total_count: number;
  mandatory_count: number;
  advisory_count: number;
  rules: RuleItem[];
}

export interface RuleSummary {
  total: number;
  mandatory: number;
  advisory: number;
  categories_count: number;
  category_counts: Record<string, number>;
}

export interface RulesResponse {
  summary: RuleSummary;
  groups: RuleGroup[];
}

export interface DocumentItem {
  id: number;
  original_filename: string;
  document_type_code?: string;
  file_size: number;
  mime_type: string;
  sha256_hash: string;
  status: string;
  ocr_status?: string;
  ocr_confidence?: number;
  verification_status?: string;
  verification_source?: string;
  created_at: string;
}

export interface CandidateOut {
  code: string;
  name: string;
  score: number;
  matched_keywords: string[];
}

export interface ClassificationOut {
  predicted_type: string;
  score: number;
  candidates: CandidateOut[];
  mismatch_flag: boolean;
  warning_message?: string;
}

export interface ExtractedFieldItem {
  id?: number;
  key: string;
  value?: string;
  normalized_value?: string;
  confidence: number;
  page_no: number;
  bbox?: number[];
  source: string;
  needs_review: boolean;
  verified_by_user: boolean;
  corrected_value?: string;
  effective_value?: string;
}

export interface VerificationComparison {
  field: string;
  submitted: any;
  official: any;
  matched: boolean;
  similarity_score?: number;
}

export interface VerificationInfo {
  id?: number;
  status: string;
  source_name: string;
  source_ref?: string;
  checked_at?: string;
  is_simulated?: boolean;
  disclaimer?: string;
  matched_fields: string[];
  mismatched_fields: Array<{ field: string; submitted: any; official: any }>;
  all_comparisons: VerificationComparison[];
  message?: string;
  manual_decision?: string;
  manual_reason?: string;
}

export interface DocumentExtractionData {
  document_id: number;
  filename: string;
  document_type_code?: string;
  ocr_status: string;
  classification?: ClassificationOut;
  fields: ExtractedFieldItem[];
  expiry_date?: string;
  issue_date?: string;
  is_expired?: boolean;
  days_remaining?: number;
  verification?: VerificationInfo;
}

export interface ChecklistItemReadiness {
  checklist_item_id: number;
  document_type_code: string;
  document_type_name: string;
  is_mandatory: boolean;
  status: string;
  document_id?: number;
  document_filename?: string;
  min_validity_days_remaining?: number;
  days_remaining?: number;
  expiry_date?: string;
  is_duplicate: boolean;
  duplicate_with_id?: number;
  help_text?: string;
}

export interface FieldProblem {
  document_id?: number;
  document_type: string;
  page_no: number;
  field_key: string;
  problem: string;
  value?: string;
}

export interface ApplicationReadinessData {
  application_id: number;
  application_number: string;
  category: string;
  ruleset_name: string;
  ruleset_version: string;
  readiness_percentage: number;
  status: string;
  total_items: number;
  ready_items: number;
  missing_items: string[];
  items: ChecklistItemReadiness[];
  field_problems: FieldProblem[];
  duplicates: any[];
}

export interface InstituteChecklistItem {
  id: number;
  document_type_code: string;
  document_type_name: string;
  description?: string;
  issuing_authority?: string;
  is_mandatory: boolean;
  status: 'missing' | 'uploaded' | 'expired';
  uploaded_document_id?: number;
  uploaded_filename?: string;
  uploaded_at?: string;
  min_validity_days_remaining?: number;
  help_text?: string;
}

export interface InstituteChecklistResponse {
  category_code: string;
  category_name: string;
  total_required: number;
  uploaded_count: number;
  missing_count: number;
  items: InstituteChecklistItem[];
}

export interface ValidationCheck {
  check: string;
  result: 'Pass' | 'Warning' | 'Fail';
  evidence: string;
  suggested_action: string;
  verification_status?: string;
  source_name?: string;
}

export interface ValidationResponse {
  application_id: string;
  status: string;
  checks: ValidationCheck[];
}

export interface ValidationFindingItem {
  id?: number;
  rule_code: string;
  rule_version?: string;
  rule_title?: string;
  severity: string;
  status: string;
  reason?: string;
  evidence_json: any[];
  suggested_action?: string;
  created_at?: string;
}

export interface ValidationRunDiff {
  previous_run_id?: number;
  newly_failed: string[];
  newly_fixed: string[];
  still_open: string[];
  newly_failed_count: number;
  newly_fixed_count: number;
  still_open_count: number;
}

export interface ValidationRunData {
  id: number;
  application_id: number;
  application_number: string;
  ruleset_id?: number;
  ruleset_version?: string;
  status: string;
  overall_status: string;
  score: number;
  blocker_count: number;
  major_count: number;
  minor_count: number;
  advisory_count: number;
  started_at: string;
  finished_at?: string;
  findings: ValidationFindingItem[];
  diff?: ValidationRunDiff;
}

export interface ComplaintEvent {
  id: number;
  action: string;
  notes: string;
  created_by: string;
  created_at: string;
}

export interface ComplaintItem {
  id: number;
  ticket_id: string;
  application_id?: number;
  category: string;
  subject: string;
  description: string;
  status: 'Open' | 'In Progress' | 'Resolved';
  created_at: string;
  updated_at: string;
  events: ComplaintEvent[];
}

export interface ReportItem {
  id: number;
  report_type: string;
  format: 'PDF' | 'CSV';
  date_range: string;
  filename: string;
  file_size: number;
  created_at: string;
}

export interface NotificationItem {
  id: number;
  title: string;
  message: string;
  type: string;
  link?: string;
  is_read: boolean;
  created_at: string;
}

export const instituteApi = {
  getDashboard: async (): Promise<DashboardData> => {
    const res = await apiClient.get<DashboardData>('/api/institute/dashboard');
    return res.data;
  },

  getCertificates: async (params?: {
    search?: string;
    status?: string;
    page?: number;
    page_size?: number;
  }): Promise<CertificateListResponse> => {
    const res = await apiClient.get<CertificateListResponse>('/api/institute/certificates', { params });
    return res.data;
  },

  getUpcomingCertificates: async (limit: number = 6): Promise<UpcomingExpiry[]> => {
    const res = await apiClient.get<UpcomingExpiry[]>('/api/institute/certificates/upcoming', {
      params: { limit },
    });
    return res.data;
  },

  renewCertificate: async (
    certificateId: number,
    payload: { new_issue_date: string; new_expiry_date: string; document_id?: number }
  ) => {
    const res = await apiClient.post(`/api/institute/certificates/${certificateId}/renew`, payload);
    return res.data;
  },

  getApplications: async (): Promise<ApplicationListResponse> => {
    const res = await apiClient.get<ApplicationListResponse>('/api/institute/applications');
    return res.data;
  },

  createApplicationDraft: async (payload: {
    category: string;
    academic_year: string;
    programme: string;
  }) => {
    const res = await apiClient.post('/api/institute/applications', payload);
    return res.data;
  },

  getRules: async (params?: {
    q?: string;
    search?: string;
    category?: string;
    type?: string;
    sort?: string;
  }): Promise<RulesResponse> => {
    const res = await apiClient.get<RulesResponse>('/api/institute/rules', { params });
    return res.data;
  },

  getDocuments: async (): Promise<DocumentItem[]> => {
    const res = await apiClient.get<DocumentItem[]>('/api/institute/documents');
    return res.data;
  },

  getChecklist: async (category: string = 'EOA', applicationId?: number): Promise<InstituteChecklistResponse> => {
    const params = new URLSearchParams({ category });
    if (applicationId) params.append('application_id', applicationId.toString());
    const res = await apiClient.get<InstituteChecklistResponse>(`/api/institute/checklist?${params.toString()}`);
    return res.data;
  },

  uploadDocument: async (file: File, applicationId?: number, documentTypeCode?: string): Promise<DocumentItem> => {
    const formData = new FormData();
    formData.append('file', file);
    if (applicationId) {
      formData.append('application_id', applicationId.toString());
    }
    if (documentTypeCode) {
      formData.append('document_type_code', documentTypeCode);
    }
    const res = await apiClient.post<DocumentItem>('/api/institute/documents', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  deleteDocument: async (id: number) => {
    const res = await apiClient.delete(`/api/institute/documents/${id}`);
    return res.data;
  },

  retryDocument: async (id: number) => {
    const res = await apiClient.post(`/api/institute/documents/${id}/retry`);
    return res.data;
  },

  cleanupPlaceholders: async (): Promise<{ message: string; deleted_count: number; deleted_ids: number[] }> => {
    const res = await apiClient.post<{ message: string; deleted_count: number; deleted_ids: number[] }>(
      '/api/institute/documents/cleanup-placeholders'
    );
    return res.data;
  },

  getValidationReport: async (appId: string): Promise<ValidationResponse> => {
    const res = await apiClient.get<ValidationResponse>(`/api/institute/validation/${appId}`);
    return res.data;
  },

  runValidation: async (appId: string | number): Promise<ValidationRunData> => {
    const res = await apiClient.post<ValidationRunData>(`/api/institute/applications/${appId}/validate`);
    return res.data;
  },

  getLatestValidation: async (appId: string | number): Promise<ValidationRunData> => {
    const res = await apiClient.get<ValidationRunData>(`/api/institute/applications/${appId}/validation/latest`);
    return res.data;
  },

  getValidationHistory: async (appId: string | number): Promise<any[]> => {
    const res = await apiClient.get<any[]>(`/api/institute/applications/${appId}/validation/history`);
    return res.data;
  },

  getComplaints: async (): Promise<ComplaintItem[]> => {
    const res = await apiClient.get<ComplaintItem[]>('/api/institute/complaints');
    return res.data;
  },

  raiseComplaint: async (payload: {
    category: string;
    related_application_id?: number;
    subject: string;
    description: string;
    attachment_document_id?: number;
  }) => {
    const res = await apiClient.post('/api/institute/complaints', payload);
    return res.data;
  },

  generateReport: async (payload: {
    report_type: string;
    format: string;
    date_range: string;
    application_id?: string;
  }): Promise<ReportItem> => {
    const res = await apiClient.post<ReportItem>('/api/institute/reports/generate', payload);
    return res.data;
  },

  getReports: async (): Promise<ReportItem[]> => {
    const res = await apiClient.get<ReportItem[]>('/api/institute/reports');
    return res.data;
  },

  getNotifications: async (): Promise<{ items: NotificationItem[]; unread_count: number }> => {
    const res = await apiClient.get<{ items: NotificationItem[]; unread_count: number }>(
      '/api/institute/notifications'
    );
    return res.data;
  },

  markNotificationRead: async (id: number) => {
    const res = await apiClient.patch(`/api/institute/notifications/${id}/read`);
    return res.data;
  },

  markAllNotificationsRead: async () => {
    const res = await apiClient.patch('/api/institute/notifications/read-all');
    return res.data;
  },

  getDocumentExtraction: async (docId: number): Promise<DocumentExtractionData> => {
    const res = await apiClient.get<DocumentExtractionData>(`/api/institute/documents/${docId}/extraction`);
    return res.data;
  },

  correctField: async (docId: number, key: string, corrected_value: string) => {
    const res = await apiClient.patch(`/api/institute/documents/${docId}/fields/${key}`, {
      corrected_value,
    });
    return res.data;
  },

  verifyDocument: async (docId: number) => {
    const res = await apiClient.post(`/api/institute/documents/${docId}/verify`);
    return res.data;
  },

  getDocumentVerification: async (docId: number) => {
    const res = await apiClient.get(`/api/institute/documents/${docId}/verification`);
    return res.data;
  },

  getApplicationReadiness: async (appId: number): Promise<ApplicationReadinessData> => {
    const res = await apiClient.get<ApplicationReadinessData>(`/api/institute/applications/${appId}/readiness`);
    return res.data;
  },

  getWhyFailed: async (appId: string | number, lang: 'en' | 'hi' = 'en'): Promise<WhyFailedData> => {
    const res = await apiClient.get<WhyFailedData>(`/api/institute/applications/${appId}/why-failed?lang=${lang}`);
    return res.data;
  },

  getEvidenceGraph: async (appId: string | number): Promise<EvidenceGraphData> => {
    const res = await apiClient.get<EvidenceGraphData>(`/api/institute/applications/${appId}/evidence-graph`);
    return res.data;
  },

  getDocumentAnomalies: async (docId: number): Promise<InstituteAnomalyFlag[]> => {
    const res = await apiClient.get<InstituteAnomalyFlag[]>(`/api/institute/documents/${docId}/anomalies`);
    return res.data;
  },

  getAnomalyOverlayUrl: (docId: number, flagId: number): string => {
    return `/api/institute/documents/${docId}/anomalies/${flagId}/overlay`;
  },

  runAnomalyScan: async (appId: string | number) => {
    const res = await apiClient.post(`/api/institute/applications/${appId}/anomaly-scan`);
    return res.data;
  },
};

export interface EvidenceGraphNode {
  id: string;
  type: 'institute' | 'application' | 'document' | 'field' | 'verification' | 'anomaly_flag' | string;
  label: string;
  properties: Record<string, any>;
}

export interface EvidenceGraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label: string;
  properties?: Record<string, any>;
}

export interface EvidenceGraphConflict {
  type: string;
  field: string;
  doc_id_1: number;
  doc_id_2: number;
  doc_file_1: string;
  doc_file_2: string;
  value_1: any;
  value_2: any;
  reason: string;
}

export interface EvidenceGraphSummary {
  node_count: number;
  edge_count: number;
  conflict_count: number;
  anomaly_flag_count: number;
  documents_count: number;
}

export interface EvidenceGraphData {
  application_id: string;
  application_pk: number;
  institute_id: number;
  institute_name: string;
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
  conflicts: EvidenceGraphConflict[];
  summary: EvidenceGraphSummary;
}

export interface InstituteAnomalyFlag {
  id: number;
  document_id: number;
  detector: string;
  code: string;
  group_key?: string;
  severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH';
  reason: string;
  evidence_json?: Array<Record<string, any>>;
  has_overlay?: boolean;
  recommended_action: string;
  review_status: string;
  created_at: string;
}

export interface RootCauseItem {
  cause_code: string;
  headline: string;
  affected_rule_codes: string[];
  severity: string;
  evidence: Array<Record<string, any>>;
  fixable_by_institute: boolean;
  ordered_suggested_actions: string[];
  needs_official_review: boolean;
  finding_ids: number[];
}

export interface HowToFixItem {
  step: string;
  effort: string;
}

export interface WhyFailedData {
  headline: string;
  plain_summary: string;
  root_causes: RootCauseItem[];
  how_to_fix: HowToFixItem[];
  reasons: Array<{
    cause_code: string;
    explanation: string;
    finding_codes: string[];
  }>;
  what_officials_will_review?: string;
  disclaimer: string;
  lang: string;
}

