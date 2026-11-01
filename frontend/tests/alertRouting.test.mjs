import test from 'node:test';
import assert from 'node:assert/strict';
import {
  deriveCaseType,
  extractCleanCaseId,
  getAlertTarget,
  canUserAccessAlert,
} from '../src/utils/alertRouting.ts';

test('extractCleanCaseId correctly extracts IDs', () => {
  assert.equal(extractCleanCaseId('UT-3 (121)', 'UNDERTAKING'), '3');
  assert.equal(extractCleanCaseId('UT-15', 'UNDERTAKING'), '15');
  assert.equal(extractCleanCaseId('7', 'UNDERTAKING'), '7');

  assert.equal(extractCleanCaseId('DOC-2', 'DOCUMENT_VALIDITY'), '2');
  assert.equal(extractCleanCaseId('DOC-42', 'DOCUMENT_VALIDITY'), '42');
  assert.equal(extractCleanCaseId('88', 'DOCUMENT_VALIDITY'), '88');

  assert.equal(extractCleanCaseId('APP-2026-S01', 'APPLICATION'), 'APP-2026-S01');
  assert.equal(extractCleanCaseId('APP-2026-N02', 'EVC'), 'APP-2026-N02');
});

test('deriveCaseType correctly derives types from event_type and case_id', () => {
  assert.equal(deriveCaseType('STAGE_DUE_SOON', 'APP-2026-S01'), 'APPLICATION');
  assert.equal(deriveCaseType('STAGE_OVERDUE', 'APP-2026-S01'), 'APPLICATION');
  assert.equal(deriveCaseType('APPLICATION_SUBMITTED', 'APP-2026-S01'), 'APPLICATION');

  assert.equal(deriveCaseType('EVC_SCHEDULING_OVERDUE', 'APP-2026-N01'), 'EVC');
  assert.equal(deriveCaseType('VISIT_APPROACHING', 'APP-2026-N01'), 'EVC');
  assert.equal(deriveCaseType('EVC_REPORT_PENDING', 'APP-2026-N01'), 'EVC');

  assert.equal(deriveCaseType('UNDERTAKING_DUE_SOON', 'UT-3 (121)'), 'UNDERTAKING');
  assert.equal(deriveCaseType('UNDERTAKING_OVERDUE', 'UT-5'), 'UNDERTAKING');
  assert.equal(deriveCaseType('UNDERTAKING_ESCALATED', 'UT-1'), 'UNDERTAKING');

  assert.equal(deriveCaseType('DOCUMENT_EXPIRING', 'DOC-2'), 'DOCUMENT_VALIDITY');
  assert.equal(deriveCaseType('DOCUMENT_EXPIRED', 'DOC-3'), 'DOCUMENT_VALIDITY');
  assert.equal(deriveCaseType('RENEWAL_SUBMITTED', 'DOC-4'), 'DOCUMENT_VALIDITY');
  assert.equal(deriveCaseType('LEASE_EXPIRING', 'DOC-5'), 'DOCUMENT_VALIDITY');
});

test('Admin destinations for all event types contain appropriate route and case ID', () => {
  const testCases = [
    { alert: { event_type: 'STAGE_DUE_SOON', case_id: 'APP-2026-S01' }, expected: '/admin/workflow?application=APP-2026-S01' },
    { alert: { event_type: 'STAGE_OVERDUE', case_id: 'APP-2026-S02' }, expected: '/admin/workflow?application=APP-2026-S02' },
    { alert: { event_type: 'STAGE_DEADLINE_APPROACHING', case_id: 'APP-2026-S03' }, expected: '/admin/workflow?application=APP-2026-S03' },
    { alert: { event_type: 'STAGE_ESCALATED', case_id: 'APP-2026-S04' }, expected: '/admin/workflow?application=APP-2026-S04' },
    { alert: { event_type: 'APPLICATION_SUBMITTED', case_id: 'APP-2026-N05' }, expected: '/admin/workflow?application=APP-2026-N05' },

    { alert: { event_type: 'EVC_SCHEDULING_OVERDUE', case_id: 'APP-2026-N01' }, expected: '/admin/evc?open=APP-2026-N01' },
    { alert: { event_type: 'EVC_VISIT_APPROACHING', case_id: 'APP-2026-N02' }, expected: '/admin/evc?open=APP-2026-N02' },
    { alert: { event_type: 'VISIT_APPROACHING', case_id: 'APP-2026-N03' }, expected: '/admin/evc?open=APP-2026-N03' },
    { alert: { event_type: 'EVC_REPORT_PENDING', case_id: 'APP-2026-N04' }, expected: '/admin/evc?open=APP-2026-N04' },

    { alert: { event_type: 'UNDERTAKING_DUE_SOON', case_id: 'UT-3 (121)' }, expected: '/admin/undertakings?open=3' },
    { alert: { event_type: 'UNDERTAKING_OVERDUE', case_id: 'UT-12' }, expected: '/admin/undertakings?open=12' },
    { alert: { event_type: 'UNDERTAKING_ESCALATED', case_id: 'UT-7' }, expected: '/admin/undertakings?open=7' },

    { alert: { event_type: 'DOCUMENT_EXPIRING', case_id: 'DOC-2' }, expected: '/admin/validity?open=2' },
    { alert: { event_type: 'DOCUMENT_EXPIRED', case_id: 'DOC-5' }, expected: '/admin/validity?open=5' },
    { alert: { event_type: 'RENEWAL_SUBMITTED', case_id: 'DOC-9' }, expected: '/admin/validity?open=9' },
    { alert: { event_type: 'LEASE_EXPIRING', case_id: 'DOC-11' }, expected: '/admin/validity?open=11' },
  ];

  for (const tc of testCases) {
    const target = getAlertTarget(tc.alert, 'ADMIN');
    assert.equal(target, tc.expected, `Failed for event ${tc.alert.event_type}`);
    assert.ok(!target.includes('/dashboard'), `Admin target ${target} should never contain /dashboard`);
    assert.ok(!target.endsWith('/workflow') && !target.endsWith('/evc') && !target.endsWith('/undertakings') && !target.endsWith('/validity'),
      `Target ${target} should include the case id parameter`);
  }
});

test('Institute destinations for all event types contain appropriate route and case ID', () => {
  const testCases = [
    { alert: { event_type: 'STAGE_DUE_SOON', case_id: 'APP-2026-S01' }, expected: '/institute/applications?open=APP-2026-S01' },
    { alert: { event_type: 'STAGE_OVERDUE', case_id: 'APP-2026-S02' }, expected: '/institute/applications?open=APP-2026-S02' },
    { alert: { event_type: 'APPLICATION_SUBMITTED', case_id: 'APP-2026-S03' }, expected: '/institute/applications?open=APP-2026-S03' },

    { alert: { event_type: 'EVC_SCHEDULING_OVERDUE', case_id: 'APP-2026-N01' }, expected: '/institute/applications?open=APP-2026-N01' },
    { alert: { event_type: 'VISIT_APPROACHING', case_id: 'APP-2026-N02' }, expected: '/institute/applications?open=APP-2026-N02' },

    { alert: { event_type: 'UNDERTAKING_DUE_SOON', case_id: 'UT-3 (121)' }, expected: '/institute/undertakings?open=3' },
    { alert: { event_type: 'UNDERTAKING_OVERDUE', case_id: 'UT-12' }, expected: '/institute/undertakings?open=12' },

    { alert: { event_type: 'DOCUMENT_EXPIRING', case_id: 'DOC-2' }, expected: '/institute/validity?open=2' },
    { alert: { event_type: 'DOCUMENT_EXPIRED', case_id: 'DOC-5' }, expected: '/institute/validity?open=5' },
    { alert: { event_type: 'RENEWAL_SUBMITTED', case_id: 'DOC-9' }, expected: '/institute/validity?open=9' },
  ];

  for (const tc of testCases) {
    const target = getAlertTarget(tc.alert, 'INSTITUTE');
    assert.equal(target, tc.expected, `Failed for event ${tc.alert.event_type}`);
    assert.ok(!target.includes('/dashboard'), `Institute target ${target} should never contain /dashboard`);
    assert.ok(!target.startsWith('/admin'), `Institute target ${target} must never start with /admin`);
    assert.ok(!target.endsWith('/applications') && !target.endsWith('/undertakings') && !target.endsWith('/validity'),
      `Target ${target} should include the case id parameter`);
  }
});

test('Role guard: canUserAccessAlert works correctly for officers and institutes', () => {
  const adminUser = { role: 'ADMIN' };
  const bureauOfficer = { role: 'BUREAU_OFFICER' };
  const southOfficer = { role: 'REGIONAL_OFFICER', region: 'South' };
  const northOfficer = { role: 'REGIONAL_OFFICER', region: 'North' };
  const institute1 = { role: 'INSTITUTE', institute_id: 101 };
  const institute2 = { role: 'INSTITUTE', institute_id: 102 };

  const southAlert = { event_type: 'STAGE_OVERDUE', case_id: 'APP-2026-S01', region: 'South', institute_id: 101 };
  const northAlert = { event_type: 'EVC_VISIT_APPROACHING', case_id: 'APP-2026-N01', region: 'North', institute_id: 102 };

  assert.equal(canUserAccessAlert(southAlert, adminUser), true);
  assert.equal(canUserAccessAlert(northAlert, adminUser), true);
  assert.equal(canUserAccessAlert(southAlert, bureauOfficer), true);
  assert.equal(canUserAccessAlert(northAlert, bureauOfficer), true);

  assert.equal(canUserAccessAlert(southAlert, southOfficer), true);
  assert.equal(canUserAccessAlert(northAlert, southOfficer), false);
  assert.equal(canUserAccessAlert(northAlert, northOfficer), true);
  assert.equal(canUserAccessAlert(southAlert, northOfficer), false);

  assert.equal(canUserAccessAlert(southAlert, institute1), true);
  assert.equal(canUserAccessAlert(southAlert, institute2), false);
  assert.equal(canUserAccessAlert(northAlert, institute2), true);
  assert.equal(canUserAccessAlert(northAlert, institute1), false);
});

