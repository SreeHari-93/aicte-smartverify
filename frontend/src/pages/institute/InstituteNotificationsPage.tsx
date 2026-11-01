import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { getAlertTarget, canUserAccessAlert } from '../../utils/alertRouting';
import {
  Bell,
  RefreshCw,
  AlertTriangle,
  ExternalLink,
  Check,
  Search,
  Filter,
} from 'lucide-react';
import { alertsApi, AlertItem } from '../../api/alerts';

export const InstituteNotificationsPage: React.FC = () => {
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>('ALL');
  const [filterSearch, setFilterSearch] = useState<string>('');
  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);

  const loadAlerts = async () => {
    setIsLoading(true);
    try {
      const res = await alertsApi.getAlerts({ limit: 100 });
      setAlerts(res.items || []);
    } catch (err) {
      console.error('Failed to load institute notifications:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAlerts();
  }, []);

  const handleMarkRead = async (id: number) => {
    try {
      await alertsApi.markAlertRead(id);
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, is_read: true } : a)));
    } catch (err) {
      console.error(err);
    }
  };

  const { user } = useAuth();
  const navigate = useNavigate();
  const [accessDeniedAlertId, setAccessDeniedAlertId] = useState<number | null>(null);

  const handleOpenCase = async (alertItem: AlertItem) => {
    if (!canUserAccessAlert(alertItem, user)) {
      setAccessDeniedAlertId(alertItem.id);
      return;
    }
    setAccessDeniedAlertId(null);
    if (!alertItem.is_read) {
      try {
        await handleMarkRead(alertItem.id);
      } catch {
        // quiet fallback
      }
    }
    const target = getAlertTarget(alertItem, user?.role || 'INSTITUTE');
    navigate(target);
  };

  const handleMarkAllRead = async () => {
    try {
      await alertsApi.markAllAlertsRead();
      setAlerts((prev) => prev.map((a) => ({ ...a, is_read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  const filtered = alerts.filter((a) => {
    if (filterType !== 'ALL') {
      if (filterType === 'DOCUMENT_EXPIRING') {
        if (a.event_type !== 'DOCUMENT_EXPIRING' && a.event_type !== 'DOC_EXPIRING_SOON') return false;
      } else if (filterType === 'DOCUMENT_EXPIRED') {
        if (a.event_type !== 'DOCUMENT_EXPIRED' && a.event_type !== 'DOC_EXPIRED') return false;
      } else if (a.event_type !== filterType) {
        return false;
      }
    }
    if (unreadOnly && a.is_read) return false;
    if (filterSearch) {
      const q = filterSearch.toLowerCase();
      const match =
        a.title.toLowerCase().includes(q) ||
        a.message.toLowerCase().includes(q) ||
        a.case_id.toLowerCase().includes(q);
      if (!match) return false;
    }
    return true;
  });

  const unreadCount = alerts.filter((a) => !a.is_read).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900">
            Notifications
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Reminders, stage updates, and notices.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="px-3.5 py-2 bg-white border border-orange-300 hover:bg-orange-50 text-[#E8650A] text-xs font-semibold rounded-lg shadow-2xs flex items-center gap-1.5"
            >
              <Check size={14} />
              <span>Mark all read</span>
            </button>
          )}

          <button
            onClick={loadAlerts}
            disabled={isLoading}
            className="flex items-center gap-2 px-3.5 py-2 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 text-xs font-semibold rounded-lg shadow-2xs"
          >
            <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="bg-white rounded-xl p-4 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search notices..."
              value={filterSearch}
              onChange={(e) => setFilterSearch(e.target.value)}
              className="pl-8 pr-3 py-1.5 rounded-lg border border-slate-300 w-64 focus:border-[#0B3C9D] outline-none placeholder:text-slate-500"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <Filter size={14} className="text-slate-500" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white font-medium"
            >
              <option value="ALL">All events</option>
              <option value="UNDERTAKING_DUE_SOON">Undertakings due soon</option>
              <option value="UNDERTAKING_OVERDUE">Undertakings overdue</option>
              <option value="DOCUMENT_EXPIRING">Documents expiring</option>
              <option value="DOCUMENT_EXPIRED">Documents expired</option>
              <option value="STAGE_DUE_SOON">Stage due soon</option>
              <option value="STAGE_OVERDUE">Stage overdue</option>
              <option value="EVC_SCHEDULED">EVC visit scheduled</option>
            </select>
          </div>

          <label className="flex items-center gap-2 cursor-pointer text-slate-600 font-medium">
            <input
              type="checkbox"
              checked={unreadOnly}
              onChange={(e) => setUnreadOnly(e.target.checked)}
              className="rounded text-[#0B3C9D]"
            />
            <span>Unread notices only</span>
          </label>
        </div>

        <span className="text-slate-500 font-medium">
          Showing {filtered.length} of {alerts.length} notices ({unreadCount} unread)
        </span>
      </div>

      {/* Notice Feed */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm divide-y divide-slate-100">
        {filtered.length === 0 ? (
          <div className="py-12 text-center text-slate-600 text-xs">
            {filterType !== 'ALL' || filterSearch || unreadOnly ? (
              <div className="space-y-2">
                <p>No notifications match these filters</p>
                <button
                  type="button"
                  onClick={() => {
                    setFilterType('ALL');
                    setFilterSearch('');
                    setUnreadOnly(false);
                  }}
                  className="px-3 py-1 bg-white border border-slate-300 hover:border-slate-400 rounded text-slate-700 text-xs font-medium cursor-pointer"
                >
                  Clear filters
                </button>
              </div>
            ) : (
              <p>No notifications yet</p>
            )}
          </div>
        ) : (
          filtered.map((n) => (
            <div
              key={n.id}
              className={`p-4 transition-colors flex items-start justify-between gap-4 ${
                !n.is_read ? 'bg-orange-50/40 hover:bg-orange-50/70' : 'hover:bg-slate-50/60'
              }`}
            >
              <div className="flex items-start gap-3.5">
                <div
                  className={`p-2.5 rounded-lg shrink-0 mt-0.5 ${
                    n.event_type.includes('OVERDUE') || n.event_type.includes('EXPIRED')
                      ? 'bg-red-100 text-red-700'
                      : 'bg-blue-100 text-[#0B3C9D]'
                  }`}
                >
                  {n.event_type.includes('OVERDUE') || n.event_type.includes('EXPIRED') ? (
                    <AlertTriangle size={18} />
                  ) : (
                    <Bell size={18} />
                  )}
                </div>

                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-black text-[#0F2A5C]">{n.title}</span>
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 border border-slate-200 font-mono">
                      {n.case_id}
                    </span>
                    {!n.is_read && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800 border border-amber-200">
                        New
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-slate-700 leading-relaxed whitespace-pre-line max-w-3xl">
                    {n.message}
                  </p>

                  <div className="flex items-center gap-3 text-[11px] text-slate-600 pt-1">
                    <span>
                      Received:{' '}
                      {(() => {
                        if (!n.created_at) return '—';
                        const d = new Date(n.created_at);
                        const day = String(d.getDate()).padStart(2, '0');
                        const month = String(d.getMonth() + 1).padStart(2, '0');
                        const year = d.getFullYear();
                        const hours = String(d.getHours()).padStart(2, '0');
                        const mins = String(d.getMinutes()).padStart(2, '0');
                        return `${day}-${month}-${year} ${hours}:${mins}`;
                      })()}
                    </span>
                    {n.due_date && (
                      <span>
                        Due:{' '}
                        {(() => {
                          const d = new Date(n.due_date);
                          const day = String(d.getDate()).padStart(2, '0');
                          const month = String(d.getMonth() + 1).padStart(2, '0');
                          const year = d.getFullYear();
                          return `${day}-${month}-${year}`;
                        })()}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                {!n.is_read && (
                  <button
                    onClick={() => handleMarkRead(n.id)}
                    className="p-1.5 text-slate-600 hover:text-slate-700 hover:bg-slate-100 rounded-lg text-xs font-medium"
                    title="Mark as read"
                  >
                    <Check size={14} />
                  </button>
                )}
                {(n.case_id || n.link) && (
                  <div className="flex flex-col items-end">
                    <button
                      type="button"
                      onClick={() => handleOpenCase(n)}
                      className="flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-300 hover:border-[#0B3C9D] text-[#0B3C9D] text-xs font-bold rounded-lg shadow-2xs cursor-pointer"
                    >
                      <span>Open case</span>
                      <ExternalLink size={12} />
                    </button>
                    {accessDeniedAlertId === n.id && (
                      <span className="text-[10px] text-red-600 font-medium mt-1">
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
    </div>
  );
};
