import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  Search,
  Filter,
  CheckCircle2,
  Eye,
  Send,
  Loader2,
  RefreshCw,
  Building,
  Lock,
} from 'lucide-react';
import { adminApi, AdminComplaintOut } from '../../api/admin';
import { StatusPill } from '../../components/StatusPill';
import { Drawer } from '../../components/Drawer';

export const AdminComplaintsInboxPage: React.FC = () => {
  const [complaints, setComplaints] = useState<AdminComplaintOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters
  const [statusFilter, setStatusFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [priorityFilter, setPriorityFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected for Detail / Conversation
  const [selectedTicket, setSelectedTicket] = useState<AdminComplaintOut | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Reply / Note Form State
  const [replyText, setReplyText] = useState('');
  const [isInternalNote, setIsInternalNote] = useState(false);
  const [newStatus, setNewStatus] = useState<string>('');
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const data = await adminApi.listComplaints({
        status: statusFilter || undefined,
        category: categoryFilter || undefined,
        priority: priorityFilter || undefined,
        search: searchQuery || undefined,
      });
      setComplaints(data);
      if (selectedTicket) {
        const refreshed = data.find((c) => c.id === selectedTicket.id);
        if (refreshed) setSelectedTicket(refreshed);
      }
    } catch (err) {
      console.error('Failed to load complaints:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [statusFilter, categoryFilter, priorityFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  const handleOpenDetail = (ticket: AdminComplaintOut) => {
    setSelectedTicket(ticket);
    setReplyText('');
    setIsInternalNote(false);
    setNewStatus('');
    setActionSuccess(null);
    setIsDrawerOpen(true);
  };

  const handleSendReply = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket) return;
    if (!replyText.trim() && !newStatus) return;

    setIsSubmittingReply(true);
    setActionSuccess(null);
    try {
      const updated = await adminApi.replyComplaint(selectedTicket.id, {
        notes: replyText.trim() || `Status updated to ${newStatus}`,
        is_internal: isInternalNote,
        new_status: newStatus || undefined,
      });
      setSelectedTicket(updated);
      setReplyText('');
      setNewStatus('');
      setActionSuccess(
        isInternalNote
          ? 'Internal note logged (Admin only)'
          : 'Reply recorded; notification and email queued for registered institute email.'
      );
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit reply.');
    } finally {
      setIsSubmittingReply(false);
    }
  };

  return (
    <div className="space-y-6 pb-12 animate-fade-in">
      {/* Header Banner */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <MessageSquare size={22} className="text-[#0B3C9D]" />
            <h1 className="text-xl font-bold text-[#0B3C9D] tracking-tight">
              Regulatory Grievance & Complaint Desk
            </h1>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Central repository for deficiency disputes, scrutiny clarifications, and fee reconciliation tickets.
          </p>
        </div>
        <button
          onClick={fetchData}
          disabled={isLoading}
          className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold transition-colors shrink-0"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin text-[#F58220]' : ''} />
          <span>Refresh Inbox</span>
        </button>
      </div>

      {actionSuccess && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-bold flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-emerald-600" />
            <span>{actionSuccess}</span>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-600 hover:text-emerald-900 text-xs font-bold">
            Dismiss
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-[12px] p-4 shadow-[0_4px_12px_rgba(0,0,0,0.06)] border border-slate-200 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="flex-1 flex items-center gap-2">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search by ticket ID, subject, or institute name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full h-10 pl-9 pr-3 rounded-lg border border-slate-200 text-xs focus:border-[#0B3C9D] outline-none"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 h-10 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded-lg text-xs font-semibold shrink-0"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center gap-1 text-xs text-slate-500 font-semibold">
            <Filter size={14} />
            <span>Filters:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 text-xs bg-white text-slate-700 focus:border-[#0B3C9D] outline-none"
          >
            <option value="">Status: All</option>
            <option value="Open">Open</option>
            <option value="In Progress">In Review</option>
            <option value="Resolved">Resolved</option>
            <option value="Rejected">Rejected</option>
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 text-xs bg-white text-slate-700 focus:border-[#0B3C9D] outline-none"
          >
            <option value="">Priority: All</option>
            <option value="URGENT">Urgent</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="h-10 px-3 rounded-lg border border-slate-200 text-xs bg-white text-slate-700 focus:border-[#0B3C9D] outline-none max-w-[210px]"
          >
            <option value="">Category: All</option>
            <option value="Application Processing Delay">Application Processing Delay</option>
            <option value="Deficiency Report Discrepancy">Deficiency Report Discrepancy</option>
            <option value="Payment Reconciliation">Payment Reconciliation</option>
            <option value="Technical Portal Issue">Technical Portal Issue</option>
            <option value="Intake Allocation Query">Intake Allocation Query</option>
            <option value="Other Regulatory Query">Other Regulatory Query</option>
          </select>
        </div>
      </div>

      {/* Complaints Table */}
      <div className="bg-white rounded-[12px] shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#E3F0FF] text-[#0B3C9D] uppercase text-[11px] font-bold tracking-wider">
                <th className="py-3 px-4">Ticket Number</th>
                <th className="py-3 px-3">Institute</th>
                <th className="py-3 px-3">Category & Subject</th>
                <th className="py-3 px-3">Priority</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3">Created / Updated</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                    <span>Loading complaints inbox...</span>
                  </td>
                </tr>
              ) : complaints.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <CheckCircle2 size={28} className="mx-auto mb-2 text-emerald-500 opacity-60" />
                    <p className="font-semibold text-slate-600">No grievances in queue.</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      All raised complaints have been resolved or filtered out.
                    </p>
                  </td>
                </tr>
              ) : (
                complaints.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <span className="font-mono font-bold text-[#0F2A5C] text-[12px] block">
                        {c.ticket_id}
                      </span>
                      {c.application_ref && (
                        <span className="text-[10px] text-slate-400 font-mono">
                          App: {c.application_ref}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-3">
                      <div className="font-semibold text-[#0F2A5C] flex items-center gap-1.5">
                        <Building size={13} className="text-slate-400 shrink-0" />
                        <span className="truncate max-w-[170px]" title={c.institute_name}>
                          {c.institute_name}
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400 font-mono">
                        Inst #{c.institute_id}
                      </span>
                    </td>

                    <td className="py-3 px-3 max-w-[240px]">
                      <span className="inline-block px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 text-[10px] font-semibold mb-0.5">
                        {c.category}
                      </span>
                      <p className="font-bold text-[#0F2A5C] truncate" title={c.subject}>
                        {c.subject}
                      </p>
                    </td>

                    <td className="py-3 px-3">
                      <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-extrabold uppercase ${
                        c.priority === 'URGENT'
                          ? 'bg-red-100 text-red-800 border border-red-200'
                          : c.priority === 'HIGH'
                          ? 'bg-amber-100 text-amber-800'
                          : 'bg-slate-100 text-slate-700'
                      }`}>
                        {c.priority}
                      </span>
                    </td>

                    <td className="py-3 px-3 whitespace-nowrap">
                      <StatusPill status={c.status} />
                    </td>

                    <td className="py-3 px-3 text-slate-500 text-[11px] whitespace-nowrap">
                      <div>Created: {new Date(c.created_at).toLocaleDateString('en-GB')}</div>
                      <div className="text-[10px] text-slate-400">
                        Updated: {new Date(c.updated_at).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                      </div>
                    </td>

                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      <button
                        onClick={() => handleOpenDetail(c)}
                        className="px-2.5 py-1.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded text-[11px] font-semibold inline-flex items-center gap-1 transition-colors"
                      >
                        <Eye size={12} />
                        <span>Manage Thread</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Ticket Conversation Detail Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedTicket?.ticket_id || 'Ticket Conversation'}
        subtitle={selectedTicket?.subject}
      >
        {selectedTicket && (
          <div className="space-y-6 text-xs">
            {/* Metadata Card */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Current Status:</span>
                <StatusPill status={selectedTicket.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Priority:</span>
                <span className="font-bold text-[#0F2A5C]">{selectedTicket.priority}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Institute:</span>
                <span className="font-bold text-[#0F2A5C]">{selectedTicket.institute_name}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-slate-500 font-semibold">Category:</span>
                <span className="font-medium text-slate-700">{selectedTicket.category}</span>
              </div>
              <div>
                <span className="text-slate-500 font-semibold block mb-1">Grievance Description:</span>
                <div className="p-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 leading-relaxed font-sans">
                  {selectedTicket.description}
                </div>
              </div>
            </div>

            {/* Conversation Thread */}
            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-3 flex items-center justify-between">
                <span>Resolution Conversation & Timeline</span>
                <span className="text-[10px] text-slate-400 font-normal">
                  {selectedTicket.events.length} Event(s)
                </span>
              </h4>

              <div className="space-y-3">
                {selectedTicket.events.map((ev) => (
                  <div
                    key={ev.id}
                    className={`p-3 rounded-xl border text-xs leading-relaxed ${
                      ev.is_internal
                        ? 'bg-amber-50/70 border-amber-200 text-amber-950'
                        : ev.created_by.includes('Institute')
                        ? 'bg-slate-50 border-slate-200 text-slate-800'
                        : 'bg-blue-50/70 border-blue-200 text-blue-950'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1 pb-1 border-b border-black/5">
                      <div className="flex items-center gap-1.5 font-bold">
                        {ev.is_internal && (
                          <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-amber-200 text-amber-900 text-[9px] uppercase font-extrabold tracking-wider">
                            <Lock size={10} />
                            <span>Internal Note</span>
                          </span>
                        )}
                        <span>{ev.action}</span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        {new Date(ev.created_at).toLocaleString('en-GB')}
                      </span>
                    </div>
                    <p className="mt-1 whitespace-pre-wrap">{ev.notes}</p>
                    <div className="text-[10px] text-slate-500 mt-1.5 font-semibold">
                      Author: {ev.created_by}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Reply / Status Update Form */}
            <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider">
                Officer Reply / Internal Remark
              </h4>

              <form onSubmit={handleSendReply} className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="font-bold text-slate-700 block mb-1">Update Status (Optional)</label>
                    <select
                      value={newStatus}
                      onChange={(e) => setNewStatus(e.target.value)}
                      className="w-full h-9 px-2.5 rounded-lg border border-slate-300 text-slate-700 bg-white focus:border-[#0B3C9D] outline-none text-xs"
                    >
                      <option value="">Keep current ({selectedTicket.status})</option>
                      <option value="Open">Open</option>
                      <option value="In Progress">In Review</option>
                      <option value="Resolved">Resolved</option>
                      <option value="Rejected">Rejected</option>
                    </select>
                  </div>

                  <div>
                    <label className="font-bold text-slate-700 block mb-1">Visibility Mode</label>
                    <div className="flex items-center gap-2 h-9">
                      <label className="flex items-center gap-1.5 cursor-pointer text-slate-700 font-medium">
                        <input
                          type="checkbox"
                          checked={isInternalNote}
                          onChange={(e) => setIsInternalNote(e.target.checked)}
                          className="rounded text-[#0B3C9D] focus:ring-0"
                        />
                        <span className="text-[11px] flex items-center gap-1">
                          <Lock size={11} className={isInternalNote ? 'text-amber-600' : 'text-slate-400'} />
                          <span>Internal Only (Hide from Institute)</span>
                        </span>
                      </label>
                    </div>
                  </div>
                </div>

                <div>
                  <label className="font-bold text-slate-700 block mb-1">
                    {isInternalNote ? 'Confidential Officer Note' : 'Public Reply to Institute (Sends Email Notification)'}
                  </label>
                  <textarea
                    required={!newStatus}
                    rows={3}
                    placeholder={
                      isInternalNote
                        ? 'Private remarks visible only to scrutiny officers...'
                        : 'Explain the resolution, deficiency justification, or required next steps...'
                    }
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    className="w-full p-2.5 rounded-lg border border-slate-300 focus:border-[#0B3C9D] outline-none text-slate-800 resize-none text-xs"
                  />
                  {!isInternalNote && (
                    <span className="text-[10px] text-slate-400 block mt-0.5">
                      Submitting a public reply automatically queues an email and in-app notification to the registered institute email.
                    </span>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isSubmittingReply || (!replyText.trim() && !newStatus)}
                  className="w-full py-2.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white font-bold rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
                >
                  {isSubmittingReply ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Send size={14} />
                  )}
                  <span>{isInternalNote ? 'Log Internal Note' : 'Send Official Resolution'}</span>
                </button>
              </form>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
