import React, { useState, useRef, useEffect } from 'react';
import { Bell, ChevronDown, User, LogOut, KeyRound, Building2, Menu, X, Check } from 'lucide-react';
import { AicteLogo } from './AicteLogo';
import { useAuth } from '../context/AuthContext';
import { NotificationItem, instituteApi } from '../api/institute';

interface TopBarProps {
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export const TopBar: React.FC<TopBarProps> = ({ onToggleSidebar, isSidebarOpen }) => {
  const { user, logout } = useAuth();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);

  const userMenuRef = useRef<HTMLDivElement>(null);
  const notifMenuRef = useRef<HTMLDivElement>(null);

  // Fetch notifications
  useEffect(() => {
    let mounted = true;
    const fetchNotifs = async () => {
      try {
        const data = await instituteApi.getNotifications();
        if (mounted) {
          setNotifications(data.items || []);
          setUnreadCount(data.unread_count || 0);
        }
      } catch {
        // quiet fallback
      }
    };
    fetchNotifs();
    const interval = setInterval(fetchNotifs, 60000); // 1 min poll
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

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
      await instituteApi.markAllNotificationsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error(err);
    }
  };

  const isAdmin = user?.role === 'ADMIN' || user?.role === 'REVIEWER';
  const instituteDisplayName = isAdmin
    ? (user?.email || 'CENTRAL ADMINISTRATOR')
    : (user?.institute?.name || user?.email?.split('@')[0] || 'SRI KRISHNA COLLEGE OF ENGINEERING AND TECHNOLOGY');

  return (
    <header className="h-24 bg-[#E8650A] text-white flex items-center justify-between px-4 sm:px-6 z-40 sticky top-0 shadow-md select-none">
      {/* Left Area: Logo & Two-line Title */}
      <div className="flex items-center gap-2 sm:gap-4 min-w-0">
        {/* Mobile Hamburger toggle */}
        <button
          onClick={onToggleSidebar}
          aria-label={isSidebarOpen ? 'Close navigation sidebar' : 'Open navigation sidebar'}
          className="lg:hidden p-2 text-white hover:bg-white/10 rounded-lg transition-colors mr-1"
        >
          {isSidebarOpen ? <X size={24} /> : <Menu size={24} />}
        </button>

        {/* Official AICTE Logo */}
        <AicteLogo size="topbar" />

        {/* Two-line title in White */}
        <div className="flex flex-col justify-center min-w-0 leading-tight">
          <h1 className="text-[13px] sm:text-base md:text-lg font-bold uppercase tracking-wider text-white truncate font-sans">
            ALL INDIA COUNCIL FOR TECHNICAL EDUCATION
          </h1>
          <h2 className="text-[11px] sm:text-xs md:text-sm font-medium text-white/95 truncate font-sans mt-0.5">
            अखिल भारतीय तकनीकी शिक्षा परिषद
          </h2>
        </div>
      </div>

      {/* Right Area: Bell, Divider, Avatar, Name, Chevron dropdown */}
      <div className="flex items-center gap-3 sm:gap-4 shrink-0">
        {/* Notifications Bell */}
        <div className="relative" ref={notifMenuRef}>
          <button
            onClick={() => setIsNotifOpen(!isNotifOpen)}
            aria-label="Notifications"
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
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-xl shadow-2xl border border-slate-100 text-slate-800 overflow-hidden z-50 animate-fade-in">
              <div className="p-3.5 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-wider text-[#0B3C9D]">
                  Notifications ({unreadCount} unread)
                </span>
                {unreadCount > 0 && (
                  <button
                    onClick={handleMarkAllRead}
                    className="text-[11px] font-semibold text-[#F58220] hover:underline flex items-center gap-1"
                  >
                    <Check size={12} />
                    <span>Mark all read</span>
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-y-auto divide-y divide-slate-100 text-xs">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-slate-400">No notifications at this time.</div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      className={`p-3.5 hover:bg-slate-50 transition-colors ${
                        !n.is_read ? 'bg-orange-50/50 font-medium' : 'text-slate-600'
                      }`}
                    >
                      <p className="text-xs font-bold text-[#0F2A5C]">{n.title}</p>
                      <p className="mt-1 text-[11px] leading-relaxed text-slate-600">{n.message}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* Thin White Vertical Divider */}
        <div className="h-8 w-px bg-white/40 hidden sm:block" />

        {/* User Info & Dropdown Trigger */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
            className="flex items-center gap-2 sm:gap-3 p-1.5 rounded-lg hover:bg-white/10 transition-colors focus:outline-none focus:ring-2 focus:ring-white/50 text-left"
            aria-expanded={isUserMenuOpen}
            aria-haspopup="true"
          >
            {/* White Circular User Avatar */}
            <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-[#E8650A] shadow-inner shrink-0">
              <User size={20} />
            </div>

            {/* Logged in Institute Name in White (two lines, wraps) */}
            <div className="hidden md:flex flex-col max-w-[190px] leading-tight">
              <span className="text-xs font-bold text-white line-clamp-2 uppercase">
                {instituteDisplayName}
              </span>
              <span className="text-[10px] text-white/80 uppercase tracking-wider mt-0.5">
                {isAdmin ? `SECURITY ROLE: ${user?.role || 'ADMIN'}` : `AICTE ID: ${user?.institute?.aicte_institute_id || 'SKCET01'}`}
              </span>
            </div>

            <ChevronDown size={16} className="text-white/80 shrink-0 ml-0.5" />
          </button>

          {/* User Menu Dropdown: Profile, Change Password, Logout */}
          {isUserMenuOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-2xl border border-slate-100 text-slate-800 py-1.5 z-50 animate-fade-in">
              <div className="px-4 py-2.5 border-b border-slate-100">
                <p className="text-xs font-bold text-[#0F2A5C] truncate">{instituteDisplayName}</p>
                <p className="text-[11px] text-slate-500 truncate">{user?.email}</p>
              </div>

              <button
                onClick={() => {
                  setIsUserMenuOpen(false);
                  window.location.href = '/institute/dashboard';
                }}
                className="w-full px-4 py-2 text-xs font-medium text-[#0F2A5C] hover:bg-[#FDF0DC] flex items-center gap-2.5 transition-colors"
              >
                <Building2 size={16} className="text-[#0B3C9D]" />
                <span>Institute Profile</span>
              </button>

              <button
                onClick={() => {
                  setIsUserMenuOpen(false);
                  alert('Change Password is available in your security settings.');
                }}
                className="w-full px-4 py-2 text-xs font-medium text-[#0F2A5C] hover:bg-[#FDF0DC] flex items-center gap-2.5 transition-colors"
              >
                <KeyRound size={16} className="text-[#0B3C9D]" />
                <span>Change Password</span>
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

