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
  created_at: string;
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
}

export interface ValidationResponse {
  application_id: string;
  status: string;
  checks: ValidationCheck[];
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

  getValidationReport: async (appId: string): Promise<ValidationResponse> => {
    const res = await apiClient.get<ValidationResponse>(`/api/institute/validation/${appId}`);
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
};
