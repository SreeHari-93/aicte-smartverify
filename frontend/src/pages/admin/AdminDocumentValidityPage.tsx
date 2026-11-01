import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import ReactDOM from 'react-dom';
import {
  Search,
  Clock,
  CheckCircle2,
  Building2,
  RefreshCw,
  Loader2,
  MoreHorizontal,
  FileText,
  History,
  Edit3,
  ShieldCheck,
} from 'lucide-react';
import { validityApi, ValidityRecordItem } from '../../api/stage3';
import { Modal } from '../../components/Modal';

function formatDate(dateStr?: string | null): string {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return String(dateStr);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}-${month}-${year}`;
}

function formatDaysLeft(days?: number | null): { text: string; color: string } {
  if (days === undefined || days === null) {
    return { text: '—', color: 'text-slate-600' };
  }
  if (days < 0) {
    const absDays = Math.abs(days);
    return {
      text: `Expired ${absDays} day${absDays === 1 ? '' : 's'} ago`,
      color: 'text-red-600 font-medium',
    };
  }
  if (days === 0) {
    return {
      text: 'Expires today',
      color: 'text-amber-600 font-medium',
    };
  }
  if (days <= 30) {
    return {
      text: `${days} day${days === 1 ? '' : 's'} left`,
      color: 'text-amber-600 font-medium',
    };
  }
  return {
    text: `${days} days left`,
    color: 'text-slate-600',
  };
}

interface ActiveMenuState {
  record: ValidityRecordItem;
  buttonRect: DOMRect;
  openUpward: boolean;
}

export const AdminDocumentValidityPage: React.FC = () => {
  const [records, setRecords] = useState<ValidityRecordItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter] = useState('ALL');
  const [leaseOnly, setLeaseOnly] = useState(false);

  // Portal menu state
  const [activeMenu, setActiveMenu] = useState<ActiveMenuState | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Renewal Decision Modal State
  const [selectedRecord, setSelectedRecord] = useState<ValidityRecordItem | null>(null);
  const [isDecisionModalOpen, setIsDecisionModalOpen] = useState(false);
  const [decisionAction, setDecisionAction] = useState<'ACCEPT' | 'REJECT'>('ACCEPT');
  const [decisionReason, setDecisionReason] = useState('');
  const [newExpiryDate, setNewExpiryDate] = useState('');
  const [isSubmittingDecision, setIsSubmittingDecision] = useState(false);

  // Edit Lease Modal State
  const [editingLeaseRecord, setEditingLeaseRecord] = useState<ValidityRecordItem | null>(null);
  const [isLeaseModalOpen, setIsLeaseModalOpen] = useState(false);
  const [lessor, setLessor] = useState('');
  const [lessee, setLessee] = useState('');
  const [leaseStart, setLeaseStart] = useState('');
  const [leaseEnd, setLeaseEnd] = useState('');
  const [propertyAddress, setPropertyAddress] = useState('');
  const [isSavingLease, setIsSavingLease] = useState(false);

  // View Document Modal State
  const [viewRecord, setViewRecord] = useState<ValidityRecordItem | null>(null);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);

  // History Modal State
  const [historyRecord, setHistoryRecord] = useState<ValidityRecordItem | null>(null);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const [highlightedId, setHighlightedId] = useState<number | null>(null);
  const [unavailableNotice, setUnavailableNotice] = useState<string | null>(null);
  const handledParamRef = useRef<string | null>(null);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const data = await validityApi.list({
        status: statusFilter !== 'ALL' ? statusFilter : undefined,
        document_type: typeFilter !== 'ALL' ? typeFilter : undefined,
        is_lease: leaseOnly ? true : undefined,
      });
      setRecords(data);
    } catch (err) {
      console.error('Failed to load validity records:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter, typeFilter, leaseOnly]);

  // Handle open query param once on load
  useEffect(() => {
    const targetCode = searchParams.get('open') || searchParams.get('application');
    if (!targetCode || isLoading) return;
    if (handledParamRef.current === targetCode) return;
    handledParamRef.current = targetCode;

    if (statusFilter !== 'ALL') setStatusFilter('ALL');
    if (leaseOnly) setLeaseOnly(false);
    if (search) setSearch('');

    const targetLower = targetCode.toLowerCase();
    const match = records.find(
      (r) =>
        String(r.id) === targetCode ||
        (r.certificate_number && r.certificate_number.toLowerCase() === targetLower) ||
        (r.document_type_code && r.document_type_code.toLowerCase() === targetLower)
    );

    if (match) {
      setHighlightedId(match.id);
      if (match.status === 'RENEWAL_SUBMITTED') {
        handleOpenDecision(match);
      } else {
        setViewRecord(match);
        setIsViewModalOpen(true);
      }
      setTimeout(() => {
        const el = document.getElementById(`validity-row-${match.id}`);
        el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }, 150);
      setTimeout(() => setHighlightedId(null), 3000);
    } else {
      setUnavailableNotice('This case is no longer available.');
      setTimeout(() => setUnavailableNotice(null), 5000);
    }

    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete('open');
    nextParams.delete('application');
    setSearchParams(nextParams, { replace: true });
  }, [searchParams, records, isLoading, statusFilter, typeFilter, leaseOnly, search]);

  // Close portal menu on click outside, escape, scroll, resize
  useEffect(() => {
    if (!activeMenu) return;

    const handleOutsideClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActiveMenu(null);
      }
    };

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveMenu(null);
      }
    };

    const handleScrollOrResize = () => {
      setActiveMenu(null);
    };

    window.addEventListener('mousedown', handleOutsideClick);
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('scroll', handleScrollOrResize, true);
    window.addEventListener('resize', handleScrollOrResize);

    return () => {
      window.removeEventListener('mousedown', handleOutsideClick);
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('scroll', handleScrollOrResize, true);
      window.removeEventListener('resize', handleScrollOrResize);
    };
  }, [activeMenu]);

  // Adjust upward position when menu is rendered
  useEffect(() => {
    if (activeMenu && menuRef.current && activeMenu.openUpward) {
      const actualHeight = menuRef.current.offsetHeight;
      menuRef.current.style.top = `${activeMenu.buttonRect.top - actualHeight - 4}px`;
    }
  }, [activeMenu]);

  // Shift + mouse wheel support
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (e.shiftKey && scrollContainerRef.current) {
      scrollContainerRef.current.scrollLeft += e.deltaY;
    }
  };

  const handleToggleMenu = (e: React.MouseEvent, record: ValidityRecordItem) => {
    e.stopPropagation();
    if (activeMenu && activeMenu.record.id === record.id) {
      setActiveMenu(null);
      return;
    }
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const spaceBelow = window.innerHeight - rect.bottom;
    const estimatedHeight = 160;
    const openUpward = spaceBelow < estimatedHeight && rect.top > estimatedHeight;

    setActiveMenu({
      record,
      buttonRect: rect,
      openUpward,
    });
  };

  const handleOpenDecision = (r: ValidityRecordItem) => {
    setSelectedRecord(r);
    setDecisionAction('ACCEPT');
    setDecisionReason('');
    const propDate = new Date();
    propDate.setFullYear(propDate.getFullYear() + 1);
    setNewExpiryDate(propDate.toISOString().slice(0, 10));
    setIsDecisionModalOpen(true);
  };

  const handleDecisionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedRecord) return;
    if (!decisionReason.trim()) {
      alert('Reason is required.');
      return;
    }

    setIsSubmittingDecision(true);
    try {
      await validityApi.decideRenewal(selectedRecord.id, {
        action: decisionAction,
        reason: decisionReason.trim(),
        new_expiry_date: decisionAction === 'ACCEPT' && newExpiryDate ? newExpiryDate : undefined,
      });
      setIsDecisionModalOpen(false);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to record decision');
    } finally {
      setIsSubmittingDecision(false);
    }
  };

  const handleOpenLease = (r: ValidityRecordItem) => {
    setEditingLeaseRecord(r);
    setLessor(r.lessor || '');
    setLessee(r.lessee || r.institute_name || '');
    setLeaseStart(r.lease_start ? r.lease_start.slice(0, 10) : '');
    setLeaseEnd(r.lease_end ? r.lease_end.slice(0, 10) : (r.expiry_date ? r.expiry_date.slice(0, 10) : ''));
    setPropertyAddress(r.property_address || '');
    setIsLeaseModalOpen(true);
  };

  const handleLeaseSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingLeaseRecord) return;

    setIsSavingLease(true);
    try {
      await validityApi.updateLease(editingLeaseRecord.id, {
        lessor: lessor.trim(),
        lessee: lessee.trim(),
        lease_start: leaseStart || undefined,
        lease_end: leaseEnd || undefined,
        property_address: propertyAddress.trim(),
      });
      setIsLeaseModalOpen(false);
      loadData();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update lease');
    } finally {
      setIsSavingLease(false);
    }
  };

  const handleViewDocument = (r: ValidityRecordItem) => {
    const docId = r.renewal_document_id || r.document_id;
    if (docId) {
      window.open(`/api/documents/${docId}/download`, '_blank');
    } else {
      setViewRecord(r);
      setIsViewModalOpen(true);
    }
  };

  const handleViewHistory = (r: ValidityRecordItem) => {
    setHistoryRecord(r);
    setIsHistoryModalOpen(true);
  };

  const filtered = records.filter((r) => {
    if (!search) return true;
    const s = search.toLowerCase();
    return (
      (r.document_name || '').toLowerCase().includes(s) ||
      (r.certificate_number || '').toLowerCase().includes(s) ||
      (r.institute_name || '').toLowerCase().includes(s) ||
      (r.document_type_code || '').toLowerCase().includes(s)
    );
  });

  const renderStatusPill = (status: string) => {
    let label = status;
    let styleClasses = 'bg-slate-100 text-slate-700 border-slate-200';

    switch (status) {
      case 'VALID':
        label = 'Valid';
        styleClasses = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        break;
      case 'EXPIRING_SOON':
        label = 'Expiring soon';
        styleClasses = 'bg-amber-50 text-amber-700 border-amber-200';
        break;
      case 'EXPIRED':
        label = 'Expired';
        styleClasses = 'bg-red-50 text-red-700 border-red-200';
        break;
      case 'RENEWAL_SUBMITTED':
        label = 'Renewal submitted';
        styleClasses = 'bg-blue-50 text-blue-700 border-blue-200';
        break;
      case 'RENEWED':
        label = 'Renewed';
        styleClasses = 'bg-teal-50 text-teal-700 border-teal-200';
        break;
    }

    return (
      <span
        className={`w-[130px] h-7 inline-flex items-center justify-center text-xs font-semibold rounded-full border whitespace-nowrap shrink-0 ${styleClasses}`}
      >
        {label}
      </span>
    );
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Scoped CSS for slim horizontal scrollbar */}
      <style>{`
        .validity-scroll-container {
          -webkit-overflow-scrolling: touch;
        }
        .validity-scroll-container::-webkit-scrollbar {
          height: 8px;
          width: 8px;
        }
        .validity-scroll-container::-webkit-scrollbar-track {
          background: #f1f5f9;
          border-radius: 9999px;
        }
        .validity-scroll-container::-webkit-scrollbar-thumb {
          background: #94a3b8;
          border-radius: 9999px;
        }
        .validity-scroll-container::-webkit-scrollbar-thumb:hover {
          background: #64748b;
        }
      `}</style>

      {/* Page Header Card */}
      <div className="bg-white rounded-lg p-5 border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Document validity
          </h1>
          <p className="text-xs text-slate-600 mt-0.5">
            Track expiration and renewal of certificates.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={isLoading}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-white border border-slate-300 hover:border-slate-400 text-slate-800 text-xs font-medium rounded-md shadow-sm transition-colors"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {unavailableNotice && (
        <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 text-xs font-semibold rounded-lg flex items-center justify-between">
          <span>{unavailableNotice}</span>
          <button onClick={() => setUnavailableNotice(null)} className="text-amber-700 hover:text-amber-900 font-bold ml-2">×</button>
        </div>
      )}
      {/* Main Table Card */}
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm overflow-hidden">
        {/* Filters */}
        <div className="p-4 border-b border-slate-200 flex flex-wrap items-center justify-between gap-3 bg-slate-50">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Status:</span>
            {[
              { id: 'ALL', label: 'All' },
              { id: 'VALID', label: 'Valid' },
              { id: 'EXPIRING_SOON', label: 'Expiring soon' },
              { id: 'EXPIRED', label: 'Expired' },
              { id: 'RENEWAL_SUBMITTED', label: 'Renewal submitted' },
              { id: 'RENEWED', label: 'Renewed' },
            ].map((st) => (
              <button
                key={st.id}
                onClick={() => setStatusFilter(st.id)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  statusFilter === st.id
                    ? 'bg-[#0B3C9D] text-white'
                    : 'bg-white text-slate-600 hover:bg-slate-100 border border-slate-200'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setLeaseOnly(!leaseOnly)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                leaseOnly
                  ? 'bg-amber-100 text-amber-900 border-amber-300'
                  : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
              }`}
            >
              Lease deeds only
            </button>

            <div className="relative w-56">
              <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Search document or institute..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"
              />
            </div>
          </div>
        </div>

        {/* Scrollable Table Container */}
        {isLoading ? (
          <div className="py-16 text-center text-slate-600 flex flex-col items-center justify-center gap-2">
            <Loader2 size={24} className="animate-spin text-[#0B3C9D]" />
            <span className="text-xs">Loading document validity records...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center text-slate-600 flex flex-col items-center justify-center gap-2">
            <p className="text-sm font-medium text-slate-700">No documents match these filters</p>
            {(statusFilter !== 'ALL' || search || leaseOnly) && (
              <button
                onClick={() => {
                  setStatusFilter('ALL');
                  setSearch('');
                  setLeaseOnly(false);
                }}
                className="text-xs text-[#0B3C9D] hover:underline font-medium"
              >
                Clear filters
              </button>
            )}
          </div>
        ) : (
          <div
            ref={scrollContainerRef}
            onWheel={handleWheel}
            className="validity-scroll-container overflow-x-auto overflow-y-auto"
            style={{
              maxHeight: '60vh',
              scrollBehavior: 'smooth',
              scrollbarWidth: 'thin',
              scrollbarColor: '#94a3b8 #f1f5f9',
            }}
          >
            <table
              className="text-sm border-separate border-spacing-0"
              style={{
                minWidth: '1180px',
                width: '100%',
                tableLayout: 'fixed',
              }}
            >
              <colgroup>
                <col style={{ width: '20%' }} />
                <col style={{ width: '20%' }} />
                <col style={{ width: '14%' }} />
                <col style={{ width: '13%' }} />
                <col style={{ width: '13%' }} />
                <col style={{ width: '20%' }} />
              </colgroup>
              <thead>
                <tr className="h-11">
                  {/* Sticky Left: Document */}
                  <th
                    className="px-4 py-3 text-left text-xs font-semibold text-slate-700 bg-slate-50 border-b border-slate-200"
                    style={{
                      position: 'sticky',
                      left: 0,
                      top: 0,
                      zIndex: 30,
                      boxShadow: '2px 0 5px -2px rgba(0, 0, 0, 0.08)',
                    }}
                  >
                    Document
                  </th>

                  <th
                    className="px-4 py-3 text-left text-xs font-semibold text-slate-700 bg-slate-50 border-b border-slate-200"
                    style={{
                      position: 'sticky',
                      top: 0,
                      zIndex: 20,
                    }}
                  >
                    Institution and region
                  </th>

                  <th
                    className="px-4 py-3 text-left text-xs font-semibold text-slate-700 bg-slate-50 border-b border-slate-200"
                    style={{
                      position: 'sticky',
                      top: 0,
                      zIndex: 20,
                    }}
                  >
                    Issuing authority
                  </th>

                  <th
                    className="px-4 py-3 text-left text-xs font-semibold text-slate-700 bg-slate-50 border-b border-slate-200"
                    style={{
                      position: 'sticky',
                      top: 0,
                      zIndex: 20,
                    }}
                  >
                    Expiry and days left
                  </th>

                  <th
                    className="px-4 py-3 text-left text-xs font-semibold text-slate-700 bg-slate-50 border-b border-slate-200"
                    style={{
                      position: 'sticky',
                      top: 0,
                      zIndex: 20,
                    }}
                  >
                    Status
                  </th>

                  {/* Sticky Right: Actions */}
                  <th
                    className="px-4 py-3 text-right text-xs font-semibold text-slate-700 bg-slate-50 border-b border-slate-200"
                    style={{
                      position: 'sticky',
                      right: 0,
                      top: 0,
                      zIndex: 30,
                      boxShadow: '-2px 0 5px -2px rgba(0, 0, 0, 0.08)',
                    }}
                  >
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {filtered.map((r) => {
                  const daysInfo = formatDaysLeft(r.days_left);
                  const isRenewal = r.status === 'RENEWAL_SUBMITTED';

                  return (
                    <tr
                      key={r.id}
                      id={`validity-row-${r.id}`}
                      className={`group hover:bg-slate-50 transition-colors h-16 ${r.id === highlightedId ? 'bg-amber-100/70' : ''}`}
                    >
                      {/* Sticky Left Cell: Document */}
                      <td
                        className="px-4 py-3 align-middle bg-white group-hover:bg-slate-50 border-b border-slate-100 transition-colors"
                        style={{
                          position: 'sticky',
                          left: 0,
                          zIndex: 10,
                          boxShadow: '2px 0 5px -2px rgba(0, 0, 0, 0.08)',
                        }}
                      >
                        <div
                          className="font-semibold text-slate-900 truncate text-xs"
                          title={r.document_name}
                        >
                          {r.document_name}
                        </div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span
                            className="font-mono text-[11px] font-bold text-[#0B3C9D] truncate"
                            title={r.certificate_number || r.document_type_code}
                          >
                            {r.certificate_number || r.document_type_code}
                          </span>
                          {r.is_lease && (
                            <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-200 shrink-0">
                              Lease
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Institution and region */}
                      <td className="px-4 py-3 align-middle border-b border-slate-100">
                        <div
                          className="font-semibold text-slate-900 truncate text-xs"
                          title={r.institute_name}
                        >
                          {r.institute_name}
                        </div>
                        <div className="text-[11px] text-slate-600 flex items-center gap-1 mt-0.5 truncate">
                          <Building2 size={11} className="text-slate-500 shrink-0" />
                          <span className="truncate" title={r.institute_state || 'AICTE Region'}>
                            {r.institute_state || 'AICTE Region'}
                          </span>
                        </div>
                      </td>

                      {/* Issuing authority */}
                      <td className="px-4 py-3 align-middle border-b border-slate-100">
                        <span
                          className="text-slate-700 text-xs truncate block"
                          title={r.issuing_authority || 'Competent Authority'}
                        >
                          {r.issuing_authority || 'Competent Authority'}
                        </span>
                      </td>

                      {/* Expiry and days left */}
                      <td className="px-4 py-3 align-middle border-b border-slate-100">
                        <div className="text-xs">
                          <div className="font-semibold text-slate-900">
                            {formatDate(r.expiry_date)}
                          </div>
                          <div className={`text-[11px] mt-0.5 flex items-center gap-1 ${daysInfo.color}`}>
                            {r.days_left !== undefined && r.days_left !== null && r.days_left <= 30 && (
                              <Clock size={11} className="shrink-0" />
                            )}
                            <span className="truncate">{daysInfo.text}</span>
                          </div>
                        </div>
                      </td>

                      {/* Status */}
                      <td className="px-4 py-3 align-middle border-b border-slate-100 text-left">
                        {renderStatusPill(r.status)}
                      </td>

                      {/* Sticky Right Cell: Actions */}
                      <td
                        className="px-4 py-3 align-middle text-right bg-white group-hover:bg-slate-50 border-b border-slate-100 transition-colors"
                        style={{
                          position: 'sticky',
                          right: 0,
                          zIndex: 10,
                          boxShadow: '-2px 0 5px -2px rgba(0, 0, 0, 0.08)',
                        }}
                      >
                        <div className="flex items-center justify-end gap-2 w-full whitespace-nowrap">
                          {isRenewal ? (
                            <button
                              type="button"
                              onClick={() => handleOpenDecision(r)}
                              className="w-[100px] h-9 shrink-0 inline-flex items-center justify-center px-3 text-xs font-semibold rounded-md bg-[#0B3C9D] text-white hover:bg-[#082B70] shadow-xs transition-colors"
                            >
                              Verify
                            </button>
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleOpenDecision(r)}
                              className="w-[100px] h-9 shrink-0 inline-flex items-center justify-center px-3 text-xs font-semibold rounded-md bg-[#0B3C9D] text-white hover:bg-[#082B70] shadow-xs transition-colors"
                            >
                              Decision
                            </button>
                          )}

                          <button
                            type="button"
                            title="More actions"
                            onClick={(e) => handleToggleMenu(e, r)}
                            className="w-9 h-9 shrink-0 inline-flex items-center justify-center rounded-md border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 hover:text-slate-900 shadow-xs transition-colors"
                          >
                            <MoreHorizontal size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Dropdown Menu Portal */}
      {activeMenu &&
        ReactDOM.createPortal(
          <div
            ref={menuRef}
            className="fixed z-[9999] bg-white rounded-md shadow-lg border border-slate-200 py-1 text-xs w-[190px] animate-in fade-in zoom-in-95 duration-100"
            style={{
              top: activeMenu.openUpward
                ? activeMenu.buttonRect.top - 160
                : activeMenu.buttonRect.bottom + 4,
              left: Math.max(10, activeMenu.buttonRect.right - 190),
            }}
          >
            {activeMenu.record.status === 'RENEWAL_SUBMITTED' && (
              <button
                type="button"
                onClick={() => {
                  const rec = activeMenu.record;
                  setActiveMenu(null);
                  handleOpenDecision(rec);
                }}
                className="w-full text-left px-3 py-2 min-h-[36px] text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 flex items-center gap-2 transition-colors"
              >
                <ShieldCheck size={14} className="text-[#0B3C9D] shrink-0" />
                <span>Verify renewal</span>
              </button>
            )}

            <button
              type="button"
              onClick={() => {
                const rec = activeMenu.record;
                setActiveMenu(null);
                handleViewDocument(rec);
              }}
              className="w-full text-left px-3 py-2 min-h-[36px] text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 flex items-center gap-2 transition-colors"
            >
              <FileText size={14} className="text-slate-600 shrink-0" />
              <span>View document</span>
            </button>

            <button
              type="button"
              onClick={() => {
                const rec = activeMenu.record;
                setActiveMenu(null);
                handleViewHistory(rec);
              }}
              className="w-full text-left px-3 py-2 min-h-[36px] text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 flex items-center gap-2 transition-colors"
            >
              <History size={14} className="text-slate-600 shrink-0" />
              <span>View history</span>
            </button>

            {activeMenu.record.is_lease && (
              <button
                type="button"
                onClick={() => {
                  const rec = activeMenu.record;
                  setActiveMenu(null);
                  handleOpenLease(rec);
                }}
                className="w-full text-left px-3 py-2 min-h-[36px] text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-100 flex items-center gap-2 transition-colors"
              >
                <Edit3 size={14} className="text-amber-600 shrink-0" />
                <span>Edit lease details</span>
              </button>
            )}
          </div>,
          document.body
        )}

      {/* Renewal Decision Modal */}
      <Modal
        isOpen={isDecisionModalOpen}
        onClose={() => setIsDecisionModalOpen(false)}
        title={`Renewal decision - ${selectedRecord?.document_name || ''}`}
      >
        <form onSubmit={handleDecisionSubmit} className="space-y-4">
          <div className="bg-slate-50 rounded-lg p-3 border border-slate-200 text-xs space-y-1.5">
            <div>
              <span className="font-medium text-slate-500">Institution:</span>{' '}
              <span className="font-medium text-slate-900">{selectedRecord?.institute_name}</span>
            </div>
            <div>
              <span className="font-medium text-slate-500">Document type:</span>{' '}
              <span>
                {selectedRecord?.document_name} ({selectedRecord?.document_type_code})
              </span>
            </div>
            <div>
              <span className="font-medium text-slate-500">Current expiry:</span>{' '}
              <span>{formatDate(selectedRecord?.expiry_date)}</span>
            </div>
            {selectedRecord?.renewal_document_id && (
              <div className="text-emerald-700 font-medium pt-1 border-t border-slate-200 flex items-center gap-1">
                <CheckCircle2 size={13} />
                <span>Renewal document uploaded</span>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Action <span className="text-red-500">*</span>
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setDecisionAction('ACCEPT')}
                className={`py-2 px-3 rounded-md text-xs font-medium border transition-colors ${
                  decisionAction === 'ACCEPT'
                    ? 'bg-emerald-600 text-white border-emerald-600 shadow-xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                }`}
              >
                Accept
              </button>
              <button
                type="button"
                onClick={() => setDecisionAction('REJECT')}
                className={`py-2 px-3 rounded-md text-xs font-medium border transition-colors ${
                  decisionAction === 'REJECT'
                    ? 'bg-red-600 text-white border-red-600 shadow-xs'
                    : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                }`}
              >
                Reject
              </button>
            </div>
          </div>

          {decisionAction === 'ACCEPT' && (
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                New expiry date <span className="text-red-500">*</span>
              </label>
              <input
                type="date"
                required
                value={newExpiryDate}
                onChange={(e) => setNewExpiryDate(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Reason <span className="text-red-500">*</span>
            </label>
            <textarea
              required
              rows={3}
              value={decisionReason}
              onChange={(e) => setDecisionReason(e.target.value)}
              placeholder="State the basis for accepting or rejecting this renewal..."
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsDecisionModalOpen(false)}
              className="px-3.5 py-1.5 border border-slate-300 text-slate-700 rounded-md text-xs font-medium hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmittingDecision}
              className="px-4 py-1.5 bg-[#0B3C9D] text-white rounded-md text-xs font-medium hover:bg-[#082B70] flex items-center gap-2"
            >
              {isSubmittingDecision && <Loader2 size={14} className="animate-spin" />}
              <span>Save decision</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Edit Lease Modal */}
      <Modal
        isOpen={isLeaseModalOpen}
        onClose={() => setIsLeaseModalOpen(false)}
        title={`Lease details - ${editingLeaseRecord?.document_name || ''}`}
      >
        <form onSubmit={handleLeaseSubmit} className="space-y-4">
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-md text-blue-900 text-xs">
            <p className="font-medium">Land lease guidelines</p>
            <p className="mt-0.5 text-slate-600">
              Technical campuses must hold minimum 30 years registered lease or clear freehold title without encumbrances.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Lessor (Land owner)
              </label>
              <input
                type="text"
                value={lessor}
                onChange={(e) => setLessor(e.target.value)}
                placeholder="e.g. State Land Development Corp / Trust"
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Lessee (Institution)
              </label>
              <input
                type="text"
                value={lessee}
                onChange={(e) => setLessee(e.target.value)}
                placeholder="e.g. Sri Krishna Educational Trust"
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Lease commencement date
              </label>
              <input
                type="date"
                value={leaseStart}
                onChange={(e) => setLeaseStart(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Lease expiry date
              </label>
              <input
                type="date"
                value={leaseEnd}
                onChange={(e) => setLeaseEnd(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Registered property address / survey plot
            </label>
            <textarea
              rows={3}
              value={propertyAddress}
              onChange={(e) => setPropertyAddress(e.target.value)}
              placeholder="Enter survey plot numbers and address..."
              className="w-full px-3 py-2 border border-slate-300 rounded-md text-xs focus:outline-none focus:border-[#0B3C9D]"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsLeaseModalOpen(false)}
              className="px-3.5 py-1.5 border border-slate-300 text-slate-700 rounded-md text-xs font-medium hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSavingLease}
              className="px-4 py-1.5 bg-[#0B3C9D] text-white rounded-md text-xs font-medium hover:bg-[#082B70] flex items-center gap-2"
            >
              {isSavingLease && <Loader2 size={14} className="animate-spin" />}
              <span>Save lease</span>
            </button>
          </div>
        </form>
      </Modal>

      {/* Document Preview Modal */}
      <Modal
        isOpen={isViewModalOpen}
        onClose={() => setIsViewModalOpen(false)}
        title={`Document details - ${viewRecord?.document_name || ''}`}
      >
        <div className="space-y-4 text-xs">
          <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-200 space-y-2">
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Document title</span>
              <span className="font-semibold text-slate-900">{viewRecord?.document_name}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Certificate / Registration</span>
              <span className="font-mono font-bold text-[#0B3C9D]">
                {viewRecord?.certificate_number || viewRecord?.document_type_code}
              </span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Issuing authority</span>
              <span className="text-slate-800">{viewRecord?.issuing_authority || 'Competent Authority'}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Issue date</span>
              <span className="text-slate-800">{formatDate(viewRecord?.issue_date)}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Expiry date</span>
              <span className="font-medium text-slate-900">{formatDate(viewRecord?.expiry_date)}</span>
            </div>
            <div className="flex justify-between items-center py-1">
              <span className="font-medium text-slate-500">Status</span>
              <div>{viewRecord && renderStatusPill(viewRecord.status)}</div>
            </div>
          </div>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsViewModalOpen(false)}
              className="px-4 py-1.5 bg-[#0B3C9D] text-white rounded-md text-xs font-medium hover:bg-[#082B70]"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>

      {/* Validity History Modal */}
      <Modal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        title={`Validity history - ${historyRecord?.document_name || ''}`}
      >
        <div className="space-y-4 text-xs">
          <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-200 space-y-2">
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Institution</span>
              <span className="font-semibold text-slate-900">{historyRecord?.institute_name}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Document</span>
              <span className="text-slate-800">{historyRecord?.document_name}</span>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Current status</span>
              <div>{historyRecord && renderStatusPill(historyRecord.status)}</div>
            </div>
            <div className="flex justify-between items-center py-1 border-b border-slate-200">
              <span className="font-medium text-slate-500">Registered expiry</span>
              <span className="font-medium text-slate-900">{formatDate(historyRecord?.expiry_date)}</span>
            </div>
            {historyRecord?.renewal_submitted_at && (
              <div className="flex justify-between items-center py-1 border-b border-slate-200">
                <span className="font-medium text-slate-500">Renewal submitted on</span>
                <span className="text-slate-800">{formatDate(historyRecord.renewal_submitted_at)}</span>
              </div>
            )}
            {historyRecord?.renewal_decision_reason && (
              <div className="py-1 border-b border-slate-200">
                <span className="font-medium text-slate-500 block mb-0.5">Last decision notes</span>
                <p className="text-slate-800 bg-white p-2 rounded border border-slate-200">
                  {historyRecord.renewal_decision_reason}
                </p>
              </div>
            )}
            <div className="flex justify-between items-center py-1">
              <span className="font-medium text-slate-500">Last updated</span>
              <span className="text-slate-600">{formatDate(historyRecord?.updated_at)}</span>
            </div>
          </div>

          <div className="flex justify-end pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setIsHistoryModalOpen(false)}
              className="px-4 py-1.5 bg-[#0B3C9D] text-white rounded-md text-xs font-medium hover:bg-[#082B70]"
            >
              Close
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
