import React from 'react';

export type TabType = 'INSTITUTE' | 'ADMIN';

interface TabSliderProps {
  activeTab: TabType;
  onChange: (tab: TabType) => void;
}

export const TabSlider: React.FC<TabSliderProps> = ({ activeTab, onChange }) => {
  return (
    <div
      role="tablist"
      aria-label="Login user type"
      className="relative flex items-center bg-[#F1F4F9] p-1 rounded-xl border border-[#E2E8F0] mb-6 select-none"
    >
      {/* 200ms Sliding active pill */}
      <div
        className={`absolute top-1 bottom-1 w-[calc(50%-4px)] bg-[#F58220] rounded-lg shadow-sm transition-transform duration-200 ease-out ${
          activeTab === 'ADMIN' ? 'translate-x-[calc(100%+8px)]' : 'translate-x-0'
        }`}
        aria-hidden="true"
      />

      {/* Institute Tab Button */}
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'INSTITUTE'}
        aria-controls="institute-panel"
        id="tab-institute"
        onClick={() => onChange('INSTITUTE')}
        className={`relative z-10 w-1/2 py-2.5 text-center text-sm font-semibold transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#F58220] rounded-lg ${
          activeTab === 'INSTITUTE' ? 'text-white' : 'text-[#0F2A5C] hover:text-[#0B3C9D]'
        }`}
      >
        Institute
      </button>

      {/* Admin Tab Button */}
      <button
        type="button"
        role="tab"
        aria-selected={activeTab === 'ADMIN'}
        aria-controls="admin-panel"
        id="tab-admin"
        onClick={() => onChange('ADMIN')}
        className={`relative z-10 w-1/2 py-2.5 text-center text-sm font-semibold transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-[#F58220] rounded-lg ${
          activeTab === 'ADMIN' ? 'text-white' : 'text-[#0F2A5C] hover:text-[#0B3C9D]'
        }`}
      >
        Admin
      </button>
    </div>
  );
};

