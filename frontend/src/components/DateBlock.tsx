import React from 'react';

interface DateBlockProps {
  day: number | string;
  month: string;
  year: number | string;
  className?: string;
}

export const DateBlock: React.FC<DateBlockProps> = ({ day, month, year, className = '' }) => {
  return (
    <div
      className={`w-14 h-16 rounded-lg bg-[#E3F0FF] border border-[#CBE4FF] flex flex-col items-center justify-center p-1 shrink-0 select-none shadow-sm ${className}`}
    >
      <span className="text-xl font-extrabold text-[#0F2A5C] leading-none tracking-tight">
        {day}
      </span>
      <span className="text-[10px] font-bold uppercase tracking-wider text-[#0B3C9D] leading-none mt-1">
        {month}
      </span>
      <span className="text-[9px] font-semibold text-[#7A8699] leading-none mt-0.5">
        {year}
      </span>
    </div>
  );
};

