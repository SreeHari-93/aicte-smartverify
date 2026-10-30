import React, { useState, useEffect } from 'react';
import {
  FileText,
  Plus,
  Eye,
  Loader2,
  CheckCircle,
} from 'lucide-react';
import {
  instituteApi,
  ApplicationItem,
  ApplicationListResponse,
} from '../../api/institute';
import { StatusPill } from '../../components/StatusPill';
import { Modal } from '../../components/Modal';
import { Drawer } from '../../components/Drawer';

export const ApplicationsPage: React.FC = () => {
  const [data, setData] = useState<ApplicationListResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeFilter, setActiveFilter] = useState('ALL');

  // Modal State for New Application
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [category, setCategory] = useState('Extension of Approval (EoA)');
  const [academicYear, setAcademicYear] = useState('2026-2027');
  const [programme, setProgramme] = useState('Engineering & Technology');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createMsg, setCreateMsg] = useState<string | null>(null);

  // Drawer State for Viewing Application Details
  const [selectedApp, setSelectedApp] = useState<ApplicationItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const fetchApplications = async () => {
    try {
      setIsLoading(true);
      const res = await instituteApi.getApplications();
      setData(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setCreateMsg(null);
    try {
      await instituteApi.createApplicationDraft({
        category,
        academic_year: academicYear,
        programme,
      });
      setCreateMsg('Draft application successfully registered!');
      setTimeout(() => {
        setIsModalOpen(false);
        setCreateMsg(null);
        fetchApplications();
      }, 1400);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const stats = data?.stats || { draft: 3, submitted: 4, under_review: 3, approved: 79, rejected: 19, total: 108 };

  const filteredItems = (data?.items || []).filter((item) => {
    if (activeFilter === 'ALL') return true;
    return item.status.toUpperCase() === activeFilter;
  });

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* Page Header Card with Stat Chips and "New Application" Action */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <FileText size={22} className="text-[#0B3C9D]" />
            <h2 className="text-xl font-bold text-[#0B3C9D] tracking-tight">
              Institutional Applications
            </h2>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Manage your AICTE Approval Process Handbook (APH) submissions and deficiency tracking.
          </p>
        </div>

        {/* Action: "New Application" orange button */}
        <button
          onClick={() => {
            setIsModalOpen(true);
          }}
          className="px-5 py-2.5 bg-[#F58220] hover:bg-[#E06F0F] text-white text-xs font-semibold rounded-[6px] transition-colors flex items-center justify-center gap-2 shadow-sm select-none"
        >
          <Plus size={16} />
          <span>New Application</span>
        </button>
      </div>

      {/* Stat Chips Row */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        <button
          onClick={() => setActiveFilter('ALL')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
            activeFilter === 'ALL'
              ? 'bg-[#0B3C9D] text-white'
              : 'bg-white text-slate-700 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          All Applications ({stats.total})
        </button>
        <button
          onClick={() => setActiveFilter('DRAFT')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
            activeFilter === 'DRAFT'
              ? 'bg-[#ECE8FB] text-[#4A3B82] border-2 border-[#4A3B82]'
              : 'bg-white text-slate-700 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          Draft ({stats.draft})
        </button>
        <button
          onClick={() => setActiveFilter('SUBMITTED')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
            activeFilter === 'SUBMITTED'
              ? 'bg-[#FFF0D6] text-[#B85700] border-2 border-[#B85700]'
              : 'bg-white text-slate-700 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          Submitted ({stats.submitted})
        </button>
        <button
          onClick={() => setActiveFilter('UNDER_REVIEW')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
            activeFilter === 'UNDER_REVIEW'
              ? 'bg-[#FFF0D6] text-[#B85700] border-2 border-[#B85700]'
              : 'bg-white text-slate-700 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          Under Review ({stats.under_review})
        </button>
        <button
          onClick={() => setActiveFilter('APPROVED')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
            activeFilter === 'APPROVED'
              ? 'bg-[#E2F6E6] text-[#1E7036] border-2 border-[#1E7036]'
              : 'bg-white text-slate-700 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          Approved ({stats.approved})
        </button>
        <button
          onClick={() => setActiveFilter('REJECTED')}
          className={`px-4 py-2 rounded-full text-xs font-semibold whitespace-nowrap transition-colors ${
            activeFilter === 'REJECTED'
              ? 'bg-[#FDE7E9] text-[#C62828] border-2 border-[#C62828]'
              : 'bg-white text-slate-700 hover:bg-slate-50 border border-slate-200'
          }`}
        >
          Rejected ({stats.rejected})
        </button>
      </div>

      {/* Applications Table Card */}
      <div className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#E3F0FF] text-[#0B3C9D] uppercase text-[11px] font-bold tracking-wider">
                <th className="py-3 px-4 rounded-l-md">Application ID</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4">Academic Year</th>
                <th className="py-3 px-4">Programme</th>
                <th className="py-3 px-4">Filed On</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-center rounded-r-md">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-slate-400">
                    <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                    Loading applications list...
                  </td>
                </tr>
              ) : filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-400">
                    No applications found in this filter category.
                  </td>
                </tr>
              ) : (
                filteredItems.map((app) => (
                  <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3.5 px-4 font-mono font-bold text-[#0F2A5C]">
                      {app.application_id}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-[#0F2A5C] max-w-xs truncate">
                      {app.category}
                    </td>
                    <td className="py-3.5 px-4">{app.academic_year}</td>
                    <td className="py-3.5 px-4 text-slate-500">{app.programme}</td>
                    <td className="py-3.5 px-4 text-slate-500 whitespace-nowrap">
                      {app.filed_on ? new Date(app.filed_on).toLocaleDateString('en-GB') : 'Draft (Unsubmitted)'}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusPill status={app.status} />
                    </td>
                    <td className="py-3.5 px-4 text-center">
                      <button
                        onClick={() => {
                          setSelectedApp(app);
                          setIsDrawerOpen(true);
                        }}
                        className="px-3 py-1.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white rounded-[6px] text-xs font-semibold inline-flex items-center gap-1.5 transition-colors"
                      >
                        <Eye size={13} />
                        <span>View</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* New Application Form Wizard Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Start New AICTE Application"
      >
        <form onSubmit={handleCreateDraft} className="space-y-4 text-xs">
          {createMsg && (
            <div className="p-3 bg-green-50 border border-green-200 text-[#1E7036] rounded-lg font-semibold flex items-center gap-2">
              <CheckCircle size={16} />
              <span>{createMsg}</span>
            </div>
          )}

          {/* Wizard step indicator */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <span className="text-xs font-bold text-[#0B3C9D] uppercase tracking-wider">
              Step 1: Programme & Category Details
            </span>
            <span className="text-[11px] font-semibold text-slate-400">Step 1 of 3</span>
          </div>

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">Application Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
            >
              <option value="Extension of Approval (EoA)">Extension of Approval (EoA)</option>
              <option value="Increase in Intake / Additional Course">Increase in Intake / Additional Course</option>
              <option value="Introduction of New Programme">Introduction of New Programme</option>
              <option value="Change of Site / Location">Change of Site / Location</option>
              <option value="Conversion of Diploma to Degree">Conversion of Diploma to Degree</option>
              <option value="Closure of Course / Institute">Closure of Course / Institute</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Academic Year</label>
              <select
                value={academicYear}
                onChange={(e) => setAcademicYear(e.target.value)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              >
                <option value="2026-2027">2026-2027</option>
                <option value="2027-2028">2027-2028</option>
              </select>
            </div>
            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">Programme Stream</label>
              <select
                value={programme}
                onChange={(e) => setProgramme(e.target.value)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none"
              >
                <option value="Engineering & Technology">Engineering & Technology</option>
                <option value="Management (MBA)">Management (MBA)</option>
                <option value="Computer Applications (MCA)">Computer Applications (MCA)</option>
                <option value="Pharmacy">Pharmacy</option>
                <option value="Architecture & Planning">Architecture & Planning</option>
              </select>
            </div>
          </div>

          <div className="p-3 bg-blue-50 border border-blue-100 rounded-lg text-slate-600">
            <p className="font-semibold text-[#0B3C9D] mb-0.5">Note on Subsequent Steps:</p>
            <p className="text-[11px] leading-relaxed">
              Step 2 and 3 (Document Attachment, OCR Scrutiny & Digital Signatures) will unlock after saving this draft.
            </p>
          </div>

          <div className="pt-4 flex justify-end gap-2.5">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 border border-slate-200 rounded-[6px] text-slate-600 font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-5 py-2 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-[6px] transition-colors flex items-center gap-1.5 disabled:opacity-50"
            >
              {isSubmitting && <Loader2 size={14} className="animate-spin" />}
              <span>Save Draft & Proceed</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* View Application Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedApp?.application_id || 'Application Overview'}
        subtitle={selectedApp?.category}
      >
        {selectedApp && (
          <div className="space-y-6 text-xs">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Filing Status:</span>
                <StatusPill status={selectedApp.status} />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Academic Year:</span>
                <span className="font-bold text-[#0F2A5C]">{selectedApp.academic_year}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Programme Division:</span>
                <span className="font-semibold text-slate-700">{selectedApp.programme}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Filing Date:</span>
                <span className="font-semibold text-slate-700">
                  {selectedApp.filed_on
                    ? new Date(selectedApp.filed_on).toLocaleString('en-GB')
                    : 'Unsubmitted Draft'}
                </span>
              </div>
            </div>

            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-2">
                Scrutiny Timeline
              </h4>
              <div className="space-y-2 border-l-2 border-[#F58220] pl-4 py-1">
                <div>
                  <span className="font-bold text-[#0F2A5C] block">Application Initialized</span>
                  <span className="text-slate-400 text-[10px]">
                    {new Date(selectedApp.created_at).toLocaleDateString('en-GB')}
                  </span>
                </div>
                {selectedApp.status === 'APPROVED' && (
                  <div>
                    <span className="font-bold text-[#1E7036] block">AICTE Council Approval Granted</span>
                    <span className="text-slate-400 text-[10px]">Verified under handbook chapter 2</span>
                  </div>
                )}
                {selectedApp.status === 'REJECTED' && (
                  <div>
                    <span className="font-bold text-[#C62828] block">Disapproved due to Deficiency</span>
                    <span className="text-slate-400 text-[10px]">Show cause compliance pending</span>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-4">
              <button
                onClick={() => (window.location.href = '/institute/validation')}
                className="w-full py-2.5 bg-[#0B3C9D] hover:bg-[#092E7A] text-white font-semibold rounded-[6px] transition-colors"
              >
                Inspect AI Validation Scrutiny
              </button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};
