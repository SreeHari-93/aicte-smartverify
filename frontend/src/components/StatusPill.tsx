import React from 'react';

interface StatusPillProps {
  status: string;
  className?: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status, className = '' }) => {
  const norm = (status || '').toLowerCase().trim();

  let bgClass = 'bg-slate-100 text-slate-700';

  if (
    norm === 'valid' ||
    norm === 'approved' ||
    norm === 'pass' ||
    norm === 'resolved' ||
    norm === 'verified'
  ) {
    // Valid: green text on #E2F6E6
    bgClass = 'bg-[#E2F6E6] text-[#1E7036]';
  } else if (
    norm === 'expiring soon' ||
    norm === 'warning' ||
    norm === 'submitted' ||
    norm === 'in progress' ||
    norm === 'needs attention' ||
    norm === 'under review'
  ) {
    // Expiring Soon: orange text on #FFF0D6
    bgClass = 'bg-[#FFF0D6] text-[#B85700]';
  } else if (
    norm === 'expired' ||
    norm === 'rejected' ||
    norm === 'fail'
  ) {
    // Expired: red text on #FDE7E9
    bgClass = 'bg-[#FDE7E9] text-[#C62828]';
  } else if (norm === 'draft' || norm === 'uploaded' || norm === 'open') {
    // Draft/Uploaded: subtle lavender on #ECE8FB
    bgClass = 'bg-[#ECE8FB] text-[#4A3B82]';
  }

  return (
    <span
      className={`inline-flex items-center justify-center px-3 py-1 rounded-full text-xs font-semibold tracking-wide whitespace-nowrap select-none ${bgClass} ${className}`}
    >
      {status}
    </span>
  );
};

