import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  GitBranch,
  FileText,
  Users,
  FileSignature,
  ShieldCheck,
  Bell,
  MessageSquare,
  Scale,
  FileBarChart,
  Cpu,
  CheckSquare,
  ScrollText,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface AdminSidebarProps {
  isOpen?: boolean;
  onClose?: () => void;
}

// Exact admin sidebar order for PS 26262:
// Dashboard, Workflow, Applications, EVC, Undertakings, Document Validity, Alerts, Complaints, Rules & Timelines, Reports, Evaluation, Audit Log
export const ADMIN_NAV_ITEMS = [
  { label: 'Dashboard', path: '/admin/dashboard', icon: LayoutDashboard },
  { label: 'Workflow', path: '/admin/workflow', icon: GitBranch },
  { label: 'Applications', path: '/admin/applications', icon: FileText },
  { label: 'EVC visits', path: '/admin/evc', icon: Users },
  { label: 'Undertakings', path: '/admin/undertakings', icon: FileSignature },
  { label: 'Document validity', path: '/admin/validity', icon: ShieldCheck },
  { label: 'Alerts', path: '/admin/alerts', icon: Bell },
  { label: 'Complaints', path: '/admin/complaints', icon: MessageSquare },
  { label: 'Rules and timelines', path: '/admin/rules', icon: Scale },
  { label: 'Reports', path: '/admin/reports', icon: FileBarChart },
  { label: 'Evaluation', path: '/admin/evaluation', icon: Cpu },
  { label: 'Coverage', path: '/admin/coverage', icon: CheckSquare },
  { label: 'Audit log', path: '/admin/audit-log', icon: ScrollText },
];

export const AdminSidebar: React.FC<AdminSidebarProps> = ({ isOpen = false, onClose }) => {
  const { user } = useAuth();

  // Role-based filtering: Committee member sees only Dashboard, EVC, Applications (assigned only), and Alerts
  const navItems = React.useMemo(() => {
    if (user?.role === 'COMMITTEE_MEMBER') {
      return ADMIN_NAV_ITEMS.filter((item) =>
        ['/admin/dashboard', '/admin/evc', '/admin/applications', '/admin/alerts'].includes(item.path)
      );
    }
    return ADMIN_NAV_ITEMS;
  }, [user?.role]);

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
        <nav className="flex flex-col gap-1 overflow-y-auto pr-1" role="navigation" aria-label="Admin Portal Navigation">
          <div className="px-3 pb-2 mb-1 border-b border-[#EFE3CF]/80">
            <span className="text-xs font-semibold text-slate-600">
              Menu
            </span>
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3.5 py-2 rounded-[8px] transition-all duration-150 group ${
                    isActive
                      ? 'bg-[#FCE0BE] text-[#0B3C9D] font-semibold shadow-xs'
                      : 'text-[#0B3C9D] hover:bg-[#FCE0BE]/60 font-medium'
                  }`
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon
                      size={18}
                      className={`shrink-0 transition-colors ${
                        isActive ? 'text-[#0F2A5C]' : 'text-[#0F2A5C]/80 group-hover:text-[#0F2A5C]'
                      }`}
                    />
                    <span className="text-[14px] tracking-tight leading-none text-[#0B3C9D]">
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
