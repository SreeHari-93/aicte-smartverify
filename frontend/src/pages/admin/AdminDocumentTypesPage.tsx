import React, { useState, useEffect } from 'react';
import {
  Files,
  Plus,
  Edit,
  Trash2,
  Search,
  Tag,
  Key,
  ShieldCheck,
  RefreshCw,
  X,
} from 'lucide-react';
import {
  adminApi,
  DocumentTypeOut,
} from '../../api/admin';
import { StatusPill } from '../../components/StatusPill';
import { Modal } from '../../components/Modal';

const AUTHORITY_ADAPTERS = [
  'MANUAL',
  'AICTE_PORTAL',
  'SWAYAM',
  'LAND_REGISTRY',
  'FIRE_AUTHORITY',
  'PWD',
  'MOCK_GOV',
  'API',
  'QR',
];

export const AdminDocumentTypesPage: React.FC = () => {
  const [docTypes, setDocTypes] = useState<DocumentTypeOut[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    issuing_authority: '',
    accepted_formats: ['PDF', 'JPG', 'PNG'],
    max_size_mb: 10,
    has_expiry: true,
    default_validity_months: 12,
    verification_method: 'MANUAL',
    authority_adapter: 'MANUAL',
    statutory_verification_applies: false,
    keywords: [] as string[],
    extraction_schema: [] as Array<{ key: string; label: string; type: string; required: boolean }>,
  });

  // Keyword input
  const [newKeyword, setNewKeyword] = useState('');
  // Schema field input
  const [newFieldKey, setNewFieldKey] = useState('');
  const [newFieldLabel, setNewFieldLabel] = useState('');
  const [newFieldType, setNewFieldType] = useState('text');
  const [newFieldRequired, setNewFieldRequired] = useState(true);

  const loadData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const data = await adminApi.listDocumentTypes();
      setDocTypes(data);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to fetch document types.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredDocTypes = docTypes.filter(
    (d) =>
      d.code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      d.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (d.issuing_authority || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const openCreateModal = () => {
    setIsEditing(false);
    setSelectedCode(null);
    setFormData({
      code: '',
      name: '',
      description: '',
      issuing_authority: '',
      accepted_formats: ['PDF', 'JPG', 'PNG'],
      max_size_mb: 10,
      has_expiry: true,
      default_validity_months: 12,
      verification_method: 'API',
      authority_adapter: 'FIRE_AUTHORITY',
      statutory_verification_applies: false,
      keywords: ['certificate', 'clearance'],
      extraction_schema: [
        { key: 'issue_date', label: 'Date of Issue', type: 'date', required: true },
        { key: 'expiry_date', label: 'Valid Till Date', type: 'date', required: true },
        { key: 'certificate_no', label: 'Certificate / NOC Number', type: 'id', required: true },
      ],
    });
    setNewKeyword('');
    setIsModalOpen(true);
  };

  const openEditModal = (dt: DocumentTypeOut) => {
    setIsEditing(true);
    setSelectedCode(dt.code);
    setFormData({
      code: dt.code,
      name: dt.name,
      description: dt.description || '',
      issuing_authority: dt.issuing_authority || '',
      accepted_formats: dt.accepted_formats || ['PDF'],
      max_size_mb: dt.max_size_mb || 10,
      has_expiry: dt.has_expiry || false,
      default_validity_months: dt.default_validity_months || 12,
      verification_method: dt.verification_method || 'MANUAL',
      authority_adapter: dt.authority_adapter || dt.verification_method || 'MANUAL',
      statutory_verification_applies: dt.statutory_verification_applies || false,
      keywords: dt.keywords || [],
      extraction_schema: (dt.extraction_schema as any) || [],
    });
    setNewKeyword('');
    setIsModalOpen(true);
  };

  const handleAddKeyword = () => {
    const val = newKeyword.trim().toLowerCase();
    if (val && !formData.keywords.includes(val)) {
      setFormData({ ...formData, keywords: [...formData.keywords, val] });
      setNewKeyword('');
    }
  };

  const handleRemoveKeyword = (kw: string) => {
    setFormData({ ...formData, keywords: formData.keywords.filter((k) => k !== kw) });
  };

  const handleAddField = () => {
    if (!newFieldKey.trim() || !newFieldLabel.trim()) return;
    const cleanKey = newFieldKey.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_');
    setFormData({
      ...formData,
      extraction_schema: [
        ...formData.extraction_schema,
        {
          key: cleanKey,
          label: newFieldLabel.trim(),
          type: newFieldType,
          required: newFieldRequired,
        },
      ],
    });
    setNewFieldKey('');
    setNewFieldLabel('');
    setNewFieldType('text');
    setNewFieldRequired(true);
  };

  const handleRemoveField = (index: number) => {
    setFormData({
      ...formData,
      extraction_schema: formData.extraction_schema.filter((_, i) => i !== index),
    });
  };

  const handleSave = async () => {
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      if (isEditing && selectedCode) {
        await adminApi.updateDocumentType(selectedCode, {
          name: formData.name,
          description: formData.description,
          issuing_authority: formData.issuing_authority,
          accepted_formats: formData.accepted_formats,
          max_size_mb: Number(formData.max_size_mb),
          has_expiry: formData.has_expiry,
          default_validity_months: Number(formData.default_validity_months),
          verification_method: formData.verification_method,
          authority_adapter: formData.authority_adapter,
          statutory_verification_applies: formData.statutory_verification_applies,
          keywords: formData.keywords,
          extraction_schema: formData.extraction_schema,
        });
        setSuccessMsg(`Document type '${selectedCode}' updated successfully.`);
      } else {
        await adminApi.createDocumentType({
          code: formData.code.trim().toUpperCase(),
          name: formData.name.trim(),
          description: formData.description,
          issuing_authority: formData.issuing_authority,
          accepted_formats: formData.accepted_formats,
          max_size_mb: Number(formData.max_size_mb),
          has_expiry: formData.has_expiry,
          default_validity_months: Number(formData.default_validity_months),
          verification_method: formData.verification_method,
          authority_adapter: formData.authority_adapter,
          statutory_verification_applies: formData.statutory_verification_applies,
          keywords: formData.keywords,
          extraction_schema: formData.extraction_schema,
        });
        setSuccessMsg(`Document type '${formData.code.toUpperCase()}' registered.`);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to save document type.');
    }
  };

  const handleDelete = async (code: string) => {
    if (!window.confirm(`Deactivate document type '${code}'?`)) return;
    try {
      await adminApi.deleteDocumentType(code);
      setSuccessMsg(`Document type '${code}' deactivated.`);
      loadData();
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || 'Failed to deactivate.');
    }
  };

  return (
    <div className="space-y-6">
      {/* Messages */}
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
              <Files size={14} />
              <span>Document Type Taxonomy & Extraction Schema</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F2A5C] tracking-tight">
              Document Types Catalog
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Define accepted document types, classification keywords for OCR detection, and statutory verification adapters.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={openCreateModal}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#0B3C9D] text-white text-sm font-bold hover:bg-[#0F2A5C] shadow-sm transition-all"
            >
              <Plus size={18} />
              <span>Register Document Type</span>
            </button>
            <button
              onClick={loadData}
              className="p-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 transition-colors"
            >
              <RefreshCw size={18} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6">
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs uppercase font-bold text-slate-500">Registered Types</span>
            <p className="text-2xl font-bold text-[#0F2A5C] mt-1">{docTypes.length}</p>
          </div>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs uppercase font-bold text-slate-500">Statutory Verified Types</span>
            <p className="text-2xl font-bold text-emerald-700 mt-1">
              {docTypes.filter((d) => d.statutory_verification_applies || d.verification_method !== 'MANUAL').length}
            </p>
          </div>
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-xs uppercase font-bold text-slate-500">Active Documents</span>
            <p className="text-2xl font-bold text-[#0B3C9D] mt-1">
              {docTypes.filter((d) => d.is_active).length} Active
            </p>
          </div>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex items-center justify-between">
        <div className="relative w-full max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search code, name, or authority..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto w-full">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200 uppercase text-xs tracking-wider">
              <tr>
                <th className="py-4 px-5">Type Code</th>
                <th className="py-4 px-5">Display Name</th>
                <th className="py-4 px-5">Issuing Authority</th>
                <th className="py-4 px-5">Statutory Adapter</th>
                <th className="py-4 px-5">Validity</th>
                <th className="py-4 px-5">Classification Keywords</th>
                <th className="py-4 px-5">Status</th>
                <th className="py-4 px-5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredDocTypes.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-400">
                    No document types found.
                  </td>
                </tr>
              ) : (
                filteredDocTypes.map((dt) => (
                  <tr key={dt.code} className="hover:bg-slate-50/70 transition-colors">
                    <td className="py-4 px-5 font-mono font-bold text-[#0B3C9D] whitespace-nowrap">
                      {dt.code}
                    </td>
                    <td className="py-4 px-5 font-semibold text-[#0F2A5C] max-w-xs truncate">
                      {dt.name}
                    </td>
                    <td className="py-4 px-5 text-xs text-slate-600 max-w-xs truncate">
                      {dt.issuing_authority || 'Authorized Regulatory Body'}
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap">
                      {dt.statutory_verification_applies || dt.verification_method !== 'MANUAL' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200">
                          <ShieldCheck size={13} className="text-emerald-600" />
                          <span>{dt.authority_adapter || dt.verification_method}</span>
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">Manual Scrutiny</span>
                      )}
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap text-xs text-slate-600">
                      {dt.has_expiry ? `${dt.default_validity_months || 12} Months` : 'Lifetime'}
                    </td>
                    <td className="py-4 px-5 max-w-xs">
                      <div className="flex flex-wrap gap-1.5">
                        {(dt.keywords || []).slice(0, 3).map((kw) => (
                          <span
                            key={kw}
                            className="text-xs bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-mono font-medium"
                          >
                            {kw}
                          </span>
                        ))}
                        {(dt.keywords || []).length > 3 && (
                          <span className="text-xs text-slate-400 font-medium">
                            +{dt.keywords!.length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-4 px-5 whitespace-nowrap">
                      <StatusPill status={dt.is_active ? 'ACTIVE' : 'ARCHIVED'} />
                    </td>
                    <td className="py-4 px-5 text-right whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={() => openEditModal(dt)}
                          className="p-1.5 text-slate-600 hover:bg-slate-100 rounded-md"
                          title="Edit Document Type"
                        >
                          <Edit size={15} />
                        </button>
                        {dt.is_active && (
                          <button
                            onClick={() => handleDelete(dt.code)}
                            className="p-1.5 text-red-600 hover:bg-red-50 rounded-md"
                            title="Deactivate Document Type"
                          >
                            <Trash2 size={15} />
                          </button>
                        )}
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
      {/* CREATE / EDIT DOCUMENT TYPE MODAL                                         */}
      {/* ========================================================================= */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={isEditing ? `Edit Document Type: ${selectedCode}` : 'Register New Document Type'}
        subtitle={isEditing ? 'Update taxonomy, classification keywords, or statutory verification adapter' : 'Configure a new document type for institutional application verification'}
        maxWidth="max-w-[840px]"
        footer={
          <>
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="h-11 px-5 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-200 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="h-11 px-6 rounded-xl text-sm font-bold bg-[#0B3C9D] text-white hover:bg-[#0F2A5C] shadow-sm transition-colors"
            >
              {isEditing ? 'Save Changes' : 'Register Document Type'}
            </button>
          </>
        }
      >
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Document Code *
              </label>
              <input
                type="text"
                disabled={isEditing}
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value.toUpperCase() })}
                placeholder="e.g. SOLAR_NOC"
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 font-mono text-sm uppercase disabled:bg-slate-100 font-semibold focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Display Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g. Solar Energy Installation NOC"
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Issuing Authority
              </label>
              <input
                type="text"
                value={formData.issuing_authority}
                onChange={(e) => setFormData({ ...formData, issuing_authority: e.target.value })}
                placeholder="e.g. Ministry of New & Renewable Energy"
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
                Max Upload Size (MB)
              </label>
              <input
                type="number"
                value={formData.max_size_mb}
                onChange={(e) => setFormData({ ...formData, max_size_mb: parseInt(e.target.value) || 10 })}
                className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase mb-2">
              Description & Regulatory Purpose
            </label>
            <textarea
              rows={2}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              className="w-full p-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              placeholder="Regulatory description and instructions for institutes..."
            />
          </div>

          {/* Validity & Expiry Settings */}
          <div className="p-5 bg-slate-50/80 rounded-xl border border-slate-200 space-y-4">
            <span className="text-xs font-bold uppercase text-[#0B3C9D] block">
              Validity & Statutory Verification Settings
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
              <label className="flex items-center gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={formData.has_expiry}
                  onChange={(e) => setFormData({ ...formData, has_expiry: e.target.checked })}
                  className="w-4 h-4 rounded text-[#0B3C9D] focus:ring-[#0B3C9D]"
                />
                <span className="text-xs font-semibold text-slate-700">Document Has Expiry Date</span>
              </label>

              {formData.has_expiry && (
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase mb-2">Default Validity (Months)</label>
                  <input
                    type="number"
                    value={formData.default_validity_months}
                    onChange={(e) =>
                      setFormData({ ...formData, default_validity_months: parseInt(e.target.value) || 12 })
                    }
                    className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                  />
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-slate-200 items-center">
              <label className="flex items-center gap-2.5 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={formData.statutory_verification_applies}
                  onChange={(e) =>
                    setFormData({ ...formData, statutory_verification_applies: e.target.checked })
                  }
                  className="w-4 h-4 rounded text-[#0B3C9D] focus:ring-[#0B3C9D]"
                />
                <span className="text-xs font-semibold text-slate-700">
                  Statutory Automated Verification Applies
                </span>
              </label>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase mb-2">Authority Adapter</label>
                <select
                  value={formData.authority_adapter}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      authority_adapter: e.target.value,
                      verification_method: e.target.value === 'MANUAL' ? 'MANUAL' : 'API',
                    })
                  }
                  className="w-full h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-semibold text-slate-800 bg-white focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                >
                  {AUTHORITY_ADAPTERS.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Classification Keywords */}
          <div className="p-5 bg-slate-50/80 rounded-xl border border-slate-200 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span className="text-xs font-bold uppercase text-[#0B3C9D] flex items-center gap-2">
                <Tag size={15} />
                <span>Classification OCR Keywords</span>
              </span>
              <span className="text-xs text-slate-500">Used by OCR to classify uploaded files</span>
            </div>

            {/* Keyword Input & Button aligned on one row */}
            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Enter token (e.g. certificate, clearance, patta, noc)..."
                value={newKeyword}
                onChange={(e) => setNewKeyword(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddKeyword())}
                className="flex-1 h-11 px-3.5 rounded-lg border border-slate-300 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
              <button
                type="button"
                onClick={handleAddKeyword}
                className="h-11 px-5 bg-[#0B3C9D] text-white text-xs font-bold rounded-lg hover:bg-[#0F2A5C] shrink-0 transition-colors"
              >
                Add Keyword
              </button>
            </div>

            {/* Keyword chips in wrapped flex row with readable spacing */}
            <div className="flex flex-wrap gap-2 pt-1">
              {formData.keywords.length === 0 ? (
                <span className="text-xs text-slate-400 italic">No keywords added yet.</span>
              ) : (
                formData.keywords.map((kw) => (
                  <span
                    key={kw}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white border border-slate-300 text-xs text-[#0F2A5C] font-mono shadow-2xs font-medium"
                  >
                    <span>{kw}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveKeyword(kw)}
                      className="text-slate-400 hover:text-red-600 transition-colors"
                      title={`Remove ${kw}`}
                    >
                      <X size={13} />
                    </button>
                  </span>
                ))
              )}
            </div>
          </div>

          {/* Extraction Schema Fields */}
          <div className="p-5 bg-slate-50/80 rounded-xl border border-slate-200 space-y-4">
            <span className="text-xs font-bold uppercase text-[#0B3C9D] flex items-center gap-2">
              <Key size={15} />
              <span>Required Extraction Schema Fields</span>
            </span>

            <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
              <input
                type="text"
                placeholder="Field key (e.g. area_sqm)"
                value={newFieldKey}
                onChange={(e) => setNewFieldKey(e.target.value)}
                className="h-11 px-3 rounded-lg border border-slate-300 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
              <input
                type="text"
                placeholder="Label (e.g. Land Area in Sqm)"
                value={newFieldLabel}
                onChange={(e) => setNewFieldLabel(e.target.value)}
                className="h-11 px-3 rounded-lg border border-slate-300 text-xs focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              />
              <select
                value={newFieldType}
                onChange={(e) => setNewFieldType(e.target.value)}
                className="h-11 px-3 rounded-lg border border-slate-300 text-xs font-semibold bg-white focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
              >
                <option value="text">text</option>
                <option value="number">number</option>
                <option value="date">date</option>
                <option value="id">id / code</option>
              </select>
              <button
                type="button"
                onClick={handleAddField}
                className="h-11 px-4 bg-[#0B3C9D] text-white text-xs font-bold rounded-lg hover:bg-[#0F2A5C] transition-colors"
              >
                Add Field
              </button>
            </div>

            <div className="space-y-2 pt-1">
              {formData.extraction_schema.map((f, idx) => (
                <div
                  key={f.key + idx}
                  className="flex items-center justify-between p-3 rounded-lg bg-white border border-slate-200 text-xs font-mono"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-[#0B3C9D]">{f.key}</span>
                    <span className="text-slate-600 font-sans">{f.label}</span>
                    <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-[10px] uppercase font-bold">{f.type}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveField(idx)}
                    className="p-1 text-slate-400 hover:text-red-600 transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Modal>
    </div>
  );
};
