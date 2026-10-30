import React, { useState, useEffect } from 'react';
import {
  ListChecks,
  Plus,
  Edit,
  Trash2,
  ArrowUp,
  ArrowDown,
  RefreshCw,
  Info,
} from 'lucide-react';
import {
  adminApi,
  ApplicationCategoryOut,
  ChecklistItemOut,
  DocumentTypeOut,
  RuleSetOut,
} from '../../api/admin';
import { StatusPill } from '../../components/StatusPill';
import { Modal } from '../../components/Modal';

const INSTITUTE_TYPES = [
  'ALL',
  'ENGINEERING',
  'MANAGEMENT',
  'PHARMACY',
  'ARCHITECTURE',
  'APPLIED_ARTS',
  'POLYTECHNIC',
];

export const AdminChecklistsPage: React.FC = () => {
  const [categories, setCategories] = useState<ApplicationCategoryOut[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('EOA');
  const [checklistItems, setChecklistItems] = useState<ChecklistItemOut[]>([]);
  const [docTypes, setDocTypes] = useState<DocumentTypeOut[]>([]);
  const [ruleSets, setRuleSets] = useState<RuleSetOut[]>([]);
  const [instituteTypeFilter, setInstituteTypeFilter] = useState<string>('ALL');

  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    document_type_id: 0,
    institute_type: 'ALL',
    min_count: 1,
    is_mandatory: true,
    min_validity_days_remaining: 30,
    max_age_days: undefined as number | undefined,
    ruleset_id: undefined as number | undefined,
    help_text: '',
    display_order: 1,
  });

  const loadInitialData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [cats, dts, rss] = await Promise.all([
        adminApi.listCategories(),
        adminApi.listDocumentTypes({ is_active: true }),
        adminApi.listRuleSets(),
      ]);
      setCategories(cats);
      setDocTypes(dts);
      setRuleSets(rss);

      const activeCat = cats.length > 0 ? cats[0].code : 'EOA';
      setSelectedCategory(activeCat);
      await loadChecklist(activeCat);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to initialize checklists catalog.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadChecklist = async (catCode: string) => {
    setIsLoading(true);
    try {
      const items = await adminApi.getChecklist(catCode);
      setChecklistItems(items);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || `Failed to fetch checklist for ${catCode}.`);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  const handleSelectCategory = (catCode: string) => {
    setSelectedCategory(catCode);
    loadChecklist(catCode);
  };

  const filteredItems = checklistItems.filter(
    (item) => instituteTypeFilter === 'ALL' || item.institute_type === 'ALL' || item.institute_type === instituteTypeFilter
  );

  const openCreateModal = () => {
    setIsEditing(false);
    setSelectedItemId(null);
    setFormData({
      document_type_id: docTypes.length > 0 ? docTypes[0].id : 0,
      institute_type: 'ALL',
      min_count: 1,
      is_mandatory: true,
      min_validity_days_remaining: 30,
      max_age_days: undefined,
      ruleset_id: ruleSets.find((rs) => rs.status === 'ACTIVE')?.id,
      help_text: '',
      display_order: checklistItems.length + 1,
    });
    setIsModalOpen(true);
  };

  const openEditModal = (item: ChecklistItemOut) => {
    setIsEditing(true);
    setSelectedItemId(item.id);
    setFormData({
      document_type_id: item.document_type_id,
      institute_type: item.institute_type || 'ALL',
      min_count: item.min_count || 1,
      is_mandatory: item.is_mandatory,
      min_validity_days_remaining: item.min_validity_days_remaining || 30,
      max_age_days: item.max_age_days,
      ruleset_id: item.ruleset_id,
      help_text: item.help_text || '',
      display_order: item.display_order,
    });
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    if (!formData.document_type_id) {
      alert('Please select a valid document type.');
      return;
    }
    try {
      if (isEditing && selectedItemId) {
        await adminApi.updateChecklistItem(selectedCategory, selectedItemId, {
          document_type_id: formData.document_type_id,
          institute_type: formData.institute_type,
          min_count: Number(formData.min_count),
          is_mandatory: formData.is_mandatory,
          min_validity_days_remaining: Number(formData.min_validity_days_remaining),
          max_age_days: formData.max_age_days ? Number(formData.max_age_days) : undefined,
          ruleset_id: formData.ruleset_id,
          help_text: formData.help_text,
          display_order: formData.display_order,
        });
        setSuccessMsg('Checklist requirement updated successfully.');
      } else {
        await adminApi.addChecklistItem(selectedCategory, {
          document_type_id: formData.document_type_id,
          institute_type: formData.institute_type,
          min_count: Number(formData.min_count),
          is_mandatory: formData.is_mandatory,
          min_validity_days_remaining: Number(formData.min_validity_days_remaining),
          max_age_days: formData.max_age_days ? Number(formData.max_age_days) : undefined,
          ruleset_id: formData.ruleset_id,
          help_text: formData.help_text,
          display_order: formData.display_order,
        });
        setSuccessMsg('Checklist requirement added successfully.');
      }
      setIsModalOpen(false);
      loadChecklist(selectedCategory);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to save checklist item.');
    }
  };

  const handleDelete = async (itemId: number) => {
    if (!window.confirm('Are you sure you want to delete this checklist requirement?')) return;
    try {
      await adminApi.deleteChecklistItem(selectedCategory, itemId);
      setSuccessMsg('Checklist requirement deleted.');
      loadChecklist(selectedCategory);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to delete checklist item.');
    }
  };

  const handleMoveOrder = async (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= checklistItems.length) return;

    const newItems = [...checklistItems];
    const temp = newItems[index];
    newItems[index] = newItems[targetIndex];
    newItems[targetIndex] = temp;

    // renumber orders
    const reorderedPayload = newItems.map((item, idx) => ({
      item_id: item.id,
      display_order: idx + 1,
    }));

    setChecklistItems(newItems);
    try {
      await adminApi.reorderChecklist(selectedCategory, reorderedPayload);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to persist order.');
      loadChecklist(selectedCategory);
    }
  };

  const activeRuleSet = ruleSets.find((rs) => rs.status === 'ACTIVE' || rs.status === 'PUBLISHED');

  return (
    <div className="space-y-6">
      {/* Alert Notices */}
      {errorMsg && (
        <div className="p-4 bg-red-50 border border-red-200 text-[#C62828] rounded-xl flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)}>✕</button>
        </div>
      )}
      {successMsg && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 text-[#1E7036] rounded-xl flex items-center justify-between">
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)}>✕</button>
        </div>
      )}

      {/* Header Card */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center gap-2 bg-[#E3F0FF] text-[#0B3C9D] text-xs font-semibold px-2.5 py-1 rounded-md mb-2">
              <ListChecks size={14} />
              <span>Application Category • Mandatory Documents Checklist</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F2A5C] tracking-tight">
              Required Documents Checklists
            </h1>
            <p className="text-sm text-slate-500 mt-1 max-w-2xl">
              Configure required documents per application category and institute type. Changes apply to live applications after a RuleSet Publish.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={openCreateModal}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#0B3C9D] text-white text-sm font-bold hover:bg-[#0F2A5C] shadow-sm transition-all"
            >
              <Plus size={18} />
              <span>Add Document Requirement</span>
            </button>
            <button
              onClick={() => loadChecklist(selectedCategory)}
              className="p-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50"
            >
              <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Category Tabs */}
        <div className="mt-6 flex flex-wrap items-center gap-2 border-b border-slate-100 pb-4">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-400 mr-2">Category:</span>
          {categories.map((cat) => (
            <button
              key={cat.code}
              onClick={() => handleSelectCategory(cat.code)}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                selectedCategory === cat.code
                  ? 'bg-[#0B3C9D] text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {cat.name} ({cat.code})
            </button>
          ))}
        </div>

        {/* Filter and RuleSet notice */}
        <div className="mt-4 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-2">
            <span className="text-slate-500 font-semibold">Institute Discipline:</span>
            <select
              value={instituteTypeFilter}
              onChange={(e) => setInstituteTypeFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white font-medium text-slate-700"
            >
              {INSTITUTE_TYPES.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="inline-flex items-center gap-2 text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200">
            <Info size={14} className="text-[#0B3C9D]" />
            <span>
              Bound RuleSet: <strong>{activeRuleSet?.name || 'APH 2026-27'}</strong> ({activeRuleSet?.version_label || 'v1.0'})
            </span>
          </div>
        </div>
      </div>

      {/* Checklists Table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase text-xs tracking-wider">
              <tr>
                <th className="py-3.5 px-4 w-12 text-center">Order</th>
                <th className="py-3.5 px-4">Document Type</th>
                <th className="py-3.5 px-4">Requirement</th>
                <th className="py-3.5 px-4">Institute Type</th>
                <th className="py-3.5 px-4">Min Count</th>
                <th className="py-3.5 px-4">Validity Requirement</th>
                <th className="py-3.5 px-4">Guidance / Help Text</th>
                <th className="py-3.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredItems.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No required documents configured for category {selectedCategory}.
                  </td>
                </tr>
              ) : (
                filteredItems.map((item, idx) => (
                  <tr key={item.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-3.5 px-4 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <span className="font-mono font-bold text-slate-500 w-5">{idx + 1}</span>
                        <div className="flex flex-col">
                          <button
                            onClick={() => handleMoveOrder(idx, 'up')}
                            disabled={idx === 0}
                            className="text-slate-400 hover:text-slate-700 disabled:opacity-20"
                          >
                            <ArrowUp size={12} />
                          </button>
                          <button
                            onClick={() => handleMoveOrder(idx, 'down')}
                            disabled={idx === filteredItems.length - 1}
                            className="text-slate-400 hover:text-slate-700 disabled:opacity-20"
                          >
                            <ArrowDown size={12} />
                          </button>
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      <p className="font-bold text-[#0F2A5C]">{item.document_type?.name || 'Document'}</p>
                      <p className="text-xs font-mono text-[#0B3C9D]">{item.document_type?.code}</p>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <StatusPill status={item.is_mandatory ? 'MANDATORY' : 'OPTIONAL'} />
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-xs font-semibold text-slate-700">
                      <span className="px-2 py-0.5 rounded bg-slate-100 border border-slate-200">
                        {item.institute_type || 'ALL'}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-xs font-mono font-bold text-slate-700">
                      {item.min_count || 1} file(s)
                    </td>
                    <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-600">
                      Min {item.min_validity_days_remaining || 30} days validity
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-500 max-w-xs truncate">
                      {item.help_text || '—'}
                    </td>
                    <td className="py-3.5 px-4 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => openEditModal(item)}
                          className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-md"
                          title="Edit requirement"
                        >
                          <Edit size={15} />
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="p-1.5 text-red-600 hover:bg-red-50 rounded-md"
                          title="Delete requirement"
                        >
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ========================================================================= */}
      {/* ADD / EDIT CHECKLIST ITEM MODAL                                           */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={isEditing ? 'Edit Checklist Item' : `Add Required Document for ${selectedCategory}`}
        maxWidth="max-w-xl"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
              Document Type *
            </label>
            <select
              value={formData.document_type_id}
              onChange={(e) => setFormData({ ...formData, document_type_id: parseInt(e.target.value) || 0 })}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm font-semibold"
            >
              {docTypes.map((dt) => (
                <option key={dt.id} value={dt.id}>
                  {dt.code} — {dt.name}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Institute Discipline *
              </label>
              <select
                value={formData.institute_type}
                onChange={(e) => setFormData({ ...formData, institute_type: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
              >
                {INSTITUTE_TYPES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Minimum Upload Count *
              </label>
              <input
                type="number"
                min={1}
                value={formData.min_count}
                onChange={(e) => setFormData({ ...formData, min_count: parseInt(e.target.value) || 1 })}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Min Days Validity Required
              </label>
              <input
                type="number"
                value={formData.min_validity_days_remaining}
                onChange={(e) =>
                  setFormData({ ...formData, min_validity_days_remaining: parseInt(e.target.value) || 30 })
                }
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
                Assign to RuleSet (Optional)
              </label>
              <select
                value={formData.ruleset_id || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    ruleset_id: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
              >
                <option value="">Global Active RuleSet</option>
                {ruleSets.map((rs) => (
                  <option key={rs.id} value={rs.id}>
                    {rs.name} ({rs.version_label})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.is_mandatory}
                onChange={(e) => setFormData({ ...formData, is_mandatory: e.target.checked })}
                className="rounded text-[#0B3C9D] focus:ring-[#0B3C9D]"
              />
              <span className="text-xs font-bold text-slate-700">
                Mandatory for Application Submission (Blocker)
              </span>
            </label>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase mb-1">
              Help Text & Submission Guidance
            </label>
            <textarea
              rows={2}
              value={formData.help_text}
              onChange={(e) => setFormData({ ...formData, help_text: e.target.value })}
              className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm"
              placeholder="Guidance shown to institute officials on the upload screen..."
            />
          </div>

          {/* Modal Footer */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-100"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-5 py-2 rounded-xl text-sm font-bold bg-[#0B3C9D] text-white hover:bg-[#0F2A5C] shadow-sm"
            >
              {isEditing ? 'Save Changes' : 'Add to Checklist'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};
