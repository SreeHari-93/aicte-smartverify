import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  PlusCircle,
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
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <MessageSquare size={22} className="text-[#0B3C9D]" />
            <h2 className="text-xl font-bold text-[#0B3C9D] tracking-tight">
              Grievance & Scrutiny Ticket Desk
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Lodge grievances, seek clarification regarding deficiency reports, or request scrutiny fee reconciliation.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Form: "Raise Complaint" Form */}
        <div className="lg:col-span-5 bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
          <div className="flex items-center gap-2 pb-4 border-b border-slate-100">
            <PlusCircle size={20} className="text-[#F58220]" />
            <h3 className="text-base font-bold text-[#0F2A5C] tracking-tight">
              Raise a New Grievance Ticket
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
              className="w-full h-11 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-[6px] transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50 select-none"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Submitting Ticket...</span>
                </>
              ) : (
                <>
                  <Send size={15} />
                  <span>Submit Grievance</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Table: Table of Past Complaints */}
        <div className="lg:col-span-7 bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
          <h3 className="text-base font-bold text-[#0B3C9D] pb-4 border-b border-slate-100 tracking-tight">
            Lodged Grievances & Status ({complaints.length})
          </h3>

          <div className="overflow-x-auto mt-4">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#E3F0FF] text-[#0B3C9D] uppercase text-[11px] font-bold tracking-wider">
                  <th className="py-3 px-3.5 rounded-l-md">Ticket ID</th>
                  <th className="py-3 px-3.5">Subject</th>
                  <th className="py-3 px-3.5">Raised On</th>
                  <th className="py-3 px-3.5">Status</th>
                  <th className="py-3 px-3.5 text-center rounded-r-md">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="py-12 text-center text-slate-400">
                      <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                      Loading grievance history...
                    </td>
                  </tr>
                ) : complaints.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-slate-400">
                      No complaints lodged yet.
                    </td>
                  </tr>
                ) : (
                  complaints.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3.5 px-3.5 font-mono font-bold text-[#0F2A5C] whitespace-nowrap">
                        {item.ticket_id}
                      </td>
                      <td className="py-3.5 px-3.5 font-semibold text-[#0F2A5C] max-w-[190px] truncate">
                        {item.subject}
                      </td>
                      <td className="py-3.5 px-3.5 text-slate-500 whitespace-nowrap">
                        {new Date(item.created_at).toLocaleDateString('en-GB')}
                      </td>
                      <td className="py-3.5 px-3.5 whitespace-nowrap">
                        <StatusPill status={item.status} />
                      </td>
                      <td className="py-3.5 px-3.5 text-center">
                        <button
                          onClick={() => handleOpenTicket(item)}
                          className="px-2.5 py-1.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded-[6px] text-xs font-semibold inline-flex items-center gap-1 transition-colors"
                        >
                          <Eye size={12} />
                          <span>Timeline</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
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
                      <span className="text-[10px] text-slate-400">
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
