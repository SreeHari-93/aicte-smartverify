import React, { useState, useRef, useEffect } from 'react';
import { Bell, ChevronDown, User, LogOut, KeyRound, Building2, Menu, X, Check, ExternalLink } from 'lucide-react';
import { AicteLogo } from './AicteLogo';
import { useAuth } from '../context/AuthContext';
import { alertsApi, AlertItem } from '../api/alerts';
import { useNavigate } from 'react-router-dom';
import { getAlertTarget, canUserAccessAlert } from '../utils/alertRouting';

interface TopBarProps {
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

function formatRole(role?: string): string {
  if (!role) return 'Admin';
  switch (role) {
    case 'ADMIN': return 'Admin';
    case 'REGIONAL_OFFICER': return 'Regional officer';
    case 'BUREAU_OFFICER': return 'Bureau officer';
    case 'COMMITTEE_MEMBER': return 'Committee member';
    case 'REVIEWER': return 'Reviewer';
    case 'INSTITUTE': return 'Institute';
    default: return role.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
  }
}

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return 'Just now';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return 'Just now';
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}-${month}-${year}`;
}

export const TopBar: React.FC<TopBarProps> = ({ onToggleSidebar, isSidebarOpen }) => {
  const { user, logout } = useAuth();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [accessDeniedId, setAccessDeniedId] = useState<number | null>(null);
  const navigate = useNavigate();

  const handleOpenCase = async (alertItem: AlertItem) => {
    if (!canUserAccessAlert(alertItem, user)) {
      setAccessDeniedId(alertItem.id);
      return;
    }
    setAccessDeniedId(null);
    if (!alertItem.is_read) {
      try {
        await alertsApi.markAlertRead(alertItem.id);
        setAlerts((prev) => prev.map((a) => (a.id === alertItem.id ? { ...a, is_read: true } : a)));
        setUnreadCount((prev) => Math.max(0, prev - 1));
      } catch {
        // quiet fallback
      }
    }
    setIsNotifOpen(false);
    const target = getAlertTarget(alertItem, user?.role);
    navigate(target);
  };

  const userMenuRef = useRef<HTMLDivElement>(null);
  const notifMenuRef = useRef<HTMLDivElement>(null);

  const fetchAlerts = async () => {
    try {
      const [alertsRes, countRes] = await Promise.all([
        alertsApi.getAlerts({ limit: 6 }),
        alertsApi.getUnreadCount(),
      ]);
      setAlerts(alertsRes.items || []);
      setUnreadCount(countRes.unread_count || 0);
    } catch {
      // quiet fallback
    }
  };

  useEffect(() => {
    let mounted = true;
    if (mounted) fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000); // 30 sec poll
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, [user]);

  // Close menus on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setIsUserMenuOpen(false);
      }
      if (notifMenuRef.current && !notifMenuRef.current.contains(e.target as Node)) {
        setIsNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, []);

  const handleMarkAllRead = async () => {
    try {
      await alertsApi.markAllAlertsRead();
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error(err);
    }
  };

  const isAdmin = user?.role !== 'INSTITUTE';
  const instituteDisplayName = isAdmin
    ? (user?.email || 'AICTE Officer Desk')
    : (user?.institute?.name || user?.email?.split('@')[0] || 'Sri Krishna College of Engineering and Technology');

  return (
    <header className="h-24 bg-[#E8650A] text-white flex items-center justify-between px-4 sm:px-6 z-40 sticky top-0 shadow-md select-none">
      {/* Left: Logo and name */}
      <div className="flex items-center gap-2 sm:gap-4 min-w-0">
        <button
          onClick={onToggleSidebar}
          aria-label={isSidebarOpen ? 'Close navigation sidebar' : 'Open navigation sidebar'}
          className="lg:hidden p-2 text-white hover:bg-white/10 rounded-lg transition-colors mr-1"
        >
          {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        <AicteLogo size="topbar" />

        <div className="flex flex-col justify-center min-w-0 leading-tight">
          <h1 className="text-[13px] sm:text-base md:text-lg font-bold uppercase tracking-wider text-white truncate font-sans">
            ALL INDIA COUNCIL FOR TECHNICAL EDUCATION
          </h1>
          <h2 className="text-[11px] sm:text-xs md:text-sm font-medium text-white/95 truncate font-sans mt-0.5">
            अखिल भारतीय तकनीकी शिक्षा परिषद
          </h2>
        </div>
      </div>

      {/* Right: Bell and user menu */}
      <div className="flex items-center gap-3 sm:gap-4 shrink-0">
        {/* Notifications Bell */}
        <div className="relative" ref={notifMenuRef}>
          <button
            onClick={() => setIsNotifOpen(!isNotifOpen)}
            aria-label="Alerts"
            className="relative p-2.5 rounded-full hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-white/50"
          >
            <Bell size={22} className="text-white" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 bg-red-600 border-2 border-[#E8650A] rounded-full text-[9px] font-bold flex items-center justify-center text-white">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown */}
          {isNotifOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-lg shadow-lg border border-slate-200 text-slate-800 overflow-hidden z-50">
              <div className="p-3.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-700">
                  Alerts ({unreadCount} unread)
                </span>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-[11px] font-medium text-[#F58220] hover:underline flex items-center gap-1"
                  >
                    <Check size={12} />
                    <span>Mark all read</span>
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 text-xs">
                {alerts.length === 0 ? (
                  <div className="p-6 text-center text-slate-600">No active alerts at this time.</div>
                ) : (
                  alerts.map((a) => (
                    <div
                      key={a.id}
                      className={`p-3.5 hover:bg-slate-50 transition-colors ${
                        !a.is_read ? 'bg-orange-50/50 font-medium' : 'text-slate-600'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-xs font-semibold text-slate-900">{a.title}</p>
                        <span className="text-[10px] text-slate-600 shrink-0 font-mono">
                          {a.case_id}
                        </span>
                      </div>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-600 line-clamp-2">
                        {a.message}
                      </p>
                      <div className="mt-2 flex items-center justify-between pt-1 border-t border-slate-100">
                        <span className="text-[10px] text-slate-600">
                          {formatDate(a.created_at)}
                        </span>
                        {(a.case_id || a.link) && (
                          <div className="flex flex-col items-end">
                            <button
                              type="button"
                              onClick={() => handleOpenCase(a)}
                              className="text-[11px] font-medium text-[#0B3C9D] hover:underline flex items-center gap-1 cursor-pointer"
                            >
                              <span>Open case</span>
                              <ExternalLink size={10} />
                            </button>
                            {accessDeniedId === a.id && (
                              <span className="text-[10px] text-red-600 font-medium mt-0.5">
                                You don't have access to this case.
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
              <div className="p-2.5 bg-slate-50 border-t border-slate-200 text-center">
                <button
                  type="button"
                  onClick={() => {
                    setIsNotifOpen(false);
                    navigate(isAdmin ? '/admin/alerts' : '/institute/notifications');
                  }}
                  className="text-xs font-semibold text-[#0B3C9D] hover:underline cursor-pointer"
                >
                  View all alerts
                </button>
              </div>
            </div>
          )}
        </div>

        {/* User Info & Dropdown Trigger */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center gap-2 sm:gap-3 p-1.5 rounded-lg hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-white/50 text-left"
            aria-expanded={isUserMenuOpen}
            aria-haspopup="true"
          >
            <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-[#E8650A] shadow-inner shrink-0">
              <User size={20} />
            </div>

            <div className="hidden md:flex flex-col max-w-[190px] leading-tight">
              <span className="text-xs font-semibold text-white line-clamp-2">
                {instituteDisplayName}
              </span>
              <span className="text-[11px] text-white/80 mt-0.5">
                {isAdmin ? `${formatRole(user?.role)}${user?.region ? ` (${user.region})` : ''}` : `AICTE ID: ${user?.institute?.aicte_institute_id || '1-SKCET2026'}`}
              </span>
            </div>

            <ChevronDown size={16} className="text-white/80 shrink-0 ml-0.5" />
          </button>

          {/* User Menu Dropdown */}
          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-slate-200 text-slate-800 py-1.5 z-50">
              <div className="px-4 py-2.5 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-900 truncate">{instituteDisplayName}</p>
                <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
              </div>

              <button
                onClick={() => {
                  setIsUserMenuOpen(false);
                  navigate(isAdmin ? '/admin/dashboard' : '/institute/dashboard');
                }}
                className="w-full px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2.5 transition-colors"
              >
                <Building2 size={16} className="text-slate-500" />
                <span>Dashboard</span>
              </button>

              <button
                onClick={() => {
                  setIsUserMenuOpen(false);
                  alert('Security credentials are managed through AICTE central authentication.');
                }}
                className="w-full px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2.5 transition-colors"
              >
                <KeyRound size={16} className="text-slate-500" />
                <span>Security settings</span>
              </button>

              <div className="border-t border-slate-100 my-1" />

              <button
                onClick={logout}
                className="w-full px-4 py-2 text-xs font-semibold text-[#C62828] hover:bg-red-50 flex items-center gap-2.5 transition-colors"
              >
                <LogOut size={16} />
                <span>Logout</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
