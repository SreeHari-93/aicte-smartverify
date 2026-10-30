import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import {
  Shield,
  CheckCircle2,
  Scale,
  Files,
  ListChecks,
  ScrollText,
  ArrowRight,
  Sparkles,
  Layers,
} from 'lucide-react';
import { adminApi, RuleOut, RuleSetOut, DocumentTypeOut } from '../api/admin';

export const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [rules, setRules] = useState<RuleOut[]>([]);
  const [ruleSets, setRuleSets] = useState<RuleSetOut[]>([]);
  const [docTypes, setDocTypes] = useState<DocumentTypeOut[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [rulesData, rulesetsData, docTypesData] = await Promise.all([
          adminApi.listRules().catch(() => []),
          adminApi.listRuleSets().catch(() => []),
          adminApi.listDocumentTypes().catch(() => []),
        ]);
        setRules(rulesData);
        setRuleSets(rulesetsData);
        setDocTypes(docTypesData);
      } catch {
        // quiet fallback
      }
    };
    fetchData();
  }, []);

  const activeRuleSet = ruleSets.find((rs) => rs.status === 'ACTIVE' || rs.status === 'PUBLISHED');

  return (
    <div className="space-y-6">
      {/* 1. Admin Profile & Status Card */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center gap-2 bg-[#E3F0FF] text-[#0B3C9D] text-xs font-semibold px-2.5 py-1 rounded-md mb-2">
              <Shield size={14} />
              <span>AICTE Central Administration Console</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F2A5C] tracking-tight">
              Welcome, {user?.email || 'Administrator'}
            </h1>
            <p className="text-sm text-slate-500 mt-1">
              Role: <strong className="text-slate-800">{user?.role || 'ADMIN'}</strong> | Session Verified (Argon2id + SameSite Cookies)
            </p>
          </div>

          <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3.5 py-2 rounded-xl text-xs font-bold shrink-0">
            <CheckCircle2 size={16} className="text-emerald-600" />
            <span>Full Governance Access</span>
          </div>
        </div>

        {/* 2. Key Metrics Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mt-6">
          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold text-slate-500">Configured Rules</span>
              <Scale size={18} className="text-[#0B3C9D]" />
            </div>
            <p className="text-2xl font-bold text-[#0F2A5C] mt-2">{rules.length}</p>
            <span className="text-xs text-slate-500">
              {rules.filter((r) => r.status === 'DRAFT').length} Draft | {rules.filter((r) => r.status === 'PUBLISHED').length} Published
            </span>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold text-slate-500">Active RuleSet</span>
              <Layers size={18} className="text-[#E8650A]" />
            </div>
            <p className="text-2xl font-bold text-[#0F2A5C] mt-2 truncate">
              {activeRuleSet?.version_label || 'v1.0'}
            </p>
            <span className="text-xs text-slate-500 truncate block">
              {activeRuleSet?.name || 'APH 2026-27'}
            </span>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold text-slate-500">Document Taxonomy</span>
              <Files size={18} className="text-emerald-600" />
            </div>
            <p className="text-2xl font-bold text-[#0F2A5C] mt-2">{docTypes.length}</p>
            <span className="text-xs text-slate-500">Recognized Document Types</span>
          </div>

          <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase font-bold text-slate-500">Audit Trail</span>
              <ScrollText size={18} className="text-indigo-600" />
            </div>
            <p className="text-2xl font-bold text-[#0F2A5C] mt-2">Active</p>
            <span className="text-xs text-slate-500">Append-Only Scrutiny</span>
          </div>
        </div>
      </div>

      {/* 3. Quick Action Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          to="/admin/rules"
          className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:border-[#0B3C9D] transition-all group"
        >
          <div className="w-12 h-12 rounded-xl bg-[#E3F0FF] text-[#0B3C9D] flex items-center justify-center mb-4 group-hover:bg-[#0B3C9D] group-hover:text-white transition-colors">
            <Scale size={24} />
          </div>
          <h2 className="text-lg font-bold text-[#0F2A5C]">Rules Manager</h2>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            Create, duplicate, simulate, version, and publish declarative rules across the 9 regulatory evaluators.
          </p>
          <div className="mt-4 flex items-center gap-1.5 text-xs font-bold text-[#0B3C9D]">
            <span>Manage Rules</span>
            <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        <Link
          to="/admin/document-types"
          className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:border-[#0B3C9D] transition-all group"
        >
          <div className="w-12 h-12 rounded-xl bg-orange-50 text-[#E8650A] flex items-center justify-center mb-4 group-hover:bg-[#E8650A] group-hover:text-white transition-colors">
            <Files size={24} />
          </div>
          <h2 className="text-lg font-bold text-[#0F2A5C]">Document Types</h2>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            Configure accepted file formats, classification keywords for OCR detection, and statutory authority adapters.
          </p>
          <div className="mt-4 flex items-center gap-1.5 text-xs font-bold text-[#E8650A]">
            <span>Configure Document Types</span>
            <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        <Link
          to="/admin/checklists"
          className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm hover:border-[#0B3C9D] transition-all group"
        >
          <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center mb-4 group-hover:bg-emerald-700 group-hover:text-white transition-colors">
            <ListChecks size={24} />
          </div>
          <h2 className="text-lg font-bold text-[#0F2A5C]">Required Checklists</h2>
          <p className="text-xs text-slate-500 mt-1 leading-relaxed">
            Define mandatory and optional document checklists per application category and institute discipline.
          </p>
          <div className="mt-4 flex items-center gap-1.5 text-xs font-bold text-emerald-700">
            <span>Manage Checklists</span>
            <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      </div>

      {/* 4. Architectural Core & Milestone Notice */}
      <div className="bg-gradient-to-r from-blue-50/80 via-white to-orange-50/80 rounded-2xl border border-blue-100/80 p-6 sm:p-8">
        <div className="flex items-center gap-3 mb-2">
          <Sparkles size={20} className="text-[#0B3C9D]" />
          <h3 className="text-base font-bold text-[#0B3C9D]">AICTE SmartVerify AI Roadmap</h3>
        </div>
        <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
          Core principle: <strong className="text-[#0F2A5C]">"Rules decide, AI explains, Officials approve."</strong> Stage 8-i delivers the complete administrative portal shell, configurable rules engine with optimistic locking and drafts isolation, classification taxonomy, and checklist management.
        </p>
      </div>
    </div>
  );
};
