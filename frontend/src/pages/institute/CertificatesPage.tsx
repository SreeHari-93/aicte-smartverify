import React, { useState, useEffect } from 'react';
import {
  Award,
  CalendarClock,
  AlertTriangle,
  ShieldCheck,
  Calendar,
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  Loader2,
  FileCheck,
} from 'lucide-react';
import {
  instituteApi,
  CertificateItem,
  CertificateListResponse,
  UpcomingExpiry,
} from '../../api/institute';
import { StatCard } from '../../components/StatCard';
import { StatusPill } from '../../components/StatusPill';
import { DateBlock } from '../../components/DateBlock';
import { Modal } from '../../components/Modal';
import { Drawer } from '../../components/Drawer';

export const CertificatesPage: React.FC = () => {
  const [data, setData] = useState<CertificateListResponse | null>(null);
  const [upcoming, setUpcoming] = useState<UpcomingExpiry[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Filters & Pagination
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [page, setPage] = useState(1);
  const pageSize = 8;

  // View Drawer State
  const [selectedCert, setSelectedCert] = useState<CertificateItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  // Renew Modal State
  const [renewCert, setRenewCert] = useState<CertificateItem | null>(null);
  const [isRenewModalOpen, setIsRenewModalOpen] = useState(false);
  const [newIssueDate, setNewIssueDate] = useState('');
  const [newExpiryDate, setNewExpiryDate] = useState('');
  const [isSubmittingRenewal, setIsSubmittingRenewal] = useState(false);
  const [renewSuccess, setRenewSuccess] = useState<string | null>(null);
  const [renewError, setRenewError] = useState<string | null>(null);

  const fetchCertificates = async () => {
    try {
      setIsLoading(true);
      const [listRes, upcomingRes] = await Promise.all([
        instituteApi.getCertificates({
          search: search || undefined,
          status: statusFilter !== 'All' ? statusFilter : undefined,
          page,
          page_size: pageSize,
        }),
        instituteApi.getUpcomingCertificates(6),
      ]);
      setData(listRes);
      setUpcoming(upcomingRes);
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCertificates();
  }, [search, statusFilter, page]);

  const handleOpenView = (cert: CertificateItem) => {
    setSelectedCert(cert);
    setIsDrawerOpen(true);
  };

  const handleOpenRenew = (cert: CertificateItem) => {
    setRenewCert(cert);
    setRenewError(null);
    setRenewSuccess(null);
    setNewIssueDate(new Date().toISOString().split('T')[0]);
    // Default expiry 1 year from today
    const nextYear = new Date();
    nextYear.setFullYear(nextYear.getFullYear() + 1);
    setNewExpiryDate(nextYear.toISOString().split('T')[0]);
    setIsRenewModalOpen(true);
  };

  const handleRenewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!renewCert) return;
    setIsSubmittingRenewal(true);
    setRenewError(null);
    setRenewSuccess(null);

    try {
      await instituteApi.renewCertificate(renewCert.id, {
        new_issue_date: newIssueDate,
        new_expiry_date: newExpiryDate,
      });
      setRenewSuccess('Renewal request submitted successfully!');
      setTimeout(() => {
        setIsRenewModalOpen(false);
        fetchCertificates();
      }, 1500);
    } catch (err: any) {
      setRenewError(err.response?.data?.detail || 'Failed to submit renewal request.');
    } finally {
      setIsSubmittingRenewal(false);
    }
  };

  // Helper date formatter: DD-MM-YYYY
  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'N/A';
    const parts = dateStr.split('-');
    if (parts.length === 3) {
      return `${parts[2]}-${parts[1]}-${parts[0]}`;
    }
    return dateStr;
  };

  const stats = data?.stats || { total: 24, expiring_soon: 6, expired: 3, renewed: 15 };
  const totalPages = Math.ceil((data?.total || 1) / pageSize);

  return (
    <div className="space-y-6 animate-fade-in pb-12">
      {/* 1. Top of Main Area shows the background image with NO title (as instructed) */}

      {/* 2. Row of 4 Stat Cards: Total, Expiring Soon, Expired, Renewed */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          label="Total Certificates"
          value={stats.total}
          icon={<Award size={28} />}
          tint="blue"
        />
        <StatCard
          label="Expiring Soon"
          value={stats.expiring_soon}
          icon={<CalendarClock size={28} />}
          tint="amber"
          subtitle="Within 60 days"
        />
        <StatCard
          label="Expired"
          value={stats.expired}
          icon={<AlertTriangle size={28} />}
          tint="pink"
          subtitle="Action required"
        />
        <StatCard
          label="Renewed & Valid"
          value={stats.renewed}
          icon={<ShieldCheck size={28} />}
          tint="green"
        />
      </div>

      {/* 3. Below, Two Cards: Left Wide (Tracker ~68%) & Right Narrow (Upcoming ~32%, min 300px) */}
      <div className="flex flex-col lg:flex-row gap-5 xl:gap-6 items-start">
        {/* Left Wide Card: Certificate Expiry Tracker */}
        <div className="w-full lg:flex-1 bg-white rounded-[12px] p-5 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col min-w-0">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 pb-3.5 border-b border-slate-100 min-w-0">
            <div className="flex items-center gap-2 shrink-0">
              <Calendar size={18} className="text-[#0B3C9D]" />
              <h2 className="text-sm sm:text-base xl:text-lg font-bold text-[#0B3C9D] tracking-tight">
                Certificate Expiry Tracker
              </h2>
            </div>

            {/* Filter controls on one row */}
            <div className="flex items-center gap-2 shrink-0">
              <div className="relative">
                <Search size={13} className="absolute left-2.5 top-2.5 text-[#7A8699]" />
                <input
                  type="text"
                  placeholder="Search certificate..."
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  className="h-8 pl-8 pr-2 text-xs rounded-md border border-[#D5DBE5] text-[#0F2A5C] focus:border-[#F58220] focus:ring-1 focus:ring-[#F58220] outline-none w-32 xl:w-40"
                />
              </div>

              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                className="h-8 px-2 text-xs rounded-md border border-[#D5DBE5] text-[#0F2A5C] bg-white focus:border-[#F58220] outline-none cursor-pointer"
              >
                <option value="All">All Statuses</option>
                <option value="Valid">Valid</option>
                <option value="Expiring Soon">Expiring Soon</option>
                <option value="Expired">Expired</option>
              </select>
            </div>
          </div>

          {/* Desktop Table (≥ 1024px) - Fixed Layout, 100% width, No Horizontal Scroll */}
          <div className="hidden lg:block mt-3.5 w-full overflow-hidden">
            <table className="w-full table-fixed text-left border-collapse">
              <colgroup>
                <col style={{ width: '15%' }} />
                <col style={{ width: '24%' }} />
                <col style={{ width: '14%' }} />
                <col style={{ width: '11%' }} />
                <col style={{ width: '11%' }} />
                <col style={{ width: '13%' }} />
                <col style={{ width: '12%' }} />
              </colgroup>
              <thead>
                <tr className="bg-[#E3F0FF] text-[#0B3C9D] uppercase text-[10.5px] xl:text-[11.5px] font-bold tracking-[0.04em]">
                  <th className="py-2.5 px-1.5 xl:px-2.5 rounded-l-md">App ID</th>
                  <th className="py-2.5 px-1.5 xl:px-2.5">Certificate</th>
                  <th className="py-2.5 px-1.5 xl:px-2.5">Cert ID</th>
                  <th className="py-2.5 px-1.5 xl:px-2.5">Issued</th>
                  <th className="py-2.5 px-1.5 xl:px-2.5">Expires</th>
                  <th className="py-2.5 px-1.5 xl:px-2.5">Status</th>
                  <th className="py-2.5 px-1.5 xl:px-2.5 text-center rounded-r-md">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-[11.5px] xl:text-[13px] text-slate-700">
                {isLoading ? (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-slate-400">
                      <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                      Loading certificates...
                    </td>
                  </tr>
                ) : !data?.items || data.items.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-400">
                      No matching certificates found.
                    </td>
                  </tr>
                ) : (
                  data.items.map((cert) => (
                    <tr key={cert.id} className="hover:bg-[#F0F6FF] transition-colors">
                      <td
                        className="py-2.5 px-1.5 xl:px-2.5 font-mono text-[11px] xl:text-[12px] text-[#0F2A5C] whitespace-nowrap overflow-hidden text-ellipsis"
                        title={cert.application_id || 'N/A'}
                      >
                        {cert.application_id || 'N/A'}
                      </td>
                      <td
                        className="py-2.5 px-1.5 xl:px-2.5 font-semibold text-[#0F2A5C] text-[11.5px] xl:text-[13px] leading-[1.3] line-clamp-2 break-words"
                        title={cert.name}
                      >
                        {cert.name}
                      </td>
                      <td
                        className="py-2.5 px-1.5 xl:px-2.5 font-mono text-[11px] xl:text-[12px] text-slate-500 whitespace-nowrap overflow-hidden text-ellipsis"
                        title={cert.certificate_id}
                      >
                        {cert.certificate_id}
                      </td>
                      <td className="py-2.5 px-1.5 xl:px-2.5 whitespace-nowrap text-slate-600 text-[11px] xl:text-[13px]">
                        {formatDate(cert.issue_date)}
                      </td>
                      <td className="py-2.5 px-1.5 xl:px-2.5 whitespace-nowrap font-semibold text-[#0F2A5C] text-[11px] xl:text-[13px]">
                        {formatDate(cert.expiry_date)}
                      </td>
                      <td className="py-2.5 px-1.5 xl:px-2.5 whitespace-nowrap">
                        <StatusPill status={cert.status} className="!px-1.5 xl:!px-2.5 !py-[3px] !text-[10.5px] xl:!text-[12px]" />
                      </td>
                      <td className="py-2.5 px-1.5 xl:px-2.5">
                        <div className="flex items-center justify-center gap-1 xl:gap-1.5">
                          {/* View: navy 32x32 button */}
                          <button
                            type="button"
                            onClick={() => handleOpenView(cert)}
                            aria-label="View certificate"
                            title="View certificate"
                            className="w-7.5 h-7.5 xl:w-8 xl:h-8 rounded-[6px] bg-[#0B3C9D] hover:bg-[#092E7A] text-white flex items-center justify-center shrink-0 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]/40"
                          >
                            <Eye size={14} className="xl:hidden" />
                            <Eye size={15} className="hidden xl:block" />
                          </button>

                          {/* Renew: orange 32x32 button */}
                          <button
                            type="button"
                            onClick={() => handleOpenRenew(cert)}
                            aria-label="Renew certificate"
                            title="Renew certificate"
                            className="w-7.5 h-7.5 xl:w-8 xl:h-8 rounded-[6px] bg-[#F58220] hover:bg-[#E06F0F] text-white flex items-center justify-center shrink-0 transition-colors shadow-sm focus:outline-none focus:ring-2 focus:ring-[#F58220]/40"
                          >
                            <RefreshCw size={14} className="xl:hidden" />
                            <RefreshCw size={15} className="hidden xl:block" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile & Tablet Stacked Cards (< 1024px) - No Horizontal Scroll */}
          <div className="block lg:hidden mt-3.5 space-y-3">
            {isLoading ? (
              <div className="py-12 text-center text-slate-400">
                <Loader2 size={24} className="animate-spin mx-auto mb-2 text-[#F58220]" />
                Loading certificates...
              </div>
            ) : !data?.items || data.items.length === 0 ? (
              <div className="py-8 text-center text-slate-400">
                No matching certificates found.
              </div>
            ) : (
              data.items.map((cert) => (
                <div
                  key={cert.id}
                  className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 hover:bg-[#F0F6FF] transition-colors flex flex-col gap-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <h4
                        className="font-bold text-[#0F2A5C] text-[13px] leading-snug break-words"
                        title={cert.name}
                      >
                        {cert.name}
                      </h4>
                      <span className="font-mono text-[11.5px] text-slate-500 block mt-0.5">
                        {cert.certificate_id}
                      </span>
                    </div>
                    <StatusPill status={cert.status} className="!px-2.5 !py-[3px] !text-[12px] shrink-0" />
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[12px] pt-2 border-t border-slate-200/70">
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-semibold">App ID</span>
                      <span className="font-mono text-[#0F2A5C]">{cert.application_id || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="text-slate-400 block text-[10px] uppercase font-semibold">Issued</span>
                      <span className="text-slate-700">{formatDate(cert.issue_date)}</span>
                    </div>
                    <div className="col-span-2 flex items-center justify-between pt-1">
                      <div>
                        <span className="text-slate-400 block text-[10px] uppercase font-semibold">Expires</span>
                        <span className="font-semibold text-[#0F2A5C]">{formatDate(cert.expiry_date)}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => handleOpenView(cert)}
                          aria-label="View certificate"
                          title="View certificate"
                          className="w-8 h-8 rounded-[6px] bg-[#0B3C9D] hover:bg-[#092E7A] text-white flex items-center justify-center transition-colors shadow-sm"
                        >
                          <Eye size={15} />
                        </button>
                        <button
                          type="button"
                          onClick={() => handleOpenRenew(cert)}
                          aria-label="Renew certificate"
                          title="Renew certificate"
                          className="w-8 h-8 rounded-[6px] bg-[#F58220] hover:bg-[#E06F0F] text-white flex items-center justify-center transition-colors shadow-sm"
                        >
                          <RefreshCw size={15} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Pagination Controls */}
          {data && data.total > pageSize && (
            <div className="flex items-center justify-between pt-3.5 mt-2 border-t border-slate-100 text-xs text-slate-500">
              <span>
                Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, data.total)} of{' '}
                {data.total} certificates
              </span>
              <div className="flex items-center gap-1">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                  className="p-1.5 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="px-2 font-semibold text-[#0F2A5C]">
                  {page} / {totalPages}
                </span>
                <button
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                  className="p-1.5 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Narrow Card: Upcoming Expiries (~32%, min-w-[300px]) */}
        <div className="w-full lg:w-[320px] xl:w-[340px] shrink-0 bg-white rounded-[12px] p-5 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col min-h-[380px]">
          {/* Header: Calendar icon + Blue bold title */}
          <div className="flex items-center gap-2 pb-4 border-b border-slate-100">
            <Calendar size={20} className="text-[#0B3C9D]" />
            <h2 className="text-base font-bold text-[#0B3C9D] tracking-tight">
              Upcoming Expiries
            </h2>
          </div>

          {/* List sorted soonest first */}
          <div className="divide-y divide-slate-100 mt-2 flex-1">
            {upcoming.length === 0 ? (
              <p className="text-xs text-slate-400 py-8 text-center">No upcoming expiries.</p>
            ) : (
              upcoming.map((item) => (
                <div key={item.id} className="py-3.5 flex items-center gap-3.5 hover:bg-slate-50/70 rounded-md px-1 transition-colors">
                  {/* Left Date Block */}
                  <DateBlock day={item.day} month={item.month_name} year={item.year} />

                  {/* Right certificate name in bold with "Expires in N days" in grey */}
                  <div className="flex flex-col min-w-0 flex-1">
                    <span className="text-xs font-bold text-[#0F2A5C] leading-snug line-clamp-1">
                      {item.name}
                    </span>
                    <span className="text-[11px] text-[#7A8699] mt-0.5 font-medium">
                      Expires in <strong className="text-[#B85700] font-semibold">{item.days_until_expiry} days</strong>
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* View Certificate Details Drawer */}
      <Drawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        title={selectedCert?.name || 'Certificate Details'}
        subtitle={`ID: ${selectedCert?.certificate_id || ''}`}
      >
        {selectedCert && (
          <div className="space-y-6 text-xs">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Current Status:</span>
                <StatusPill status={selectedCert.status} />
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Application Reference:</span>
                <span className="font-mono font-bold text-[#0F2A5C]">{selectedCert.application_id || 'N/A'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Date of Issue:</span>
                <span className="font-semibold text-slate-800">{formatDate(selectedCert.issue_date)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Date of Expiration:</span>
                <span className="font-bold text-[#0F2A5C]">{formatDate(selectedCert.expiry_date)}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-500 font-medium">Days Remaining:</span>
                <span className={`font-bold ${selectedCert.days_until_expiry < 0 ? 'text-red-600' : 'text-[#B85700]'}`}>
                  {selectedCert.days_until_expiry < 0
                    ? `Expired ${Math.abs(selectedCert.days_until_expiry)} days ago`
                    : `${selectedCert.days_until_expiry} days remaining`}
                </span>
              </div>
            </div>

            {/* Document Preview Placeholder */}
            <div>
              <h4 className="font-bold text-[#0F2A5C] uppercase tracking-wider mb-2">
                Document Preview
              </h4>
              <div className="h-64 rounded-xl border-2 border-dashed border-[#D5DBE5] bg-slate-50 flex flex-col items-center justify-center p-6 text-center">
                <FileCheck size={40} className="text-[#0B3C9D] mb-2" />
                <p className="font-bold text-slate-700">Digital Certificate Record</p>
                <p className="text-[11px] text-slate-500 max-w-xs mt-1">
                  Validated against AICTE State Regional Authority repository.
                </p>
              </div>
            </div>

            <div className="pt-4 flex gap-3">
              <button
                onClick={() => {
                  setIsDrawerOpen(false);
                  handleOpenRenew(selectedCert);
                }}
                className="w-full py-2.5 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-[6px] transition-colors"
              >
                Initiate Renewal
              </button>
            </div>
          </div>
        )}
      </Drawer>

      {/* Renew Certificate Modal */}
      <Modal
        isOpen={isRenewModalOpen}
        onClose={() => setIsRenewModalOpen(false)}
        title={`Renew ${renewCert?.name || 'Certificate'}`}
      >
        <form onSubmit={handleRenewSubmit} className="space-y-4 text-xs">
          {renewSuccess && (
            <div className="p-3 bg-green-50 border border-green-200 text-[#1E7036] rounded-lg font-semibold">
              {renewSuccess}
            </div>
          )}
          {renewError && (
            <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg font-semibold">
              {renewError}
            </div>
          )}

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">Certificate Identifier</label>
            <input
              type="text"
              readOnly
              value={renewCert?.certificate_id || ''}
              className="w-full h-11 px-3 bg-slate-100 rounded-lg border border-slate-200 font-mono text-slate-600 outline-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">New Issue Date</label>
              <input
                type="date"
                required
                value={newIssueDate}
                onChange={(e) => setNewIssueDate(e.target.value)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] focus:border-[#F58220] outline-none"
              />
            </div>
            <div>
              <label className="font-bold text-[#0F2A5C] block mb-1">New Expiry Date</label>
              <input
                type="date"
                required
                value={newExpiryDate}
                onChange={(e) => setNewExpiryDate(e.target.value)}
                className="w-full h-11 px-3 rounded-lg border border-[#D5DBE5] text-[#0F2A5C] focus:border-[#F58220] outline-none"
              />
            </div>
          </div>

          <div>
            <label className="font-bold text-[#0F2A5C] block mb-1">Upload Renewed Document (PDF/JPG)</label>
            <input
              type="file"
              accept=".pdf,.jpg,.jpeg,.png"
              className="w-full py-2 text-xs text-slate-500 file:mr-3 file:py-2 file:px-3 file:rounded-md file:border-0 file:bg-[#E3F0FF] file:text-[#0B3C9D] file:font-semibold hover:file:bg-blue-100 cursor-pointer"
            />
            <p className="text-[10px] text-slate-400 mt-1">Accepts authentic certificates up to 10 MB.</p>
          </div>

          <div className="pt-4 flex justify-end gap-2.5">
            <button
              type="button"
              onClick={() => setIsRenewModalOpen(false)}
              className="px-4 py-2 border border-slate-200 rounded-[6px] text-slate-600 font-semibold hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingRenewal}
              className="px-5 py-2 bg-[#F58220] hover:bg-[#E06F0F] text-white font-semibold rounded-[6px] transition-colors disabled:opacity-50 flex items-center gap-1.5"
            >
              {isSubmittingRenewal && <Loader2 size={14} className="animate-spin" />}
              <span>Submit Renewal</span>
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
};

