import React, { useState, useEffect } from 'react';
import {
  Hourglass,
  Clock,
  CheckCircle2,
  UploadCloud,
  FileText,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { validityApi, ValidityRecordItem } from '../../api/stage3';
import { StatusPill } from '../../components/StatusPill';
import { Modal } from '../../components/Modal';

export const InstituteDocumentValidityPage: React.FC = () => {
  const [records, setRecords] = useState<ValidityRecordItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Renewal Upload Modal
  const [renewRecord, setRenewRecord] = useState<ValidityRecordItem | null>(null);
  const [isRenewModalOpen, setIsRenewModalOpen] = useState(false);
  const [renewalFile, setRenewalFile] = useState<File | null>(null);
  const [newIssueDate, setNewIssueDate] = useState('');
  const [newExpiryDate, setNewExpiryDate] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const data = await validityApi.list();
      setRecords(data);
    } catch (err) {
      console.error('Failed to load institute validity records:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenRenew = (r: ValidityRecordItem) => {
    setRenewRecord(r);
    setRenewalFile(null);
    setNewIssueDate(new Date().toISOString().slice(0, 10));
    const nextYear = new Date();
    nextYear.setFullYear(nextYear.getFullYear() + 1);
    setNewExpiryDate(nextYear.toISOString().slice(0, 10));
    setIsRenewModalOpen(true);
  };

  const handleRenewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renewRecord || !renewalFile) {
      alert('Please select a renewed document file.');
      return;
    }
    if (!newIssueDate || !newExpiryDate) {
      alert('Issue date and expiry date are required.');
      return;
    }

    setIsSubmitting(true);
    try {
      const formData = new FormData();
      formData.append('renewal_file', renewalFile);
      formData.append('new_issue_date', newIssueDate);
      formData.append('new_expiry_date', newExpiryDate);
      await validityApi.submitRenewal(renewRecord.id, formData);
      setIsRenewModalOpen(false);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit document renewal');
    } finally {
      setIsSubmitting(false);
    }
  };


  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="bg-white rounded-xl p-6 border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 bg-blue-50 text-[#0B3C9D] text-xs font-semibold px-2.5 py-1 rounded-md mb-1 border border-blue-200">
            <Hourglass size={14} />
            <span>AICTE Document Validity & Expiry Register</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-800">
            Statutory Document Validity & Renewal
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Real-time validity monitoring for Fire Safety NOC, Building Stability, Land Leases, and NBA Accreditations.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-300 hover:border-[#0B3C9D] text-slate-700 text-xs font-semibold rounded-lg shadow-xs transition-colors"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          Refresh Register
        </button>
      </div>


      {/* Main Register Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/50 flex items-center justify-between">
          <h2 className="font-bold text-slate-800 text-sm">
            Monitored Institutional Statutory Certificates ({records.length})
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-100/70 text-slate-600 font-bold uppercase tracking-wider text-[11px]">
                <th className="py-3 px-4">Document / Certificate</th>
                <th className="py-3 px-4">Issuing Authority</th>
                <th className="py-3 px-4">Issue Date</th>
                <th className="py-3 px-4">Expiry Date</th>
                <th className="py-3 px-4">Days Remaining</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-center">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#0B3C9D]" />
                    Loading monitored validity certificates...
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No monitored statutory documents found.
                  </td>
                </tr>
              ) : (
                records.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 flex items-center gap-1.5">
                        <FileText size={14} className="text-[#0B3C9D]" />
                        <span>{r.document_name}</span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-400 ml-5">
                        {r.certificate_number || r.document_type_code}
                      </div>
                      {r.is_lease && (
                        <span className="ml-5 mt-0.5 inline-block px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                          Registered Lease Deed
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {r.issuing_authority || 'Statutory Authority'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-slate-600">
                      {r.issue_date ? new Date(r.issue_date).toLocaleDateString('en-GB') : '-'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-semibold text-slate-800">
                      {new Date(r.expiry_date).toLocaleDateString('en-GB')}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {r.days_left !== undefined && r.days_left !== null ? (
                        r.days_left < 0 ? (
                          <span className="font-bold text-red-600 flex items-center gap-1">
                            <Clock size={12} />
                            <span>Expired {Math.abs(r.days_left)} days ago</span>
                          </span>
                        ) : r.days_left <= r.expiring_soon_window_days ? (
                          <span className="font-bold text-amber-600 flex items-center gap-1">
                            <Clock size={12} />
                            <span>{r.days_left} days left</span>
                          </span>
                        ) : (
                          <span className="text-slate-600">{r.days_left} days</span>
                        )
                      ) : (
                        '-'
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <StatusPill status={r.status} />
                    </td>
                    <td className="py-3 px-4 text-center whitespace-nowrap">
                      {r.status === 'RENEWAL_SUBMITTED' ? (
                        <span className="text-amber-700 font-semibold text-[11px] inline-flex items-center gap-1">
                          <CheckCircle2 size={13} />
                          <span>Renewal Pending Review</span>
                        </span>
                      ) : (
                        <button
                          onClick={() => handleOpenRenew(r)}
                          className="px-3 py-1 bg-[#F58220] hover:bg-[#D96B0E] text-white rounded text-[11px] font-semibold transition-colors inline-flex items-center gap-1 shadow-xs"
                        >
                          <UploadCloud size={12} />
                          <span>Renew Document</span>
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Renew Document Modal */}
      <Modal
        isOpen={isRenewModalOpen}
        onClose={() => setIsRenewModalOpen(false)}
        title={`Renew Statutory Certificate - ${renewRecord?.document_name || ''}`}
      >
        <form onSubmit={handleRenewSubmit} className="space-y-4">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs space-y-1">
            <span className="font-bold text-[#0B3C9D]">Existing Document on Record:</span>
            <p className="text-slate-700">
              {renewRecord?.document_name} ({renewRecord?.certificate_number})
            </p>
            <div className="text-[11px] text-slate-500 pt-1">
              Current Expiry Date:{' '}
              <span className="font-bold text-slate-700">
                {renewRecord?.expiry_date ? new Date(renewRecord.expiry_date).toLocaleDateString('en-GB') : '-'}
              </span>
            </div>
            <p className="text-[11px] text-blue-900 mt-1">
              Your uploaded renewal document will be linked to this certificate record and submitted to AICTE regional officers for verification.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Upload Renewed Certificate / NOC (PDF or Scanned Document) *
            </label>
            <input
              type="file"
              required
              accept=".pdf,.jpg,.jpeg,.png"
              onChange={(e) => setRenewalFile(e.target.files?.[0] || null)}
              className="w-full text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-[#0B3C9D] hover:file:bg-blue-100 border border-slate-300 rounded-lg"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                New Certificate Issue Date *
              </label>
              <input
                type="date"
                required
                value={newIssueDate}
                onChange={(e) => setNewIssueDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#0B3C9D]"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                New Certificate Expiry Date *
              </label>
              <input
                type="date"
                required
                value={newExpiryDate}
                onChange={(e) => setNewExpiryDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-xs focus:outline-none focus:ring-1 focus:ring-[#0B3C9D]"
              />
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsRenewModalOpen(false)}
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
              <span>Upload Renewal Certificate</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
