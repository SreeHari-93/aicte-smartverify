import { apiClient } from './client';

// EVC Types
export interface CommitteeMember {
  id?: number;
  name: string;
  email: string;
  role?: string;
  institution?: string;
  region?: string;
}

export interface EvcRecordItem {
  id: number;
  application_id: number;
  application_code?: string;
  institute_name: string;
  institute_state?: string;
  category?: string;
  workflow_id?: number;
  is_new_institution: boolean;
  committee_members: CommitteeMember[];
  proposed_date?: string;
  confirmed_date?: string;
  status: 'PENDING_SCHEDULING' | 'SCHEDULED' | 'RESCHEDULED' | 'COMPLETED' | 'CANCELLED';
  report_file_path?: string;
  report_original_filename?: string;
  report_uploaded_at?: string;
  remarks?: string;
  scheduling_deadline: string;
  completion_deadline: string;
  created_at: string;
  updated_at: string;
}

// Undertaking Types
export interface UndertakingTemplate {
  category: string;
  title: string;
  condition: string;
  default_sla_days: number;
}

export interface UndertakingItem {
  id: number;
  application_id: number;
  application_code?: string;
  institute_id: number;
  institute_name: string;
  condition: string;
  category: 'lease' | 'accreditation' | 'infrastructure' | 'faculty' | 'other' | string;
  due_date: string;
  status: 'ACTIVE' | 'SUBMITTED' | 'UNDER_VERIFICATION' | 'FULFILLED' | 'OVERDUE' | 'ESCALATED' | 'CLOSED' | 'PENDING' | 'VERIFIED' | string;
  evidence_original_filename?: string;
  evidence_document_id?: number;
  evidence_remarks?: string;
  evidence_submitted_at?: string;
  history: Array<{
    action: string;
    from_status?: string;
    to_status: string;
    reason: string;
    performed_by: string;
    timestamp: string;
    file?: string;
  }>;
  created_by_officer_id?: number;
  verification_reason?: string;
  created_at: string;
  updated_at: string;
}

// Document Validity Types
export interface ValidityRecordItem {
  id: number;
  document_id?: number;
  institute_id: number;
  institute_name: string;
  institute_state?: string;
  application_id?: number;
  application_code?: string;
  document_type_code: string;
  document_name: string;
  certificate_number?: string;
  issuing_authority?: string;
  issue_date?: string;
  expiry_date: string;
  status: 'VALID' | 'EXPIRING_SOON' | 'EXPIRED' | 'RENEWAL_SUBMITTED' | 'RENEWED';
  days_left?: number;
  expiring_soon_window_days: number;
  renewal_document_id?: number;
  renewal_status?: string;
  renewal_submitted_at?: string;
  renewal_decision_reason?: string;
  is_lease: boolean;
  lessor?: string;
  lessee?: string;
  lease_start?: string;
  lease_end?: string;
  property_address?: string;
  created_at: string;
  updated_at: string;
}

export const evcApi = {
  getQueue: async (params?: { status?: string; search?: string }) => {
    const res = await apiClient.get<EvcRecordItem[]>('/api/evc/queue', { params });
    return res.data;
  },
  getUpcoming: async () => {
    const res = await apiClient.get<EvcRecordItem[]>('/api/evc/upcoming');
    return res.data;
  },
  getCommitteeMembers: async () => {
    const res = await apiClient.get<CommitteeMember[]>('/api/evc/committee-members');
    return res.data;
  },
  scheduleVisit: async (
    evcId: number,
    data: {
      proposed_date: string;
      confirmed_date: string;
      committee_members: CommitteeMember[];
      remarks?: string;
    }
  ) => {
    const res = await apiClient.post<{ success: boolean; evc: EvcRecordItem; conflict_warning: string | null }>(
      `/api/evc/${evcId}/schedule`,
      data
    );
    return res.data;
  },
  completeVisit: async (evcId: number, formData: FormData) => {
    const res = await apiClient.post<{ success: boolean; message: string; evc: EvcRecordItem }>(
      `/api/evc/${evcId}/complete`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return res.data;
  },
};

export const undertakingsApi = {
  list: async (params?: { status?: string; category?: string; application_id?: number; search?: string }) => {
    const res = await apiClient.get<UndertakingItem[]>('/api/undertakings', { params });
    return res.data;
  },
  getTemplates: async () => {
    const res = await apiClient.get<UndertakingTemplate[]>('/api/undertakings/templates');
    return res.data;
  },
  create: async (data: { application_id: number; condition: string; category: string; due_date: string }) => {
    const res = await apiClient.post<UndertakingItem>('/api/undertakings', data);
    return res.data;
  },
  submitEvidence: async (undertakingId: number, formData: FormData) => {
    const res = await apiClient.post<UndertakingItem>(
      `/api/undertakings/${undertakingId}/submit-evidence`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return res.data;
  },
  verify: async (undertakingId: number, data: { action: 'ACCEPT' | 'REQUEST_MORE' | 'REJECT'; reason: string }) => {
    const res = await apiClient.post<UndertakingItem>(`/api/undertakings/${undertakingId}/verify`, data);
    return res.data;
  },
};

export const validityApi = {
  list: async (params?: {
    region?: string;
    institute_id?: number;
    document_type?: string;
    status?: string;
    is_lease?: boolean;
    search?: string;
  }) => {
    const res = await apiClient.get<ValidityRecordItem[]>('/api/validity', { params });
    return res.data;
  },
  submitRenewal: async (recordId: number, formData: FormData) => {
    const res = await apiClient.post<ValidityRecordItem>(
      `/api/validity/${recordId}/renew`,
      formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return res.data;
  },
  decideRenewal: async (
    recordId: number,
    data: { action: 'ACCEPT' | 'REJECT'; reason: string; new_expiry_date?: string }
  ) => {
    const res = await apiClient.post<ValidityRecordItem>(`/api/validity/${recordId}/decide-renewal`, data);
    return res.data;
  },
  updateLease: async (
    recordId: number,
    data: {
      lessor?: string;
      lessee?: string;
      lease_start?: string;
      lease_end?: string;
      property_address?: string;
    }
  ) => {
    const res = await apiClient.patch<ValidityRecordItem>(`/api/validity/${recordId}/lease`, data);
    return res.data;
  },
};

