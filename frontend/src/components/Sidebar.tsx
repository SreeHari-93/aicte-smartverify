import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Home,
  FileText,
  FileSignature,
  Hourglass,
  FileUp,
  MessageSquare,
  Bell,
  BarChart3,
} from 'lucide-react';

interface SidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

// Exact Institute Sidebar Order for PS 26262:
// Dashboard, My Applications, Undertakings, Document Validity, Documents, Complaints, Notifications, Reports.
export const NAV_ITEMS = [
  { label: 'Dashboard', path: '/institute/dashboard', icon: Home },
  { label: 'Applications', path: '/institute/applications', icon: FileText },
  { label: 'Undertakings', path: '/institute/undertakings', icon: FileSignature },
  { label: 'Document validity', path: '/institute/validity', icon: Hourglass },
  { label: 'Documents', path: '/institute/upload', icon: FileUp },
  { label: 'Complaints', path: '/institute/complaints', icon: MessageSquare },
  { label: 'Notifications', path: '/institute/notifications', icon: Bell },
  { label: 'Reports', path: '/institute/reports', icon: BarChart3 },
];

export const Sidebar: React.FC<SidebarProps> = ({ isOpen = false, onClose }) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-30 lg:hidden backdrop-blur-xs transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      {/* Sidebar Container: ~255px wide, cream #FDF0DC, full height */}
      <aside
        className={`fixed lg:static top-24 bottom-0 left-0 z-30 w-[255px] bg-[#FDF0DC] border-r border-[#EFE3CF] flex flex-col justify-between py-6 px-3 shrink-0 select-none transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <nav className="flex flex-col gap-1.5 overflow-y-auto pr-1" role="navigation" aria-label="Institute Portal Navigation">
          <div className="px-3 pb-2 mb-1 border-b border-[#EFE3CF]/80">
            <span className="text-xs font-semibold text-slate-600">
              Menu
            </span>
          </div>
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3.5 px-4 py-2.5 rounded-[8px] transition-all duration-150 group ${
                    isActive
                      ? 'bg-[#FCE0BE] text-[#0B3C9D] font-semibold shadow-xs'
                      : 'text-[#0B3C9D] hover:bg-[#FCE0BE]/60 font-medium'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      size={19}
                      className={`shrink-0 transition-colors ${
                        isActive ? 'text-[#0F2A5C]' : 'text-[#0F2A5C]/80 group-hover:text-[#0F2A5C]'
                      }`}
                    />
                    <span className="text-[15px] tracking-tight leading-none text-[#0B3C9D]">
                      {item.label}
                    </span>
                  </>
                )}
              </NavLink>
            );
          })}
        </nav>
      </aside>
    </>
  );
};
