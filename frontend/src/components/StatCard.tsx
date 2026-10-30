import React from 'react';

export type StatTint = 'blue' | 'green' | 'lavender' | 'pink' | 'amber';

interface StatCardProps {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  tint?: StatTint;
  className?: string;
  subtitle?: string;
}

const TINT_STYLES: Record<StatTint, { bg: string; iconBg: string; text: string; iconColor: string }> = {
  blue: {
    bg: 'bg-[#E3F0FF]',
    iconBg: 'bg-[#CBE4FF]',
    text: 'text-[#0B3C9D]',
    iconColor: 'text-[#0B3C9D]',
  },
  green: {
    bg: 'bg-[#E2F6E6]',
    iconBg: 'bg-[#C7F0CE]',
    text: 'text-[#1E7036]',
    iconColor: 'text-[#1E7036]',
  },
  lavender: {
    bg: 'bg-[#ECE8FB]',
    iconBg: 'bg-[#D9D1F7]',
    text: 'text-[#4A3B82]',
    iconColor: 'text-[#4A3B82]',
  },
  pink: {
    bg: 'bg-[#FDE7E9]',
    iconBg: 'bg-[#FBC7CC]',
    text: 'text-[#C62828]',
    iconColor: 'text-[#C62828]',
  },
  amber: {
    bg: 'bg-[#FFF0D6]',
    iconBg: 'bg-[#FFE0B2]',
    text: 'text-[#B85700]',
    iconColor: 'text-[#B85700]',
  },
};

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon,
  tint = 'blue',
  className = '',
  subtitle,
}) => {
  const styles = TINT_STYLES[tint] || TINT_STYLES.blue;

  return (
    <div
      className={`bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex items-center gap-5 transition-transform hover:-translate-y-0.5 duration-200 ${className}`}
    >
      {/* Tinted Inner Panel with Circular Icon */}
      <div className={`w-14 h-14 rounded-full flex items-center justify-center shrink-0 ${styles.iconBg} ${styles.iconColor}`}>
        {icon}
      </div>

      <div className="flex flex-col min-w-0 flex-1">
        <span className="text-xs font-semibold uppercase tracking-wider text-[#0F2A5C]/70 truncate">
          {label}
        </span>
        <span className="text-3xl font-bold text-[#0F2A5C] mt-0.5 tracking-tight font-sans">
          {value}
        </span>
        {subtitle && <span className="text-xs text-slate-500 mt-0.5">{subtitle}</span>}
      </div>
    </div>
  );
};

