import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Scale,
  Files,
  ListChecks,
  Clock,
  AlertTriangle,
  MessageSquare,
  FileBarChart,
  ScrollText,
  Cpu,
} from 'lucide-react';

interface AdminSidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

export const ADMIN_NAV_ITEMS = [
  { label: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
  { label: 'Rules', path: '/admin/rules', icon: Scale },
  { label: 'Document Types', path: '/admin/document-types', icon: Files },
  { label: 'Checklists', path: '/admin/checklists', icon: ListChecks },
  { label: 'Verification Queue', path: '/admin/verification-queue', icon: Clock },
  { label: 'Anomalies', path: '/admin/anomalies', icon: AlertTriangle },
  { label: 'Complaints', path: '/admin/complaints', icon: MessageSquare },
  { label: 'AI Evaluation', path: '/admin/evaluation', icon: Cpu },
  { label: 'Reports', path: '/admin/reports', icon: FileBarChart },
  { label: 'Audit Log', path: '/admin/audit-log', icon: ScrollText },
];

export const AdminSidebar: React.FC<AdminSidebarProps> = ({ isOpen = false, onClose }) => {
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

      {/* Admin Sidebar Container: ~255px wide, cream #FDF0DC, full height */}
      <aside
        className={`fixed lg:static top-24 bottom-0 left-0 z-30 w-[255px] bg-[#FDF0DC] border-r border-[#EFE3CF] flex flex-col justify-between py-6 px-3 shrink-0 select-none transition-transform duration-300 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        }`}
      >
        <nav className="flex flex-col gap-1.5" role="navigation" aria-label="Admin Portal Navigation">
          <div className="px-3 pb-2 mb-1 border-b border-[#EFE3CF]/80">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#0B3C9D]/70">
              Admin Governance
            </span>
          </div>
          {ADMIN_NAV_ITEMS.map((item) => {
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

