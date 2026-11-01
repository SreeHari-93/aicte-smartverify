import React from 'react';

interface StatusPillProps {
  status: string;
  className?: string;
}

export function formatStatusLabel(status: string): string {
  if (!status) return '';
  const norm = status.trim().toUpperCase();
  switch (norm) {
    case 'IN_PROGRESS':
    case 'IN PROGRESS':
      return 'In progress';
    case 'OVERDUE':
      return 'Overdue';
    case 'DUE_SOON':
    case 'DUE SOON':
      return 'Due soon';
    case 'ON_TRACK':
    case 'ON TRACK':
      return 'On track';
    case 'COMPLETED':
      return 'Completed';
    case 'RETURNED':
      return 'Returned';
    case 'ON_HOLD':
    case 'ON HOLD':
      return 'On hold';
    case 'ACTIVE':
      return 'Active';
    case 'SUBMITTED':
      return 'Submitted';
    case 'UNDER_VERIFICATION':
    case 'UNDER VERIFICATION':
      return 'Under verification';
    case 'ESCALATED':
      return 'Escalated';
    case 'EXPIRING_SOON':
    case 'EXPIRING SOON':
      return 'Expiring soon';
    case 'EXPIRED':
      return 'Expired';
    case 'RENEWAL_SUBMITTED':
    case 'RENEWAL SUBMITTED':
      return 'Renewal submitted';
    case 'RESOLVED':
      return 'Resolved';
    case 'OPEN':
      return 'Open';
    case 'CLOSED':
      return 'Closed';
    case 'VERIFIED':
      return 'Verified';
    case 'REJECTED':
      return 'Rejected';
    case 'APPROVED':
      return 'Approved';
    case 'PENDING':
      return 'Pending';
    case 'PENDING_SCHEDULING':
    case 'PENDING SCHEDULING':
      return 'Pending scheduling';
    case 'SCHEDULED':
      return 'Scheduled';
    case 'PASS':
      return 'Pass';
    case 'FAIL':
      return 'Fail';
    case 'WARNING':
      return 'Warning';
    case 'BLOCKER':
      return 'Blocker';
    case 'MANUAL_REVIEW_REQUIRED':
    case 'MANUAL REVIEW REQUIRED':
      return 'Manual review required';
    default:
      // Default convert SNAKE_CASE or UPPER to Sentence case
      return status
        .replace(/_/g, ' ')
        .toLowerCase()
        .replace(/^\w/, (c) => c.toUpperCase());
  }
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, className = '' }) => {
  const norm = (status || '').toLowerCase().trim();

  let bgClass = 'bg-slate-100 text-slate-700';

  if (
    norm === 'valid' ||
    norm === 'approved' ||
    norm === 'pass' ||
    norm === 'resolved' ||
    norm === 'verified' ||
    norm === 'done' ||
    norm === 'ready' ||
    norm === 'published' ||
    norm === 'active' ||
    norm === 'on_track' ||
    norm === 'on track' ||
    norm === 'completed'
  ) {
    // Valid / Done / Ready / Published / Active / Completed / On track: green text on #E2F6E6
    bgClass = 'bg-[#E2F6E6] text-[#1E7036]';
  } else if (
    norm === 'expiring soon' ||
    norm === 'expiring_soon' ||
    norm === 'warning' ||
    norm === 'major' ||
    norm === 'submitted' ||
    norm === 'in progress' ||
    norm === 'in_progress' ||
    norm === 'due soon' ||
    norm === 'due_soon' ||
    norm === 'needs attention' ||
    norm === 'needs_review' ||
    norm === 'incomplete' ||
    norm === 'incomplete_fields' ||
    norm === 'under review' ||
    norm === 'under_verification' ||
    norm === 'source unavailable' ||
    norm === 'source_unavailable' ||
    norm === 'manual review required' ||
    norm === 'manual_review_required' ||
    norm === 'pending_scheduling' ||
    norm === 'pending scheduling'
  ) {
    // Expiring Soon / Needs Attention / Due soon / In progress / Warning: orange text on #FFF0D6
    bgClass = 'bg-[#FFF0D6] text-[#B85700]';
  } else if (
    norm === 'expired' ||
    norm === 'overdue' ||
    norm === 'escalated' ||
    norm === 'rejected' ||
    norm === 'fail' ||
    norm === 'missing' ||
    norm === 'failed' ||
    norm.startsWith('failed') ||
    norm === 'mismatch detected' ||
    norm === 'mismatch_detected' ||
    norm === 'blocker'
  ) {
    // Expired / Overdue / Escalated / Failed: red text on #FDE7E9
    bgClass = 'bg-[#FDE7E9] text-[#C62828]';
  } else if (norm === 'draft' || norm === 'uploaded' || norm === 'open') {
    bgClass = 'bg-[#ECE8FB] text-[#4A3B82]';
  } else if (
    norm === 'processing' ||
    norm === 'pending' ||
    norm === 'scheduled' ||
    norm === 'on_hold' ||
    norm === 'on hold' ||
    norm === 'returned' ||
    norm === 'verification pending' ||
    norm === 'verification_pending' ||
    norm === 'info' ||
    norm === 'minor' ||
    norm === 'advisory'
  ) {
    bgClass = 'bg-[#E3F0FF] text-[#0B3C9D]';
  } else if (norm === 'archived' || norm === 'inactive') {
    bgClass = 'bg-slate-200 text-slate-700';
  }

  const label = formatStatusLabel(status);

  return (
    <span
      className={`inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-medium tracking-normal whitespace-nowrap select-none ${bgClass} ${className}`}
    >
      {label}
    </span>
  );
};

