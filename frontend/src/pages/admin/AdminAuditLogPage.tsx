import React, { useState, useEffect } from 'react';
import { Search, RefreshCw, Eye } from 'lucide-react';
import { adminApi, AuditLogOut } from '../../api/admin';
import { Modal } from '../../components/Modal';
import { DataTable, ColumnDef } from '../../components/DataTable';

export const AdminAuditLogPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLog, setSelectedLog] = useState<AuditLogOut | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const loadLogs = async () => {
    setIsLoading(true);
    try {
      const data = await adminApi.listAuditLogs({ limit: 100 });
      setLogs(data);
    } catch {
      // quiet fallback
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadLogs();
  }, []);

  const filteredLogs = logs.filter(
    (l) =>
      l.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (l.reason || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      (l.role || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Audit log
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Audit trail of all administrative and workflow actions.
            </p>
          </div>

          <button
            onClick={loadLogs}
            className="p-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 self-start sm:self-auto"
            title="Refresh logs"
          >
            <RefreshCw size={16} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs font-semibold text-slate-600">Total logged events</span>
            <p className="text-2xl font-bold text-slate-900 mt-1">{logs.length}</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs font-semibold text-slate-600">Security mode</span>
            <p className="text-2xl font-bold text-emerald-700 mt-1">Append-only</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs font-semibold text-slate-600">Scrutiny state</span>
            <p className="text-2xl font-bold text-[#0B3C9D] mt-1">Active</p>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
        <div className="relative w-full max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search action, reason, or role..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D] placeholder:text-slate-500"
          />
        </div>
      </div>

      {/* Table */}
      {(() => {
        const formatRole = (r?: string) => {
          if (!r) return 'Admin';
          return r
            .split('_')
            .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
            .join(' ');
        };
        const formatDate = (iso: string) => {
          const d = new Date(iso);
          const day = String(d.getDate()).padStart(2, '0');
          const month = String(d.getMonth() + 1).padStart(2, '0');
          const year = d.getFullYear();
          const hours = String(d.getHours()).padStart(2, '0');
          const mins = String(d.getMinutes()).padStart(2, '0');
          return `${day}-${month}-${year} ${hours}:${mins}`;
        };

        const columns: ColumnDef<AuditLogOut>[] = [
          {
            key: 'action',
            header: 'Action',
            width: '22%',
            align: 'left',
            sticky: true,
            render: (log) => (
              <span className="font-mono font-medium text-[#0B3C9D] text-xs">
                {log.action}
              </span>
            ),
          },
          {
            key: 'role',
            header: 'Role',
            width: '14%',
            align: 'left',
            render: (log) => (
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                {formatRole(log.role)}
              </span>
            ),
          },
          {
            key: 'reason',
            header: 'Reason',
            width: '28%',
            align: 'left',
            render: (log) => (
              <span className="line-clamp-2 text-xs text-slate-700 block" title={log.reason || ''}>
                {log.reason || '—'}
              </span>
            ),
          },
          {
            key: 'ip_address',
            header: 'IP address',
            width: '12%',
            align: 'left',
            render: (log) => (
              <span className="text-xs font-mono text-slate-600">
                {log.ip_address || '127.0.0.1'}
              </span>
            ),
          },
          {
            key: 'timestamp',
            header: 'Date',
            width: '14%',
            align: 'left',
            render: (log) => (
              <span className="text-xs text-slate-600">
                {formatDate(log.timestamp)}
              </span>
            ),
          },
          {
            key: 'details',
            header: 'Details',
            width: '10%',
            align: 'right',
            render: (log) => (
              <div className="flex justify-end">
                <button
                  onClick={() => {
                    setSelectedLog(log);
                    setIsDetailOpen(true);
                  }}
                  className="px-2.5 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:border-[#0B3C9D] hover:text-[#0B3C9D] rounded inline-flex items-center gap-1 shadow-2xs transition-colors"
                  title="View event details"
                >
                  <Eye size={12} />
                  <span>Inspect</span>
                </button>
              </div>
            ),
          },
        ];

        return (
          <DataTable
            columns={columns}
            data={filteredLogs}
            keyExtractor={(log) => log.id}
            isLoading={isLoading}
            emptyMessage="No audit records found"
            emptySubtitle="Try adjusting your search criteria."
            onClearFilters={searchQuery ? () => setSearchQuery('') : undefined}
            isWide={true}
            isLong={filteredLogs.length > 12}
          />
        );
      })()}

      {/* Details Modal */}
      <Modal
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        title={`Audit event #${selectedLog?.id}: ${selectedLog?.action || ''}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-3">
          {selectedLog && (
            <>
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 text-xs space-y-1.5">
                <p><strong>Action:</strong> <span className="font-mono text-[#0B3C9D]">{selectedLog.action}</span></p>
                <p><strong>Initiated by:</strong> User #{selectedLog.user_id || 'System'} ({selectedLog.role})</p>
                <p><strong>Date:</strong> {(() => {
                  const d = new Date(selectedLog.timestamp);
                  const day = String(d.getDate()).padStart(2, '0');
                  const month = String(d.getMonth() + 1).padStart(2, '0');
                  const year = d.getFullYear();
                  const hours = String(d.getHours()).padStart(2, '0');
                  const mins = String(d.getMinutes()).padStart(2, '0');
                  return `${day}-${month}-${year} ${hours}:${mins}`;
                })()}</p>
                <p><strong>Reason:</strong> {selectedLog.reason || 'None provided'}</p>
              </div>

              <div>
                <span className="text-xs font-semibold text-slate-600 block mb-1">
                  Event metadata and state changes
                </span>
                <pre className="p-3 bg-slate-900 text-emerald-400 rounded-lg text-xs font-mono overflow-x-auto max-h-72">
                  {JSON.stringify(selectedLog.details || {}, null, 2)}
                </pre>
              </div>
            </>
          )}
        </div>
      </Modal>
    </div>
  );
};
