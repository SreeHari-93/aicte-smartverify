import React from 'react';

export const TricolourStrip: React.FC = () => {
  return (
    <div className="w-full h-1 flex shadow-sm z-50 fixed top-0 left-0" role="presentation">
      <div className="flex-1 bg-[#FF9933]" />
      <div className="flex-1 bg-[#FFFFFF]" />
      <div className="flex-1 bg-[#138808]" />
    </div>
  );
};

