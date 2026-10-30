import React from 'react';
import { Star } from 'lucide-react';

interface StarRingProps {
  rank: number | string;
  grade?: string;
}

export const StarRing: React.FC<StarRingProps> = ({ rank, grade }) => {
  // 8 stars arranged symmetrically in a circle (every 45 degrees)
  const starCount = 8;
  const radius = 48; // radius in pixels

  return (
    <div className="flex flex-col items-center justify-center p-2 text-center select-none">
      <span className="text-xs font-bold tracking-widest text-[#0B3C9D] uppercase">
        NIRF
      </span>
      <span className="text-[11px] font-semibold text-[#7A8699] uppercase tracking-wider mb-2">
        RANK
      </span>

      {/* Ring container */}
      <div className="relative w-32 h-32 flex items-center justify-center my-1">
        {/* Ring of 8 stars */}
        {Array.from({ length: starCount }).map((_, index) => {
          const angle = (index * 360) / starCount - 90; // Start at top
          const rad = (angle * Math.PI) / 180;
          const x = Math.round(radius * Math.cos(rad));
          const y = Math.round(radius * Math.sin(rad));

          return (
            <div
              key={index}
              className="absolute text-[#F58220] transition-transform hover:scale-125"
              style={{
                transform: `translate(${x}px, ${y}px)`,
              }}
            >
              <Star size={12} fill="#F58220" />
            </div>
          );
        })}

        {/* Center Rank number in large bold navy */}
        <div className="w-20 h-20 rounded-full bg-[#E3F0FF] flex items-center justify-center border-2 border-white shadow-inner">
          <span className="text-3xl font-extrabold text-[#0F2A5C] tracking-tight">
            {rank}
          </span>
        </div>
      </div>

      {/* Accreditation Grade below in bold */}
      {grade && (
        <div className="mt-3 px-3 py-1 bg-emerald-50 border border-emerald-200 rounded-md">
          <span className="text-xs font-bold text-[#1E7036] tracking-wide">
            NAAC {grade}
          </span>
        </div>
      )}
    </div>
  );
};

