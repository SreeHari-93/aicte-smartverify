import { apiClient } from './client';

export interface AlertItem {
  id: number;
  event_type: string;
  case_id: string;
  case_type?: string;
  recipient_role: string;
  due_date?: string;
  offset_days: number;
  title: string;
  message: string;
  link?: string;
  is_read: boolean;
  created_at?: string;
  institute_id?: number;
  details?: Record<string, any>;
  region?: string;
}

export interface NotificationRuleItem {
  id: number;
  event_type: string;
  title: string;
  offsets_days: number[];
  recipient_role: string;
  channel: string;
  message_template: string;
  is_enabled: boolean;
  updated_at?: string;
}

export interface EscalationMatrixItem {
  id: number;
  event_type: string;
  level: number;
  days_overdue: number;
  designated_role: string;
  is_enabled: boolean;
}

export interface EscalationRecordItem {
  id: number;
  case_id: string;
  case_type: string;
  event_type: string;
  level: number;
  notified_role: string;
  notified_user_email?: string;
  days_overdue: number;
  status: string;
  resolved_at?: string;
  created_at: string;
}

export interface SchedulerLogItem {
  id: number;
  run_at: string;
  simulated_clock?: string;
  items_checked: number;
  alerts_created: number;
  escalations_triggered: number;
  status: string;
  duration_ms: number;
  details?: Record<string, any>;
}

export interface DemoClockStatus {
  is_active: boolean;
  simulated_time?: string;
  effective_time: string;
  wall_clock: string;
}

export interface AuditTimelineEvent {
  source: 'WORKFLOW' | 'EVC' | 'UNDERTAKING' | 'ALERT' | 'ESCALATION' | 'AUDIT';
  action: string;
  title: string;
  actor: string;
  reason?: string;
  details?: any;
  timestamp: string;
}

export const alertsApi = {
  // Alert Centre
  getAlerts: async (params?: { event_type?: string; status_filter?: string; case_id?: string; unread_only?: boolean; page?: number; limit?: number }) => {
    const res = await apiClient.get('/api/alerts', { params });
    return res.data;
  },

  getUnreadCount: async () => {
    const res = await apiClient.get('/api/alerts/unread-count');
    return res.data;
  },

  markAlertRead: async (id: number) => {
    const res = await apiClient.post(`/api/alerts/${id}/read`);
    return res.data;
  },

  markAllAlertsRead: async () => {
    const res = await apiClient.post('/api/alerts/mark-all-read');
    return res.data;
  },

  // Notification Rules
  getRules: async () => {
    const res = await apiClient.get('/api/alerts/rules');
    return res.data as NotificationRuleItem[];
  },

  updateRule: async (id: number, payload: Partial<NotificationRuleItem>) => {
    const res = await apiClient.put(`/api/alerts/rules/${id}`, payload);
    return res.data;
  },

  // Escalation Matrix
  getEscalationMatrix: async () => {
    const res = await apiClient.get('/api/alerts/escalation-matrix');
    return res.data as EscalationMatrixItem[];
  },

  updateEscalationMatrix: async (id: number, payload: Partial<EscalationMatrixItem>) => {
    const res = await apiClient.put(`/api/alerts/escalation-matrix/${id}`, payload);
    return res.data;
  },

  getEscalationRecords: async (params?: { status_filter?: string; case_type?: string }) => {
    const res = await apiClient.get('/api/alerts/escalations', { params });
    return res.data as EscalationRecordItem[];
  },

  // Scheduler & Demo Clock
  triggerSchedulerScan: async () => {
    const res = await apiClient.post('/api/alerts/scheduler/run');
    return res.data;
  },

  getSchedulerLogs: async () => {
    const res = await apiClient.get('/api/alerts/scheduler/logs');
    return res.data as SchedulerLogItem[];
  },

  getDemoClock: async () => {
    const res = await apiClient.get('/api/alerts/demo-clock');
    return res.data as DemoClockStatus;
  },

  setDemoClock: async (simulated_date: string) => {
    const res = await apiClient.post('/api/alerts/demo-clock', { simulated_date });
    return res.data;
  },

  resetDemoClock: async () => {
    const res = await apiClient.delete('/api/alerts/demo-clock');
    return res.data;
  },

  // Consolidated Reports
  listConsolidatedReports: async () => {
    const res = await apiClient.get('/api/reports/consolidated/list');
    return res.data as { id: string; name: string }[];
  },

  downloadConsolidatedReport: async (
    report_type: string,
    format: 'PDF' | 'CSV',
    region?: string,
    start_date?: string,
    end_date?: string
  ) => {
    const res = await apiClient.get('/api/reports/consolidated/export', {
      params: {
        report_type,
        format,
        region: region && region !== 'ALL' ? region : undefined,
        start_date: start_date || undefined,
        end_date: end_date || undefined,
      },
      responseType: 'blob',
    });
    const blob = new Blob([res.data], { type: format === 'CSV' ? 'text/csv' : 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const regLabel = region && region !== 'ALL' ? `_${region.toUpperCase()}` : '_NATIONAL';
    const dateLabel = start_date && end_date ? `_${start_date}_to_${end_date}` : '';
    link.setAttribute('download', `AICTE_${report_type.toUpperCase()}${regLabel}${dateLabel}.${format.toLowerCase()}`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  getReportApplications: async (region?: string) => {
    const res = await apiClient.get('/api/reports/applications', {
      params: { region: region && region !== 'ALL' ? region : undefined },
    });
    return res.data as Array<{
      id: number;
      application_id: string;
      institute_id: number;
      institute_name: string;
      stage: string;
      region: string;
      category: string;
      status: string;
      created_at?: string;
      label: string;
    }>;
  },

  downloadApplicationSummaryPdf: async (applicationId: string, lang: 'en' | 'hi' = 'en') => {
    const res = await apiClient.get(`/api/v1/admin/applications/${applicationId}/report.pdf`, {
      params: { lang },
      responseType: 'blob',
    });
    const today = new Date().toISOString().slice(0, 10);
    const cleanCode = applicationId.replace(/[^a-zA-Z0-9_-]/g, '_');
    const filename = `${cleanCode}_summary_${today}.pdf`;

    const blob = new Blob([res.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    return filename;
  },

  // Synthetic Evaluation
  getSyntheticEvaluation: async () => {
    const res = await apiClient.get('/api/evaluation/synthetic-scenarios');
    return res.data;
  },

  triggerSyntheticEvaluation: async () => {
    const res = await apiClient.post('/api/evaluation/trigger-scenarios');
    return res.data;
  },

  // Unified Audit Timeline
  getAuditTimeline: async (workflowId: number) => {
    const res = await apiClient.get(`/api/workflow/application/${workflowId}/audit-timeline`);
    return res.data as { workflow_id: number; application_id: string; total_events: number; timeline: AuditTimelineEvent[] };
  },
};

