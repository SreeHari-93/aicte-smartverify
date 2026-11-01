import React, { useState, useEffect } from 'react';
import {
  Eye,
  CheckCircle,
  Send,
  Loader2,
} from 'lucide-react';
import {
  instituteApi,
  ComplaintItem,
  ApplicationItem,
} from '../../api/institute';
import { StatusPill } from '../../components/StatusPill';
import { DataTable, ColumnDef } from '../../components/DataTable';
import { Drawer } from '../../components/Drawer';

export const ComplaintsPage: React.FC = () => {
  const [complaints, setComplaints] = useState<ComplaintItem[]>([]);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Form State
  const [category, setCategory] = useState('Application Processing Delay');
  const [relatedAppId, setRelatedAppId] = useState<number | undefined>();
  const [subject, setSubject] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Drawer State
  const [selectedTicket, setSelectedTicket] = useState<ComplaintItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      const [cRes, aRes] = await Promise.all([
        instituteApi.getComplaints(),
        instituteApi.getApplications(),
      ]);
      setComplaints(cRes);
      setApplications(aRes.items || []);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !description.trim()) return;

    setIsSubmitting(true);
    setSuccessMsg(null);

    try {
      const res = await instituteApi.raiseComplaint({
        category,
        related_application_id: relatedAppId,
        subject,
        description,
      });
      setSuccessMsg(`Ticket created successfully! Ref: ${res.ticket_id}`);
      setSubject('');
      setDescription('');
      fetchData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit complaint.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenTicket = (ticket: ComplaintItem) => {
    setSelectedTicket(ticket);
    setIsDrawerOpen(true);
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Page Title Card */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Complaints
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Submit grievances and track responses.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Form: "Raise Complaint" Form */}
        <div className="lg:col-span-5 bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
          <div className="pb-4 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-900">
              Raise complaint
            </h3>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 mt-4 text-xs">
            {successMsg && (
              <div className="p-3 bg-green-50 border border-green-200 text-[#1E7036] rounded-lg font-semibold flex items-center gap-2">
                <CheckCircle size={16} />
                <span>{successMsg}</span>
              </div>
            )}

            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Grievance Category</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              >
                <option value="Application Processing Delay">Application Processing Delay</option>
                <option value="Deficiency Report Discrepancy">Deficiency Report Discrepancy</option>
                <option value="Payment Reconciliation">Payment Reconciliation</option>
                <option value="Technical Portal Issue">Technical Portal Issue</option>
                <option value="Intake Allocation Query">Intake Allocation Query</option>
                <option value="Other Regulatory Query">Other Regulatory Query</option>
              </select>
            </div>

            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">
                Related Application Reference (Optional)
              </label>
              <select
                value={relatedAppId || ''}
                onChange={(e) => setRelatedAppId(e.target.value ? Number(e.target.value) : undefined)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none font-mono"
              >
                <option value="">-- None / General Inquiry --</option>
                {applications.slice(0, 15).map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.application_id} ({a.category.substring(0, 24)})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Subject</label>
              <input
                type="text"
                required
                placeholder="Brief summary of the issue..."
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] focus:border-[#F58220] outline-none"
              />
            </div>

            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Detailed Explanation</label>
              <textarea
                required
                rows={4}
                placeholder="Please describe the discrepancy, application sections involved, and requested resolution..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full p-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] focus:border-[#F58220] outline-none resize-none"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full h-10 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-sm disabled:bg-slate-300 disabled:text-slate-600 disabled:cursor-not-allowed select-none text-xs"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Submitting complaint...</span>
                </>
              ) : (
                <>
                  <Send size={14} />
                  <span>Submit complaint</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Table: Table of Past Complaints */}
        <div className="lg:col-span-7 bg-white rounded-xl p-6 border border-slate-200 shadow-sm">
          <h3 className="text-sm font-semibold text-slate-900 pb-4 border-b border-slate-100">
            Complaints archive ({complaints.length})
          </h3>

          <div className="mt-4">
            {(() => {
              const columns: ColumnDef<ComplaintItem>[] = [
                {
                  key: 'ticket_id',
                  header: 'Ticket ID',
                  width: '20%',
                  align: 'left',
                  render: (item) => (
                    <span className="font-mono font-medium text-[#0B3C9D] text-xs">
                      {item.ticket_id}
                    </span>
                  ),
                },
                {
                  key: 'subject',
                  header: 'Subject',
                  width: '38%',
                  align: 'left',
                  render: (item) => (
                    <span className="text-slate-800 text-xs font-medium line-clamp-2 block" title={item.subject}>
                      {item.subject}
                    </span>
                  ),
                },
                {
                  key: 'date',
                  header: 'Date',
                  width: '16%',
                  align: 'left',
                  render: (item) => (
                    <span className="text-slate-600 text-xs">
                      {new Date(item.created_at).toLocaleDateString('en-GB')}
                    </span>
                  ),
                },
                {
                  key: 'status',
                  header: 'Status',
                  width: '14%',
                  align: 'left',
                  render: (item) => <StatusPill status={item.status} />,
                },
                {
                  key: 'action',
                  header: 'Action',
                  width: '12%',
                  align: 'right',
                  render: (item) => (
                    <button
                      onClick={() => handleOpenTicket(item)}
                      className="px-2.5 py-1 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded text-xs font-medium inline-flex items-center gap-1 transition-colors"
                    >
                      <Eye size={11} />
                      <span>View</span>
                    </button>
                  ),
                },
              ];

              return (
                <DataTable
                  columns={columns}
                  data={complaints}
                  keyExtractor={(item) => item.id}
                  isLoading={isLoading}
                  emptyMessage="No complaints raised yet."
                  isLong={complaints.length > 12}
                />
              );
            })()}
          </div>
        </div>
      </div>

      {/* Ticket Timeline Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedTicket?.ticket_id || 'Ticket Scrutiny History'}
        subtitle={selectedTicket?.category}
      >
        {selectedTicket && (
          <div className="space-y-6 text-xs">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5">
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-semibold">Status:</span>
                <StatusPill status={selectedTicket.status} />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-semibold">Lodged Date:</span>
                <span className="font-semibold text-slate-800">
                  {new Date(selectedTicket.created_at).toLocaleString('en-GB')}
                </span>
              </div>
              <div>
                <span className="text-slate-500 font-semibold block mb-0.5">Subject:</span>
                <p className="font-bold text-[#0F2A5C]">{selectedTicket.subject}</p>
              </div>
              <div>
                <span className="text-slate-500 font-semibold block mb-0.5">Description:</span>
                <p className="text-slate-700 leading-relaxed bg-white p-2.5 rounded border border-slate-200">
                  {selectedTicket.description}
                </p>
              </div>
            </div>

            {/* Event Timeline */}
            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-3">
                Scrutiny Resolution Timeline
              </h4>
              <div className="space-y-4 border-l-2 border-[#0B3C9D] pl-4 py-1">
                {selectedTicket.events.map((ev) => (
                  <div key={ev.id} className="relative">
                    <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-[#0B3C9D]" />
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[#0F2A5C] text-xs">{ev.action}</span>
                      <span className="text-[10px] text-slate-600">
                        {new Date(ev.created_at).toLocaleString('en-GB')}
                      </span>
                    </div>
                    <p className="text-slate-600 mt-0.5 text-xs">{ev.notes}</p>
                    <span className="inline-block text-[10px] font-semibold text-[#F58220] mt-1 bg-orange-50 px-2 py-0.5 rounded">
                      Officer: {ev.created_by}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
