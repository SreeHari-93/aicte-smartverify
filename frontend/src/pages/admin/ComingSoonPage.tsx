import React from 'react';
import { Clock, ShieldCheck, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

interface ComingSoonPageProps {
  title: string;
  moduleName: string;
  stage?: string;
  description?: string;
}

export const ComingSoonPage: React.FC<ComingSoonPageProps> = ({
  title,
  moduleName,
  stage = 'Stage 8-ii',
  description = 'This governance module is under active implementation for the next milestone in the AICTE SmartVerify AI rollout schedule.',
}) => {
  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="inline-flex items-center gap-2 bg-blue-50 text-[#0B3C9D] text-xs font-semibold px-2.5 py-1 rounded-md mb-2">
              <ShieldCheck size={14} />
              <span>AICTE Central Administration Console</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-[#0F2A5C] tracking-tight">
              {title}
            </h1>
            <p className="text-sm text-slate-500 mt-1 max-w-2xl">
              {description}
            </p>
          </div>

          <div className="inline-flex items-center gap-2 bg-[#FFF0D6] border border-[#FCE0BE] text-[#B85700] px-3.5 py-2 rounded-xl text-xs font-bold shrink-0 self-start sm:self-auto">
            <Clock size={16} />
            <span>Scheduled for {stage}</span>
          </div>
        </div>

        {/* Coming Soon Card */}
        <div className="mt-8 bg-slate-50/80 rounded-2xl border border-dashed border-slate-300 p-8 sm:p-12 text-center max-w-2xl mx-auto">
          <div className="w-16 h-16 rounded-2xl bg-[#E3F0FF] text-[#0B3C9D] mx-auto flex items-center justify-center mb-4 shadow-xs">
            <Clock size={32} />
          </div>
          <h2 className="text-xl font-bold text-[#0F2A5C]">
            {moduleName} Module Coming Soon
          </h2>
          <p className="text-sm text-slate-600 mt-2 leading-relaxed">
            As outlined in the milestone roadmap, <strong className="text-[#0B3C9D]">{moduleName}</strong> will be connected in <strong className="text-[#0B3C9D]">{stage}</strong> following the Stage 8-i configurable rules, document types, and checklists release.
          </p>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/admin/rules"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-[#0B3C9D] text-white text-sm font-semibold hover:bg-[#0F2A5C] shadow-sm transition-colors"
            >
              <span>Manage Rules & Rulesets</span>
              <ArrowRight size={16} />
            </Link>
            <Link
              to="/admin/document-types"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white text-slate-700 border border-slate-200 text-sm font-semibold hover:bg-slate-50 transition-colors"
            >
              <span>Document Types</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

