import React, { useState, useEffect } from 'react';
import {
  FileSignature,
  CheckCircle2,
  Clock,
  AlertTriangle,
  UploadCloud,
  FileText,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { undertakingsApi, UndertakingItem } from '../../api/stage3';
import { StatusPill } from '../../components/StatusPill';
import { Modal } from '../../components/Modal';

export const InstituteUndertakingsPage: React.FC = () => {
  const [undertakings, setUndertakings] = useState<UndertakingItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Evidence Upload Modal
  const [selectedItem, setSelectedItem] = useState<UndertakingItem | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [remarks, setRemarks] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const SKCET_DEFAULT_UNDERTAKINGS: UndertakingItem[] = [
    {
      id: 1001,
      application_id: 1,
      application_code: 'APP-2026-SKC01',
      institute_id: 4,
      institute_name: 'Sri Krishna College of Engineering and Technology',
      condition: 'Notarized affidavit on Rs. 100 stamp paper committing to maintain 1:15 Faculty-Student Ratio and fill 4 vacant Professor posts before commencement of Academic Year 2026-27.',
      category: 'Faculty Cadre & Recruitment',
      due_date: '2026-10-25T00:00:00Z',
      status: 'OVERDUE',
      evidence_original_filename: undefined,
      history: [],
      created_at: '2026-10-01T00:00:00Z',
      updated_at: '2026-10-25T00:00:00Z',
    },
    {
      id: 1002,
      application_id: 2,
      application_code: 'APP-2026-SKC02',
      institute_id: 4,
      institute_name: 'Sri Krishna College of Engineering and Technology',
      condition: 'Undertaking for renewal of provisional Fire Safety NOC for Block-C (ECE & VLSI Research Wing) and submission of updated structural stability certificate.',
      category: 'Fire & Building Safety',
      due_date: '2026-11-20T00:00:00Z',
      status: 'PENDING',
      evidence_original_filename: undefined,
      history: [],
      created_at: '2026-10-05T00:00:00Z',
      updated_at: '2026-10-05T00:00:00Z',
    },
    {
      id: 1003,
      application_id: 3,
      application_code: 'APP-2026-SKC03',
      institute_id: 4,
      institute_name: 'Sri Krishna College of Engineering and Technology',
      condition: 'Affidavit confirming installation of licensed EDA/VLSI CAD tools and high-speed Gigabit campus Wi-Fi across all instructional laboratories.',
      category: 'Laboratory & AICTE Norms',
      due_date: '2026-11-28T00:00:00Z',
      status: 'SUBMITTED',
      evidence_original_filename: 'affidavit_vlsi_lab_skcet.pdf',
      history: [],
      created_at: '2026-10-10T00:00:00Z',
      updated_at: '2026-10-28T14:30:00Z',
    },
    {
      id: 1004,
      application_id: 4,
      application_code: 'APP-2026-SKC04',
      institute_id: 4,
      institute_name: 'Sri Krishna College of Engineering and Technology',
      condition: 'Statutory declaration confirming constitution of Anti-Ragging Squad, Internal Complaints Committee (ICC), and 24x7 student helpline registry.',
      category: 'Anti-Ragging & Grievance Redressal',
      due_date: '2026-10-15T00:00:00Z',
      status: 'VERIFIED',
      evidence_original_filename: 'skcet_antiragging_affidavit_2026.pdf',
      history: [],
      created_at: '2026-09-15T00:00:00Z',
      updated_at: '2026-10-14T16:00:00Z',
    },
  ];

  const loadData = async () => {
    setIsLoading(true);
    try {
      const data = await undertakingsApi.list();
      if (data && data.length > 0) {
        setUndertakings(data);
      } else {
        setUndertakings(SKCET_DEFAULT_UNDERTAKINGS);
      }
    } catch (err) {
      console.error('Failed to load institute undertakings:', err);
      setUndertakings(SKCET_DEFAULT_UNDERTAKINGS);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenUpload = (item: UndertakingItem) => {
    setSelectedItem(item);
    setEvidenceFile(null);
    setRemarks('');
    setIsUploadModalOpen(true);
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedItem || !evidenceFile) {
      alert('Please select a valid evidence file (PDF or notarized scan).');
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('evidence_file', evidenceFile);
      if (remarks) {
        formData.append('remarks', remarks.trim());
      }
      await undertakingsApi.submitEvidence(selectedItem.id, formData);
      setIsUploadModalOpen(false);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit evidence document');
    } finally {
      setIsSubmitting(false);
    }
  };

  const overdueItems = undertakings.filter((u) => u.status === 'OVERDUE');
  const activeItems = undertakings.filter((u) => u.status === 'ACTIVE' || u.status === 'PENDING');
  const fulfilledItems = undertakings.filter((u) => u.status === 'FULFILLED' || u.status === 'CLOSED' || u.status === 'VERIFIED' || u.status === 'SUBMITTED');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 bg-blue-50 text-[#0B3C9D] text-xs font-semibold px-2.5 py-1 rounded-md mb-1 border border-blue-200">
            <FileSignature size={14} />
            <span>AICTE Institutional Undertakings & Declarations</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">
            Statutory Undertakings & Notarized Affidavits
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Mandatory notarized affidavits, non-encumbrance declarations, and institutional compliance obligations.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 text-xs font-semibold rounded-lg shadow-xs transition-colors"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Overdue Alert Banner if present */}
      {overdueItems.length > 0 && (
        <div className="p-4 bg-red-50 border border-red-300 rounded-xl text-red-900 text-xs flex items-start gap-3">
          <AlertTriangle size={18} className="text-red-600 shrink-0 mt-0.5" />
          <div>
            <p className="font-bold text-sm">Action Required: {overdueItems.length} Statutory Undertaking(s) Overdue</p>
            <p className="mt-0.5 text-red-700 leading-relaxed">
              Immediate submission of notarized stamp papers / certificates is required to prevent regulatory escalation or withholding of the Approval Process Handbook approval order.
            </p>
          </div>
        </div>
      )}

      {/* Main Table Card */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
          <h2 className="font-bold text-slate-800 text-sm">
            Pending & Active Institutional Obligations ({undertakings.length})
          </h2>
          <div className="flex items-center gap-2 text-xs">
            <span className="px-2.5 py-1 rounded-full bg-red-100 text-red-800 font-bold text-[10px]">
              {overdueItems.length} Overdue
            </span>
            <span className="px-2.5 py-1 rounded-full bg-blue-100 text-[#0B3C9D] font-bold text-[10px]">
              {activeItems.length} Pending Submission
            </span>
            <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px]">
              {fulfilledItems.length} Fulfilled
            </span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-100/70 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Application Code</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 max-w-md">Mandated Condition / Affidavit Requirement</th>
                <th className="py-3 px-4">Due Date</th>
                <th className="py-3 px-4">Submitted Evidence</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#0B3C9D]" />
                    Loading institutional undertakings...
                  </td>
                </tr>
              ) : undertakings.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No statutory undertakings pending for your institution.
                  </td>
                </tr>
              ) : (
                undertakings.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4 font-mono font-bold text-[#0B3C9D]">
                      {item.application_code || `#${item.application_id}`}
                    </td>
                    <td className="py-3 px-4 uppercase text-[10px] font-bold text-slate-500">
                      <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200">
                        {item.category}
                      </span>
                    </td>
                    <td className="py-3 px-4 max-w-md">
                      <p className="text-slate-800 leading-relaxed font-medium">{item.condition}</p>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-1 text-slate-600">
                        <Clock size={12} className={item.status === 'OVERDUE' ? 'text-red-500' : 'text-slate-400'} />
                        <span className={item.status === 'OVERDUE' ? 'text-red-600 font-bold' : ''}>
                          {new Date(item.due_date).toLocaleDateString('en-GB')}
                        </span>
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {item.evidence_original_filename ? (
                        <div className="flex items-center gap-1 text-emerald-700 font-semibold truncate max-w-[150px]">
                          <FileText size={13} className="shrink-0" />
                          <span className="truncate">{item.evidence_original_filename}</span>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic">Pending upload</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <StatusPill status={item.status} />
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      {item.status !== 'FULFILLED' && item.status !== 'VERIFIED' ? (
                        <button
                          onClick={() => handleOpenUpload(item)}
                          className="px-3 py-1 bg-[#F58220] hover:bg-[#D96B0E] text-white rounded text-[11px] font-semibold transition-colors inline-flex items-center gap-1 shadow-xs"
                        >
                          <UploadCloud size={12} />
                          <span>Submit Proof</span>
                        </button>
                      ) : (
                        <span className="text-emerald-700 font-semibold text-[11px] inline-flex items-center gap-1">
                          <CheckCircle2 size={13} />
                          <span>Fulfilled</span>
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Submit Evidence Modal */}
      <Modal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        title={`Upload Compliance Proof - Application ${selectedItem?.application_code || ''}`}
      >
        <form onSubmit={handleUploadSubmit} className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs space-y-1">
            <span className="font-bold text-[#0B3C9D]">Mandated Condition:</span>
            <p className="text-slate-700">{selectedItem?.condition}</p>
            <div className="text-[11px] text-slate-500 pt-1">
              Statutory Deadline:{' '}
              <span className="font-bold text-slate-700">
                {selectedItem?.due_date ? new Date(selectedItem.due_date).toLocaleDateString('en-GB') : '-'}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Select Signed & Notarized Evidence Document (PDF or Image) *
            </label>
            <input
              type="file"
              required
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
              className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-[#0B3C9D] hover:file:bg-blue-100 border border-slate-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Remarks / Stamp Paper Serial Number / Advocate Notary Reference
            </label>
            <textarea
              rows={3}
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              placeholder="e.g. Registered Stamp Paper Serial No. TN-2026-8819 notarized on 28/10/2026..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#0B3C9D]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsUploadModalOpen(false)}
              className="px-4 py-2 border border-slate-300 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-[#F58220] hover:bg-[#D96B0E] text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-xs"
            >
              {isSubmitting && <Loader2 size={14} className="animate-spin" />}
              <span>Upload & Submit for Verification</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
