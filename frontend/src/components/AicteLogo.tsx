import React from 'react';

interface AicteLogoProps {
  className?: string;
  size?: 'topbar' | 'small' | 'large';
}

export const AicteLogo: React.FC<AicteLogoProps> = ({ className = '', size = 'topbar' }) => {
  // Desktop: ~84px height (fills 96px topbar with generous presence), Mobile: ~60px
  const sizeClasses =
    size === 'topbar'
      ? 'h-16 md:h-[84px] w-auto max-w-[120px]'
      : size === 'small'
      ? 'h-10 w-auto max-w-[60px]'
      : 'h-24 w-auto max-w-[150px]';

  return (
    <div className={`flex items-center justify-center p-0 shrink-0 ${className}`} aria-label="AICTE Logo">
      <img
        src="/AICTE Golden Gear Emblem.png"
        alt="All India Council for Technical Education Golden Gear Emblem"
        className={`${sizeClasses} object-contain select-none`}
        loading="eager"
      />
    </div>
  );
};

