import type { AlertItem } from '../api/alerts';

export type CaseType = 'APPLICATION' | 'EVC' | 'UNDERTAKING' | 'DOCUMENT_VALIDITY';

/**
 * Derive case type from event_type and case_id if not explicitly provided.
 */
export function deriveCaseType(eventType?: string, caseId?: string): CaseType {
  const et = (eventType || '').toUpperCase();
  const cid = (caseId || '').toUpperCase();

  if (et.includes('EVC') || et.includes('VISIT')) {
    return 'EVC';
  }
  if (et.includes('UNDERTAKING') || cid.startsWith('UT-')) {
    return 'UNDERTAKING';
  }
  if (
    et.includes('DOCUMENT') ||
    et.includes('VALIDITY') ||
    et.includes('RENEWAL') ||
    et.includes('LEASE') ||
    cid.startsWith('DOC-')
  ) {
    return 'DOCUMENT_VALIDITY';
  }
  if (
    et.includes('STAGE') ||
    et.includes('APPLICATION') ||
    et.includes('WORKFLOW') ||
    cid.startsWith('APP-')
  ) {
    return 'APPLICATION';
  }
  return 'APPLICATION';
}

/**
 * Clean case identifier from raw alert strings (e.g. "UT-3 (121)" -> "3", "DOC-2" -> "2").
 */
export function extractCleanCaseId(caseId?: string, caseType?: CaseType): string {
  if (!caseId) return '';
  const trimmed = caseId.trim();

  if (caseType === 'UNDERTAKING') {
    const utMatch = trimmed.match(/UT-(\d+)/i);
    if (utMatch) return utMatch[1];
    const numMatch = trimmed.match(/^(\d+)/);
    if (numMatch) return numMatch[1];
  }

  if (caseType === 'DOCUMENT_VALIDITY') {
    const docMatch = trimmed.match(/DOC-(\d+)/i);
    if (docMatch) return docMatch[1];
    const numMatch = trimmed.match(/^(\d+)/);
    if (numMatch) return numMatch[1];
  }

  return trimmed;
}

/**
 * Build destination route from alert object and user role.
 * Never falls back to dashboard.
 */
export function getAlertTarget(
  alert: Partial<AlertItem> | { event_type?: string; case_id?: string; case_type?: string; link?: string },
  userRole?: string
): string {
  const role = (userRole || '').toUpperCase();
  const isInstitute = role === 'INSTITUTE';

  const caseType = (alert.case_type as CaseType) || deriveCaseType(alert.event_type, alert.case_id);
  const cleanId = extractCleanCaseId(alert.case_id, caseType);

  if (isInstitute) {
    switch (caseType) {
      case 'UNDERTAKING':
        return cleanId ? `/institute/undertakings?open=${encodeURIComponent(cleanId)}` : '/institute/undertakings';
      case 'DOCUMENT_VALIDITY':
        return cleanId ? `/institute/validity?open=${encodeURIComponent(cleanId)}` : '/institute/validity';
      case 'EVC':
      case 'APPLICATION':
      default:
        return cleanId ? `/institute/applications?open=${encodeURIComponent(cleanId)}` : '/institute/applications';
    }
  }

  // Admin and officer destinations
  switch (caseType) {
    case 'UNDERTAKING':
      return cleanId ? `/admin/undertakings?open=${encodeURIComponent(cleanId)}` : '/admin/undertakings';
    case 'DOCUMENT_VALIDITY':
      return cleanId ? `/admin/validity?open=${encodeURIComponent(cleanId)}` : '/admin/validity';
    case 'EVC':
      return cleanId ? `/admin/evc?open=${encodeURIComponent(cleanId)}` : '/admin/evc';
    case 'APPLICATION':
    default:
      return cleanId ? `/admin/workflow?application=${encodeURIComponent(cleanId)}` : '/admin/workflow';
  }
}

/**
 * Role guard: Check whether an officer or institute has access to this alert's case.
 */
export function canUserAccessAlert(alert: any, user: any): boolean {
  if (!user) return false;
  const role = String(user.role || '').toUpperCase();

  if (role === 'ADMIN' || role === 'BUREAU_OFFICER') {
    return true;
  }

  if (role === 'INSTITUTE') {
    if (alert.institute_id && user.institute_id && alert.institute_id !== user.institute_id) {
      return false;
    }
    return true;
  }

  if (role === 'REGIONAL_OFFICER') {
    const userRegion = String(user.region || '').toLowerCase();
    if (!userRegion || userRegion === 'national' || userRegion === 'all') {
      return true;
    }

    const alertRegion = String(
      alert.region ||
      alert.details?.region ||
      alert.details?.institute_state ||
      alert.institute_state ||
      ''
    ).toLowerCase();

    if (alertRegion) {
      if (!alertRegion.includes(userRegion) && !userRegion.includes(alertRegion)) {
        return false;
      }
    }

    // Check regional application prefix code (APP-2026-S.. South, APP-2026-N.. North, etc.)
    const caseId = String(alert.case_id || '').toUpperCase();
    if (caseId.startsWith('APP-2026-S') && !userRegion.includes('south')) return false;
    if (caseId.startsWith('APP-2026-N') && !userRegion.includes('north')) return false;
    if (caseId.startsWith('APP-2026-W') && !userRegion.includes('west')) return false;
    if (caseId.startsWith('APP-2026-E') && !userRegion.includes('east')) return false;
  }

  return true;
}
