import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import {
  Clock,
  AlertTriangle,
  ArrowRight,
  FileSignature,
  Hourglass,
  Calendar,
  Users,
} from 'lucide-react';
import { workflowApi, WorkflowDashboardData } from '../api/workflow';

export const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<WorkflowDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setIsLoading(true);
        const wfData = await workflowApi.getDashboard();
        setData(wfData);
      } catch (err) {
        console.error('Failed to load workflow dashboard metrics:', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchData();
  }, []);

  const counters = data?.counters || {
    total: 0,
    in_progress: 0,
    returned: 0,
    on_hold: 0,
    completed: 0,
    overdue: 0,
    due_in_7_days: 0,
    open_undertakings: 0,
    documents_expiring: 0,
    evc_pending: 0,
  };

  const isCommitteeMember = user?.role === 'COMMITTEE_MEMBER';
  const todayFormatted = (() => {
    const d = new Date();
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    return `${day}-${month}-${year}`;
  })();

  return (
    <div className="space-y-6 pb-12">
      {/* 1. Page Title & Today's Date */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 mb-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Dashboard</h1>
            <p className="text-sm text-slate-600 mt-1">Overview of application workflows, deadlines, and operational metrics.</p>
          </div>
          <div className="text-xs text-slate-600 font-medium">
            {todayFormatted}
          </div>
        </div>
      </div>

      {/* 2. Primary Workflow Counters Grid (Plain white cards, soft shadow) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {/* Card 1: In progress */}
        <Link
          to={isCommitteeMember ? '/admin/applications' : '/admin/workflow'}
          className="p-5 bg-white rounded-lg border border-slate-200 shadow-sm hover:border-[#0B3C9D] transition-colors group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-600">In progress</span>
            <Clock size={16} className="text-[#0B3C9D]" />
          </div>
          <p className="text-2xl font-bold text-[#0F2A5C] mt-3">
            {isLoading ? '...' : counters.in_progress}
          </p>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
            <span>Active applications</span>
            <ArrowRight size={12} className="text-[#0B3C9D] group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Card 2: Overdue */}
        <Link
          to={isCommitteeMember ? '/admin/applications' : '/admin/workflow'}
          className="p-5 bg-white rounded-lg border border-slate-200 shadow-sm hover:border-red-400 transition-colors group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-red-600">Overdue</span>
            <AlertTriangle size={16} className="text-red-600" />
          </div>
          <p className="text-2xl font-bold text-red-700 mt-3">
            {isLoading ? '...' : counters.overdue}
          </p>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
            <span>Exceeded SLA</span>
            <ArrowRight size={12} className="text-red-600 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Card 3: Due in 7 days */}
        <Link
          to={isCommitteeMember ? '/admin/applications' : '/admin/workflow'}
          className="p-5 bg-white rounded-lg border border-slate-200 shadow-sm hover:border-amber-400 transition-colors group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-amber-700">Due in 7 days</span>
            <Calendar size={16} className="text-[#E8650A]" />
          </div>
          <p className="text-2xl font-bold text-amber-800 mt-3">
            {isLoading ? '...' : counters.due_in_7_days}
          </p>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
            <span>Approaching deadline</span>
            <ArrowRight size={12} className="text-[#E8650A] group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Card 4: Open undertakings */}
        <Link
          to={isCommitteeMember ? '/admin/dashboard' : '/admin/undertakings'}
          className="p-5 bg-white rounded-lg border border-slate-200 shadow-sm hover:border-purple-400 transition-colors group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-purple-700">Open undertakings</span>
            <FileSignature size={16} className="text-purple-700" />
          </div>
          <p className="text-2xl font-bold text-purple-900 mt-3">
            {isLoading ? '...' : counters.open_undertakings ?? 0}
          </p>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
            <span>Active conditions</span>
            <ArrowRight size={12} className="text-purple-700 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Card 5: Expiring documents */}
        <Link
          to={isCommitteeMember ? '/admin/dashboard' : '/admin/validity'}
          className="p-5 bg-white rounded-lg border border-slate-200 shadow-sm hover:border-orange-400 transition-colors group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-orange-700">Documents expiring</span>
            <Hourglass size={16} className="text-orange-600" />
          </div>
          <p className="text-2xl font-bold text-orange-900 mt-3">
            {isLoading ? '...' : counters.documents_expiring ?? 0}
          </p>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
            <span>Leases and NOCs</span>
            <ArrowRight size={12} className="text-orange-600 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Card 6: EVC pending */}
        <Link
          to="/admin/evc"
          className="p-5 bg-white rounded-lg border border-slate-200 shadow-sm hover:border-emerald-400 transition-colors group flex flex-col justify-between"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-emerald-800">EVC pending</span>
            <Users size={16} className="text-emerald-700" />
          </div>
          <p className="text-2xl font-bold text-emerald-900 mt-3">
            {isLoading ? '...' : counters.evc_pending ?? 0}
          </p>
          <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
            <span>Visit scheduling</span>
            <ArrowRight size={12} className="text-emerald-700 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      </div>

      {/* 3. Section Navigation Cards (Plain white, consistent soft shadow, no circle icons next to headings) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {!isCommitteeMember && (
          <Link
            to="/admin/workflow"
            className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:border-slate-300 transition-colors group flex flex-col justify-between"
          >
            <div>
              <h2 className="text-base font-semibold text-slate-900">Workflow</h2>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Track application stages, monitor regional pipelines, and manage officer assignments.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-1.5 text-xs font-medium text-[#0B3C9D]">
              <span>Open workflow</span>
              <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>
        )}

        <Link
          to="/admin/applications"
          className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:border-slate-300 transition-colors group flex flex-col justify-between"
        >
          <div>
            <h2 className="text-base font-semibold text-slate-900">Applications</h2>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              {isCommitteeMember
                ? 'Review assigned applications, inspect stage history, and verify submitted documents.'
                : 'Filter and inspect institutional applications across regions, categories, and review stages.'}
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1.5 text-xs font-medium text-[#0B3C9D]">
            <span>View applications</span>
            <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        <Link
          to="/admin/evc"
          className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:border-slate-300 transition-colors group flex flex-col justify-between"
        >
          <div>
            <h2 className="text-base font-semibold text-slate-900">EVC visits</h2>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Schedule inspection visits with date conflict detection, assign committee members, and record visit reports.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1.5 text-xs font-medium text-[#0B3C9D]">
            <span>Manage visits</span>
            <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {!isCommitteeMember && (
          <Link
            to="/admin/undertakings"
            className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:border-slate-300 transition-colors group flex flex-col justify-between"
          >
            <div>
              <h2 className="text-base font-semibold text-slate-900">Undertakings</h2>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Issue conditional compliance undertakings, track deadlines, verify institute evidence, and record decisions.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-1.5 text-xs font-medium text-[#0B3C9D]">
              <span>Review undertakings</span>
              <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>
        )}

        {!isCommitteeMember && (
          <Link
            to="/admin/validity"
            className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:border-slate-300 transition-colors group flex flex-col justify-between"
          >
            <div>
              <h2 className="text-base font-semibold text-slate-900">Document validity</h2>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Monitor validity registers for fire safety NOCs, building stability certificates, and land leases.
              </p>
            </div>
            <div className="mt-4 flex items-center gap-1.5 text-xs font-medium text-[#0B3C9D]">
              <span>Inspect validity register</span>
              <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>
        )}

        <Link
          to="/admin/alerts"
          className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:border-slate-300 transition-colors group flex flex-col justify-between"
        >
          <div>
            <h2 className="text-base font-semibold text-slate-900">Alerts</h2>
            <p className="text-xs text-slate-600 mt-1 leading-relaxed">
              Review due-soon reminders, overdue escalations, unread supervisory alerts, and automated notifications.
            </p>
          </div>
          <div className="mt-4 flex items-center gap-1.5 text-xs font-medium text-[#0B3C9D]">
            <span>Open alerts</span>
            <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      </div>

      {/* 4. Second Row for Central Configuration (Admin & Officers) */}
      {!isCommitteeMember && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Link
            to="/admin/rules"
            className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:border-slate-300 transition-colors group flex flex-col justify-between"
          >
            <div>
              <h2 className="text-base font-semibold text-slate-900">Rules and timelines</h2>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Configure workflow SLAs, document checklists, and notification offset rules across all 4 templates.
              </p>
            </div>
            <div className="mt-3 flex items-center gap-1 text-xs font-medium text-[#0B3C9D]">
              <span>Open rules and timelines</span>
              <ArrowRight size={12} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>

          <Link
            to="/admin/reports"
            className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:border-slate-300 transition-colors group flex flex-col justify-between"
          >
            <div>
              <h2 className="text-base font-semibold text-slate-900">Reports</h2>
              <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                Generate and download summary reports covering workflow progression, overdue cases, EVC visit status, and active undertakings.
              </p>
            </div>
            <div className="mt-3 flex items-center gap-1 text-xs font-medium text-[#0B3C9D]">
              <span>Generate reports</span>
              <ArrowRight size={12} className="group-hover:translate-x-1 transition-transform" />
            </div>
          </Link>
        </div>
      )}
    </div>
  );
};
