import { apiClient } from './client';

export interface WorkflowStage {
  id: number;
  template_id: number;
  sequence: number;
  stage_code: string;
  stage_name: string;
  responsible_role: string;
  sla_days: number;
  is_final_decision: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowTemplate {
  id: number;
  code: string;
  name: string;
  description?: string;
  stages: WorkflowStage[];
  created_at: string;
  updated_at: string;
}

export interface WorkflowHistory {
  id: number;
  workflow_id: number;
  action: string;
  from_stage?: string;
  to_stage?: string;
  performed_by_id?: number;
  performed_by_role: string;
  performed_by_name?: string;
  reason: string;
  details?: string;
  created_at: string;
}

export interface ApplicationWorkflow {
  id: number;
  application_id: number;
  application_code: string;
  institute_id: number;
  institute_name: string;
  category: string;
  template_code: string;
  template_name: string;
  current_stage_id?: number;
  current_stage_sequence: number;
  current_stage_name: string;
  assigned_officer_id?: number;
  assigned_officer_name?: string;
  region: string;
  stage_start: string;
  due_date: string;
  status: 'IN_PROGRESS' | 'RETURNED' | 'ON_HOLD' | 'COMPLETED';
  final_decision?: 'APPROVED' | 'REJECTED';
  final_decision_notes?: string;
  final_decision_by?: string;
  final_decision_at?: string;
  case_summary?: string;
  is_overdue: boolean;
  days_remaining: number;
  created_at: string;
  updated_at: string;
  stages: WorkflowStage[];
  history: WorkflowHistory[];
}

export interface OldestPendingCase {
  id: number;
  application_id: string;
  institute_name: string;
  category: string;
  stage_name: string;
  region: string;
  assigned_officer: string;
  age_days: number;
  due_date: string;
  status: string;
  sla_badge: 'ON TRACK' | 'DUE SOON' | 'OVERDUE';
}

export interface AgeingBucket {
  bucket: string;
  count: number;
  on_track: number;
  due_soon: number;
  overdue: number;
}

export interface StageAnalytic {
  stage_id: number;
  stage_name: string;
  sla_days: number;
  completed_cases: number;
  avg_days_spent: number;
  variance_days: number;
  status: 'ON_TRACK' | 'SLIGHT_DELAY' | 'BOTTLENECK';
}

export interface WorstOverdueStage {
  stage_name: string;
  overdue_count: number;
}

export interface OfficerWorkloadItem {
  officer_id: number;
  name?: string;
  email: string;
  role: string;
  region: string;
  assigned_count: number;
  overdue_count: number;
  completed_count: number;
}

export interface CommitteeWorkloadItem {
  member_id: number;
  name?: string;
  email: string;
  role: string;
  region: string;
  active_cases: number;
  scheduled_visits?: number;
  completed_visits?: number;
  visits_display: string;
}

export interface CommunicationTemplate {
  id: number;
  code: string;
  name: string;
  category: string;
  subject_template: string;
  body_template: string;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkflowDashboardData {
  counters: {
    total: number;
    in_progress: number;
    returned: number;
    on_hold: number;
    completed: number;
    overdue: number;
    due_in_7_days: number;
    open_undertakings?: number;
    documents_expiring?: number;
    evc_pending?: number;
  };
  stage_funnel: Array<{ stage: string; count: number }>;
  region_table: Array<{
    region: string;
    total: number;
    in_progress: number;
    returned: number;
    overdue: number;
  }>;
  officer_workload: OfficerWorkloadItem[];
  stage_analytics?: StageAnalytic[];
  worst_overdue_stage?: WorstOverdueStage | null;
  committee_workload?: CommitteeWorkloadItem[];
  oldest_pending: OldestPendingCase[];
  ageing_buckets: AgeingBucket[];
  user_scope: {
    role: string;
    region?: string;
    effective_region?: string;
  };
}

export interface WorkflowOfficer {
  id: number;
  email: string;
  role: string;
  region?: string;
}

export const workflowApi = {
  getTemplates: async (): Promise<WorkflowTemplate[]> => {
    const res = await apiClient.get<WorkflowTemplate[]>('/api/workflow/templates');
    return res.data;
  },

  updateStageSla: async (
    templateId: number,
    stageId: number,
    data: { sla_days: number; responsible_role?: string }
  ): Promise<WorkflowStage> => {
    const res = await apiClient.put<WorkflowStage>(
      `/api/workflow/templates/${templateId}/stages/${stageId}`,
      data
    );
    return res.data;
  },

  getDashboard: async (region?: string): Promise<WorkflowDashboardData> => {
    const res = await apiClient.get<WorkflowDashboardData>('/api/workflow/dashboard', {
      params: region ? { region } : undefined,
    });
    return res.data;
  },

  getApplications: async (params?: {
    region?: string;
    stage?: string;
    officer_id?: number;
    status_filter?: string;
    search?: string;
  }): Promise<ApplicationWorkflow[]> => {
    const res = await apiClient.get<ApplicationWorkflow[]>('/api/workflow/applications', {
      params,
    });
    return res.data;
  },

  getApplication: async (identifier: string | number): Promise<ApplicationWorkflow> => {
    const res = await apiClient.get<ApplicationWorkflow>(`/api/workflow/application/${identifier}`);
    return res.data;
  },

  advanceStage: async (
    workflowId: number,
    data: { reason: string; notes?: string }
  ): Promise<ApplicationWorkflow> => {
    const res = await apiClient.post<ApplicationWorkflow>(
      `/api/workflow/application/${workflowId}/advance`,
      data
    );
    return res.data;
  },

  returnWorkflow: async (
    workflowId: number,
    data: { reason: string; notes?: string }
  ): Promise<ApplicationWorkflow> => {
    const res = await apiClient.post<ApplicationWorkflow>(
      `/api/workflow/application/${workflowId}/return`,
      data
    );
    return res.data;
  },

  reassignOfficer: async (
    workflowId: number,
    data: { new_officer_id: number; reason: string }
  ): Promise<ApplicationWorkflow> => {
    const res = await apiClient.post<ApplicationWorkflow>(
      `/api/workflow/application/${workflowId}/reassign`,
      data
    );
    return res.data;
  },

  holdWorkflow: async (
    workflowId: number,
    data: { reason: string }
  ): Promise<ApplicationWorkflow> => {
    const res = await apiClient.post<ApplicationWorkflow>(
      `/api/workflow/application/${workflowId}/hold`,
      data
    );
    return res.data;
  },

  resumeWorkflow: async (
    workflowId: number,
    data: { reason: string }
  ): Promise<ApplicationWorkflow> => {
    const res = await apiClient.post<ApplicationWorkflow>(
      `/api/workflow/application/${workflowId}/resume`,
      data
    );
    return res.data;
  },

  recordDecision: async (
    workflowId: number,
    data: { decision: 'APPROVED' | 'REJECTED'; reason: string; notes?: string }
  ): Promise<ApplicationWorkflow> => {
    const res = await apiClient.post<ApplicationWorkflow>(
      `/api/workflow/application/${workflowId}/record-decision`,
      data
    );
    return res.data;
  },

  refreshSummary: async (workflowId: number): Promise<{ case_summary: string }> => {
    const res = await apiClient.post<{ case_summary: string }>(
      `/api/workflow/application/${workflowId}/summary`
    );
    return res.data;
  },

  getOfficers: async (): Promise<WorkflowOfficer[]> => {
    const res = await apiClient.get<WorkflowOfficer[]>('/api/workflow/officers');
    return res.data;
  },

  submitApplication: async (data: {
    category: string;
    academic_year?: string;
    programme?: string;
    intake?: number;
    details?: string;
    document_ids?: number[];
  }): Promise<ApplicationWorkflow> => {
    const res = await apiClient.post<ApplicationWorkflow>('/api/workflow/application/submit', data);
    return res.data;
  },

  resubmitApplication: async (
    applicationId: number,
    data: { response_text: string; document_ids?: number[] }
  ): Promise<ApplicationWorkflow> => {
    const res = await apiClient.post<ApplicationWorkflow>(
      `/api/workflow/application/${applicationId}/resubmit`,
      data
    );
    return res.data;
  },

  getCommunicationTemplates: async (): Promise<CommunicationTemplate[]> => {
    const res = await apiClient.get<CommunicationTemplate[]>('/api/workflow/communications/templates');
    return res.data;
  },

  updateCommunicationTemplate: async (
    templateId: number,
    data: { name?: string; subject_template?: string; body_template?: string; is_enabled?: boolean }
  ): Promise<CommunicationTemplate> => {
    const res = await apiClient.put<CommunicationTemplate>(
      `/api/workflow/communications/templates/${templateId}`,
      data
    );
    return res.data;
  },

  generateCommunication: async (data: {
    template_code: string;
    workflow_id: number;
    reason: string;
    target_email?: string;
  }): Promise<{
    success: boolean;
    template_code: string;
    subject: string;
    body: string;
    pdf_base64: string;
    notification_id?: number;
    email_status: string;
    disclaimer: string;
  }> => {
    const res = await apiClient.post('/api/workflow/communications/generate', data);
    return res.data;
  },

  getCategoryMappings: async (): Promise<{ category: string; template_code: string; description: string }[]> => {
    const res = await apiClient.get('/api/workflow/category-mappings');
    return res.data;
  },

  updateCategoryMappings: async (
    mappings: { category: string; template_code: string; description?: string }[]
  ): Promise<any> => {
    const res = await apiClient.put('/api/workflow/category-mappings', mappings);
    return res.data;
  },

  getSafeguardSettings: async (): Promise<Record<string, string>> => {
    const res = await apiClient.get('/api/workflow/settings/safeguards');
    return res.data;
  },

  updateSafeguardSettings: async (settings: Record<string, string>): Promise<any> => {
    const res = await apiClient.put('/api/workflow/settings/safeguards', settings);
    return res.data;
  },

  getIntegrationsStatus: async (): Promise<any> => {
    const res = await apiClient.get('/api/integrations/status');
    return res.data;
  },

  triggerSimulatedSync: async (): Promise<any> => {
    const res = await apiClient.post('/api/integrations/sync-feed');
    return res.data;
  },

  importFeedFile: async (file: File): Promise<any> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/api/integrations/import-feed', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },
};
