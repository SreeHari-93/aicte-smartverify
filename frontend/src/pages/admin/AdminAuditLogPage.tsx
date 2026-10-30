import React, { useState, useEffect } from 'react';
import { ScrollText, Search, RefreshCw, Eye } from 'lucide-react';
import { adminApi, AuditLogOut } from '../../api/admin';
import { Modal } from '../../components/Modal';

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
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center gap-2 bg-[#E3F0FF] text-[#0B3C9D] text-xs font-semibold px-2.5 py-1 rounded-md mb-2">
              <ScrollText size={14} />
              <span>Immutable Regulatory Scrutiny Trail</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F2A5C] tracking-tight">
              Administrative Audit Log
            </h1>
            <p className="text-sm text-slate-500 mt-1 max-w-2xl">
              Append-only audit trail capturing all administrative mutations, rule modifications, RuleSet releases, and statutory overrides.
            </p>
          </div>

          <button
            onClick={loadLogs}
            className="p-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 self-start sm:self-auto"
          >
            <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs uppercase font-bold text-slate-500">Total Logged Events</span>
            <p className="text-2xl font-bold text-[#0F2A5C] mt-1">{logs.length}</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs uppercase font-bold text-slate-500">Security Mode</span>
            <p className="text-2xl font-bold text-emerald-700 mt-1">Append-Only</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs uppercase font-bold text-slate-500">Scrutiny State</span>
            <p className="text-2xl font-bold text-[#0B3C9D] mt-1">Active Monitoring</p>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
        <div className="relative w-full max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search action, reason, or role..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase text-xs tracking-wider">
              <tr>
                <th className="py-3.5 px-4">Action</th>
                <th className="py-3.5 px-4">Role</th>
                <th className="py-3.5 px-4">Reason / Notes</th>
                <th className="py-3.5 px-4">IP / User Agent</th>
                <th className="py-3.5 px-4">Timestamp</th>
                <th className="py-3.5 px-4 text-right">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-400">
                    No audit records found.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-[#0B3C9D] whitespace-nowrap">
                      {log.action}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700 font-mono">
                        {log.role || 'ADMIN'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-700 max-w-sm truncate">
                      {log.reason || 'Administrative action'}
                    </td>
                    <td className="py-3.5 px-4 text-xs font-mono text-slate-500 whitespace-nowrap">
                      {log.ip_address || '127.0.0.1'}
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-500">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={() => {
                          setSelectedLog(log);
                          setIsDetailOpen(true);
                        }}
                        className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-md"
                        title="View Event Details"
                      >
                        <Eye size={15} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Details Modal */}
      <Modal
        isOpen={isDetailOpen}
        onClose={() => setIsDetailOpen(false)}
        title={`Audit Event #${selectedLog?.id}: ${selectedLog?.action || ''}`}
        maxWidth="max-w-2xl"
      >
        <div className="space-y-3">
          {selectedLog && (
            <>
              <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 text-xs space-y-1.5">
                <p><strong>Action:</strong> <span className="font-mono text-[#0B3C9D]">{selectedLog.action}</span></p>
                <p><strong>Initiated By:</strong> User #{selectedLog.user_id || 'System'} ({selectedLog.role})</p>
                <p><strong>Timestamp:</strong> {new Date(selectedLog.timestamp).toLocaleString()}</p>
                <p><strong>Reason:</strong> {selectedLog.reason || 'None provided'}</p>
              </div>

              <div>
                <span className="text-xs font-bold uppercase text-slate-500 block mb-1">
                  Event Metadata & State Changes
                </span>
                <pre className="p-3 bg-slate-900 text-emerald-400 rounded-xl text-xs font-mono overflow-x-auto max-h-72">
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
