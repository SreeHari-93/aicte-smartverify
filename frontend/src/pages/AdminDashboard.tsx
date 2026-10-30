import React from 'react';
import { useAuth } from '../context/AuthContext';
import { TricolourStrip } from '../components/TricolourStrip';
import { Shield, LogOut, CheckCircle2, Users, FileCheck2, AlertTriangle } from 'lucide-react';

export const AdminDashboard: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <TricolourStrip />

      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#0B3C9D] flex items-center justify-center text-white">
              <Shield size={22} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-[#0B3C9D] leading-none">
                AICTE SmartVerify AI
              </h1>
              <span className="text-xs text-[#7A8699]">Central Admin Console</span>
            </div>
          </div>

          <button
            onClick={logout}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-[#0F2A5C] hover:text-[#C62828] hover:bg-red-50 rounded-lg transition-colors border border-slate-200"
          >
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto w-full p-6 sm:p-8 flex-1">
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div>
              <span className="text-xs uppercase tracking-wider font-semibold text-[#0B3C9D] bg-blue-50 px-2.5 py-1 rounded">
                AICTE Central Administrator
              </span>
              <h2 className="text-2xl font-bold text-[#0F2A5C] mt-2">
                Administrator: {user?.email || 'admin@aicte-india.org'}
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                Security Role: <span className="font-semibold text-slate-800">{user?.role || 'ADMIN'}</span> | Session: Active
              </p>
            </div>

            <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3.5 py-2 rounded-xl text-xs font-semibold">
              <CheckCircle2 size={16} className="text-emerald-600" />
              <span>Full Administrative Access</span>
            </div>
          </div>

          {/* Quick Metrics Placeholder for future modules */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
            <div className="p-5 bg-slate-50 rounded-xl border border-slate-200 flex items-center gap-4">
              <div className="p-3 bg-blue-100 text-[#0B3C9D] rounded-lg">
                <Users size={24} />
              </div>
              <div>
                <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">Registered Institutes</span>
                <p className="text-xl font-bold text-[#0F2A5C] mt-0.5">3 Active</p>
              </div>
            </div>

            <div className="p-5 bg-slate-50 rounded-xl border border-slate-200 flex items-center gap-4">
              <div className="p-3 bg-orange-100 text-[#F58220] rounded-lg">
                <FileCheck2 size={24} />
              </div>
              <div>
                <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">Validation Queue (Step 2)</span>
                <p className="text-xl font-bold text-[#0F2A5C] mt-0.5">Ready for Ingestion</p>
              </div>
            </div>

            <div className="p-5 bg-slate-50 rounded-xl border border-slate-200 flex items-center gap-4">
              <div className="p-3 bg-emerald-100 text-emerald-700 rounded-lg">
                <AlertTriangle size={24} />
              </div>
              <div>
                <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">Audit Trail Security</span>
                <p className="text-xl font-bold text-[#0F2A5C] mt-0.5">Append-Only Active</p>
              </div>
            </div>
          </div>
        </div>

        {/* Step 1 Completion Notice */}
        <div className="bg-gradient-to-r from-blue-50 to-orange-50 rounded-2xl border border-blue-100 p-8">
          <div className="flex items-center gap-3 mb-2">
            <Shield size={24} className="text-[#0B3C9D]" />
            <h3 className="text-lg font-bold text-[#0B3C9D]">Authentication Core Online</h3>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed max-w-2xl">
            Admin session verified with Argon2id credentials and double-submit CSRF protection.
            Reviewer workflows and document validation scrutiny modules will be configured in subsequent steps.
          </p>
        </div>
      </main>

      <footer className="w-full py-4 text-center text-xs text-slate-500 border-t border-slate-200">
        © AICTE, Ministry of Education, Govt. of India | Central Administration
      </footer>
    </div>
  );
};

